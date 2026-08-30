"""Prompts live as versioned .md files beside the agents (AGENTS.md)."""

import hashlib
from functools import cache
from pathlib import Path

_DIR = Path(__file__).parent

_HUMAN_VOICE_PROMPTS = frozenset(
    {
        "coach",
        "composer",
        "crop",
        "judge",
        "journey",
        "preflight",
        "scout",
        "scrub",
        "storyteller",
        "synthesizer",
        "technician",
    }
)


@cache
def load(name: str) -> str:
    source = (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
    if name not in _HUMAN_VOICE_PROMPTS:
        return source
    voice = (_DIR / "human_voice.md").read_text(encoding="utf-8").strip()
    return f"{source}\n\n{voice}"


@cache
def version(name: str) -> str:
    """A short digest of the prompt this claim was written under.

    Recorded beside every longitudinal claim a model contributed to, so a
    sentence can be traced to the exact instructions that produced it. Editing
    a prompt changes the digest, which is the point: the wording of a claim is
    part of what makes it reproducible, and a paragraph written under different
    instructions is a different paragraph even when the figures behind it are
    identical.
    """
    return hashlib.sha256(load(name).encode()).hexdigest()[:12]


@cache
def bundle_version(names: tuple[str, ...]) -> str:
    """Digest a complete multi-prompt agent contract in stable name order."""
    source = "\n".join(f"{name}\n{load(name)}" for name in sorted(names))
    return hashlib.sha256(source.encode()).hexdigest()[:12]
