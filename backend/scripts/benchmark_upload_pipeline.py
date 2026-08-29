"""Measure production Shot ingress through terminal Run settlement.

This is an operational benchmark, not a model-quality evaluation. It creates a
disposable Photographer and device directly in the configured production store,
uploads a bounded still-image corpus through the public API, polls authoritative
Run state, writes aggregate timings, then deletes the exact test identity and its
blob prefix.

The bearer token exists only in this process and is never printed or persisted.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import secrets
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.api.pairing import token_fingerprint
from app.domain.entities import User
from app.infra import repository as repo
from app.infra.storage import GcsBlobStore, user_prefix
from app.infra.store import FirestoreStore

TERMINAL_RUNS = {"completed", "terminal"}
MODEL_USAGE_LOG_PREFIX = "SHOOTS_MODEL_USAGE "
GEMINI_37_FLASH_GLOBAL_INPUT_PER_MILLION = 0.75
GEMINI_37_FLASH_GLOBAL_CACHED_INPUT_PER_MILLION = 0.075
GEMINI_37_FLASH_GLOBAL_OUTPUT_PER_MILLION = 3.75


@dataclass
class Sample:
    index: int
    path: Path
    source_id: str
    upload_started_at: datetime
    upload_seconds: float = 0.0
    accepted_at: datetime | None = None
    shot_id: str = ""
    run_status: str = ""
    server_seconds: float | None = None
    accepted_to_settled_seconds: float | None = None
    client_total_seconds: float | None = None
    retries: int = 0
    terminal_steps: list[str] = field(default_factory=list)
    error: str = ""

    def public(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "filename": self.path.name,
            "bytes": self.path.stat().st_size,
            "upload_seconds": rounded(self.upload_seconds),
            "run_status": self.run_status,
            "server_seconds": rounded(self.server_seconds),
            "accepted_to_settled_seconds": rounded(self.accepted_to_settled_seconds),
            "client_total_seconds": rounded(self.client_total_seconds),
            "retries": self.retries,
            "terminal_steps": self.terminal_steps,
            "error": self.error,
        }


def rounded(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = max(0, min(len(ordered) - 1, int((len(ordered) * fraction) + 0.999999) - 1))
    return ordered[position]


def summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": rounded(statistics.fmean(values)) if values else None,
        "p50": rounded(percentile(values, 0.50)),
        "p90": rounded(percentile(values, 0.90)),
        "maximum": rounded(max(values)) if values else None,
    }


def corpus_files(root: Path) -> list[Path]:
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    files = sorted(path for path in root.rglob("*") if path.suffix.lower() in allowed)
    if not files:
        raise ValueError(f"no supported still images under {root}")
    return files


def usage_cost(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    prompt = sum(int(item.get("prompt_tokens") or 0) for item in receipts)
    cached = sum(int(item.get("cached_tokens") or 0) for item in receipts)
    tool = sum(int(item.get("tool_tokens") or 0) for item in receipts)
    candidates = sum(int(item.get("candidate_tokens") or 0) for item in receipts)
    thoughts = sum(int(item.get("thought_tokens") or 0) for item in receipts)
    total = sum(int(item.get("total_tokens") or 0) for item in receipts)
    uncached_input = max(0, prompt - cached) + tool
    output = candidates + thoughts
    token_cost = (
        uncached_input * GEMINI_37_FLASH_GLOBAL_INPUT_PER_MILLION
        + cached * GEMINI_37_FLASH_GLOBAL_CACHED_INPUT_PER_MILLION
        + output * GEMINI_37_FLASH_GLOBAL_OUTPUT_PER_MILLION
    ) / 1_000_000
    web_queries = sum(int(item.get("web_grounding_queries") or 0) for item in receipts)
    image_queries = sum(int(item.get("image_grounding_queries") or 0) for item in receipts)
    by_agent: dict[str, dict[str, int]] = {}
    for item in receipts:
        agent = str(item.get("agent") or "unknown")
        row = by_agent.setdefault(agent, {"calls": 0, "tokens": 0})
        row["calls"] += 1
        row["tokens"] += int(item.get("total_tokens") or 0)
    return {
        "calls": len(receipts),
        "prompt_tokens": prompt,
        "cached_tokens": cached,
        "tool_tokens": tool,
        "candidate_tokens": candidates,
        "thought_tokens": thoughts,
        "total_tokens": total,
        "web_grounding_queries": web_queries,
        "image_grounding_queries": image_queries,
        "token_cost_usd": round(token_cost, 6),
        "grounding_cost_usd": 0.0 if not web_queries and not image_queries else None,
        "model_versions": sorted(
            {str(item.get("model_version")) for item in receipts if item.get("model_version")}
        ),
        "by_agent": dict(sorted(by_agent.items())),
        "pricing": {
            "model": "gemini-3.7-flash",
            "region": "global",
            "input_per_million_usd": GEMINI_37_FLASH_GLOBAL_INPUT_PER_MILLION,
            "cached_input_per_million_usd": (GEMINI_37_FLASH_GLOBAL_CACHED_INPUT_PER_MILLION),
            "output_and_reasoning_per_million_usd": (GEMINI_37_FLASH_GLOBAL_OUTPUT_PER_MILLION),
            "valid_through": "2026-12-31",
        },
    }


def _usage_message(entry: dict[str, Any]) -> str:
    text = entry.get("textPayload")
    if isinstance(text, str):
        return text
    payload = entry.get("jsonPayload") or {}
    message = payload.get("message") if isinstance(payload, dict) else ""
    return message if isinstance(message, str) else ""


def query_usage_logs(
    project: str,
    service: str,
    user_id: str,
    started_at: datetime,
    finished_at: datetime,
) -> list[dict[str, Any]]:
    start = (started_at - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")
    finish = (finished_at + timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
    query = (
        'resource.type="cloud_run_revision" '
        f'AND resource.labels.service_name="{service}" '
        f'AND timestamp>="{start}" AND timestamp<="{finish}" '
        f'AND (textPayload:"{MODEL_USAGE_LOG_PREFIX.strip()}" '
        f'OR jsonPayload.message:"{MODEL_USAGE_LOG_PREFIX.strip()}")'
    )
    gcloud = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
    result = subprocess.run(
        [
            gcloud,
            "logging",
            "read",
            query,
            "--project",
            project,
            "--limit",
            "2000",
            "--format=json",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    entries = json.loads(result.stdout or "[]")
    receipts: dict[str, dict[str, Any]] = {}
    for entry in entries:
        message = _usage_message(entry)
        position = message.find(MODEL_USAGE_LOG_PREFIX)
        if position < 0:
            continue
        try:
            receipt = json.loads(message[position + len(MODEL_USAGE_LOG_PREFIX) :])
        except json.JSONDecodeError:
            continue
        if receipt.get("user_id") != user_id:
            continue
        receipt_id = str(receipt.get("receipt_id") or "")
        if receipt_id:
            receipts[receipt_id] = receipt
    return list(receipts.values())


async def provision(store: FirestoreStore, run_id: str) -> tuple[str, str]:
    user_id = f"benchmark-{run_id}"
    token = secrets.token_urlsafe(32)
    await repo.put_user(
        store,
        User(
            id=user_id,
            email=f"{user_id}@example.invalid",
            name="Disposable upload benchmark",
        ),
    )
    await repo.put_device(
        store,
        token_fingerprint(token),
        user_id,
        "Upload benchmark",
        auth_method="benchmark",
    )
    return user_id, token


async def upload_one(
    client: httpx.AsyncClient,
    token: str,
    run_id: str,
    index: int,
    path: Path,
) -> Sample:
    started_at = datetime.now(UTC)
    started = time.monotonic()
    source_id = (
        f"benchmark-{run_id}:external:{index}:{int(started_at.timestamp())}:{path.stat().st_size}"
    )
    sample = Sample(
        index=index,
        path=path,
        source_id=source_id,
        upload_started_at=started_at,
    )
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    try:
        with path.open("rb") as source:
            response = await client.post(
                "/api/ingress/shots",
                headers={"Authorization": f"Bearer {token}"},
                data={"source_id": source_id},
                files={"file": (path.name, source, mime)},
            )
        sample.upload_seconds = time.monotonic() - started
        sample.accepted_at = datetime.now(UTC)
        response.raise_for_status()
        sample.shot_id = response.json()["shot_id"]
    except Exception as error:  # report the individual failure; continue the batch
        sample.upload_seconds = time.monotonic() - started
        sample.error = f"upload: {type(error).__name__}: {str(error)[:240]}"
    return sample


async def wait_for_run(
    client: httpx.AsyncClient,
    token: str,
    sample: Sample,
    *,
    timeout_seconds: float,
    poll_seconds: float,
) -> None:
    if not sample.shot_id or sample.accepted_at is None:
        return
    deadline = time.monotonic() + timeout_seconds
    headers = {"Authorization": f"Bearer {token}"}
    while time.monotonic() < deadline:
        try:
            response = await client.get(f"/api/shots/{sample.shot_id}", headers=headers)
            response.raise_for_status()
            run = response.json().get("run") or {}
            sample.run_status = str(run.get("status", ""))
            if sample.run_status in TERMINAL_RUNS:
                completed_at = parse_time(run.get("completed_at"))
                started_at = parse_time(run.get("started_at"))
                if completed_at and started_at:
                    sample.server_seconds = (completed_at - started_at).total_seconds()
                if completed_at:
                    sample.accepted_to_settled_seconds = max(
                        0.0,
                        (completed_at - sample.accepted_at).total_seconds(),
                    )
                    sample.client_total_seconds = max(
                        0.0,
                        (completed_at - sample.upload_started_at).total_seconds(),
                    )
                steps = run.get("steps") or {}
                sample.retries = sum(
                    1 for step in steps.values() if step.get("state") == "retrying"
                )
                sample.terminal_steps = [
                    name for name, step in steps.items() if step.get("state") == "terminal"
                ]
                return
        except Exception as error:
            sample.error = f"poll: {type(error).__name__}: {str(error)[:240]}"
        await asyncio.sleep(poll_seconds)
    sample.error = sample.error or f"timeout after {timeout_seconds:g} seconds"


async def wait_for_shoot_record(
    client: httpx.AsyncClient,
    token: str,
    shot_ids: set[str],
    *,
    timeout_seconds: float,
    poll_seconds: float,
) -> tuple[dict[str, Any] | None, datetime | None]:
    deadline = time.monotonic() + timeout_seconds
    headers = {"Authorization": f"Bearer {token}"}
    while time.monotonic() < deadline:
        response = await client.get("/api/mobile/snapshot", headers=headers)
        response.raise_for_status()
        record = response.json().get("latest_shoot_record")
        if record and shot_ids.issubset(set(record.get("shot_ids") or [])):
            return record, datetime.now(UTC)
        await asyncio.sleep(poll_seconds)
    return None, None


async def cleanup(store: FirestoreStore, blobs: GcsBlobStore, user_id: str) -> None:
    await blobs.delete_prefix(user_prefix(user_id))
    await repo.delete_user_records(store, user_id)


async def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(3)
    files = corpus_files(args.corpus)
    selected = [files[index % len(files)] for index in range(args.count)]
    store = FirestoreStore()
    blobs = GcsBlobStore()
    user_id = ""
    batch_started_at = datetime.now(UTC)
    samples: list[Sample] = []
    cleanup_error = ""
    runs_observed_at: datetime | None = None
    shoot_record: dict[str, Any] | None = None
    shoot_record_observed_at: datetime | None = None
    shoot_wait_finished_at: datetime | None = None
    try:
        user_id, token = await provision(store, run_id)
        timeout = httpx.Timeout(connect=30, read=180, write=180, pool=30)
        async with httpx.AsyncClient(base_url=args.service_url, timeout=timeout) as client:
            for index, path in enumerate(selected, start=1):
                sample = await upload_one(client, token, run_id, index, path)
                samples.append(sample)
                print(
                    f"accepted {index:02d}/{args.count}: "
                    f"{sample.upload_seconds:.2f}s"
                    + (f" error={sample.error}" if sample.error else ""),
                    flush=True,
                )
            await asyncio.gather(
                *(
                    wait_for_run(
                        client,
                        token,
                        sample,
                        timeout_seconds=args.timeout_seconds,
                        poll_seconds=args.poll_seconds,
                    )
                    for sample in samples
                )
            )
            runs_observed_at = datetime.now(UTC)
            if args.wait_for_shoot_record:
                expected = {sample.shot_id for sample in samples if sample.shot_id}
                shoot_record, shoot_record_observed_at = await wait_for_shoot_record(
                    client,
                    token,
                    expected,
                    timeout_seconds=args.shoot_timeout_seconds,
                    poll_seconds=args.shoot_poll_seconds,
                )
                shoot_wait_finished_at = datetime.now(UTC)
    finally:
        if user_id:
            try:
                await cleanup(store, blobs, user_id)
            except Exception as error:  # preserve the exact id for manual cleanup
                cleanup_error = f"{type(error).__name__}: {str(error)[:300]}"
                print(f"CLEANUP FAILED for {user_id}: {cleanup_error}", flush=True)

    measured_finished_at = shoot_wait_finished_at or runs_observed_at or datetime.now(UTC)
    usage_receipts: list[dict[str, Any]] = []
    usage_error = ""
    if args.gcp_project and args.cloud_run_service and user_id:
        if args.log_wait_seconds:
            await asyncio.sleep(args.log_wait_seconds)
        try:
            usage_receipts = await asyncio.to_thread(
                query_usage_logs,
                args.gcp_project,
                args.cloud_run_service,
                user_id,
                batch_started_at,
                measured_finished_at,
            )
        except Exception as error:
            usage_error = f"{type(error).__name__}: {str(error)[:300]}"

    completed = [sample for sample in samples if sample.run_status == "completed"]
    terminal = [sample for sample in samples if sample.run_status == "terminal"]
    failed = [sample for sample in samples if sample.run_status not in TERMINAL_RUNS]
    accepted = [sample.accepted_at for sample in samples if sample.accepted_at is not None]
    last_accepted_at = max(accepted) if accepted else None
    model_usage = usage_cost(usage_receipts) if usage_receipts else None
    report = {
        "benchmark_id": run_id,
        "service_url": args.service_url,
        "started_at": batch_started_at.isoformat(),
        "finished_at": measured_finished_at.isoformat(),
        "batch_wall_seconds": rounded((measured_finished_at - batch_started_at).total_seconds()),
        "runs_observed_at": runs_observed_at.isoformat() if runs_observed_at else None,
        "runs_batch_wall_seconds": rounded(
            (runs_observed_at - batch_started_at).total_seconds() if runs_observed_at else None
        ),
        "shoot_record_requested": args.wait_for_shoot_record,
        "shoot_record_ready": shoot_record is not None,
        "shoot_record_observed_at": (
            shoot_record_observed_at.isoformat() if shoot_record_observed_at else None
        ),
        "last_upload_to_shoot_record_seconds": rounded(
            (shoot_record_observed_at - last_accepted_at).total_seconds()
            if shoot_record_observed_at and last_accepted_at
            else None
        ),
        "shoot_record": (
            {
                "shoot_id": shoot_record.get("shoot_id"),
                "revision": shoot_record.get("revision"),
                "shot_count": len(shoot_record.get("shot_ids") or []),
                "scout_route": (shoot_record.get("scout") or {}).get("route"),
                "scout_execution_state": (shoot_record.get("scout") or {}).get("execution_state"),
                "deconstruction_status": (shoot_record.get("deconstruction") or {}).get("status"),
            }
            if shoot_record
            else None
        ),
        "requested": args.count,
        "completed": len(completed),
        "terminal": len(terminal),
        "unfinished": len(failed),
        "cleanup_succeeded": not cleanup_error,
        "cleanup_error": cleanup_error,
        "usage_receipts_found": len(usage_receipts),
        "usage_query_error": usage_error,
        "model_usage": model_usage,
        "upload_seconds": summary([sample.upload_seconds for sample in samples]),
        "server_run_seconds": summary(
            [sample.server_seconds for sample in samples if sample.server_seconds is not None]
        ),
        "accepted_to_settled_seconds": summary(
            [
                sample.accepted_to_settled_seconds
                for sample in samples
                if sample.accepted_to_settled_seconds is not None
            ]
        ),
        "client_total_seconds": summary(
            [
                sample.client_total_seconds
                for sample in samples
                if sample.client_total_seconds is not None
            ]
        ),
        "samples": [sample.public() for sample in samples],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--wait-for-shoot-record", action="store_true")
    parser.add_argument("--shoot-poll-seconds", type=float, default=10.0)
    parser.add_argument("--shoot-timeout-seconds", type=float, default=2400.0)
    parser.add_argument("--gcp-project", default="")
    parser.add_argument("--cloud-run-service", default="")
    parser.add_argument("--log-wait-seconds", type=float, default=30.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.count < 1 or args.count > 100:
        parser.error("--count must be between 1 and 100")
    return args


def main() -> None:
    report = asyncio.run(benchmark(arguments()))
    print(json.dumps({key: value for key, value in report.items() if key != "samples"}, indent=2))


if __name__ == "__main__":
    main()
