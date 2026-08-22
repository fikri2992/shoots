"""Backfill demo shots from Wikimedia Commons: CC-licensed originals with EXIF.

One query per technique family. Keeps only files whose EXIF carries an exposure
time (so the Judge's hard-evidence path has something to check) and writes them
to data/demo/commons/<technique>_<n>.jpg with a sidecar .json of licence info.
Demo data only; never committed (data/demo/ is git-ignored).
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Shoots-hackathon-demo/0.1 (your-contact@example.com)"
API = "https://commons.wikimedia.org/w/api.php"
OUT = Path(__file__).resolve().parents[2] / "data" / "demo" / "commons"
PER_QUERY = 3
MAX_BYTES = 9_000_000

QUERIES = {
    "panning": "panning motion blur cyclist",
    "long_exposure": "long exposure waterfall silky",
    "light_trails": "light trails night traffic",
    "silhouette": "silhouette sunset person",
    "golden_hour": "golden hour portrait",
    "shallow_dof": "bokeh portrait shallow depth of field",
    "leading_lines": "leading lines railway perspective",
    "reflections": "reflection lake mountain symmetry",
    "macro": "macro insect eye",
    "telephoto_compression": "telephoto compression moon building",
    "freeze_action": "splash water drop high speed",
    "astro": "milky way night sky landscape",
}


def call(params: dict) -> dict:
    params = {**params, "format": "json"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def candidates(query: str) -> list[dict]:
    data = call(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": 25,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|metadata|extmetadata",
        }
    )
    pages = data.get("query", {}).get("pages", {})
    out = []
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        if info.get("mime") != "image/jpeg" or info.get("size", 0) > MAX_BYTES:
            continue
        meta = {m["name"]: m["value"] for m in info.get("metadata") or [] if "name" in m}
        if "ExposureTime" not in meta or "FNumber" not in meta:
            continue
        ext = info.get("extmetadata") or {}
        out.append(
            {
                "title": p["title"],
                "url": info["url"],
                "size": info["size"],
                "exposure": meta.get("ExposureTime"),
                "fnumber": meta.get("FNumber"),
                "iso": meta.get("ISOSpeedRatings"),
                "license": ext.get("LicenseShortName", {}).get("value", ""),
                "artist": ext.get("Artist", {}).get("value", ""),
                "page": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(p['title'])}",
            }
        )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for technique, query in QUERIES.items():
        found = candidates(query)[:PER_QUERY]
        print(f"{technique}: {len(found)} with EXIF", flush=True)
        for n, c in enumerate(found, 1):
            target = OUT / f"{technique}_{n}.jpg"
            if target.exists():
                continue
            req = urllib.request.Request(c["url"], headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                target.write_bytes(r.read())
            target.with_suffix(".json").write_text(json.dumps(c, indent=2))
            total += 1
            settings_text = f"{c['exposure']}s f/{c['fnumber']} ISO {c['iso']}"
            print(
                f"  {target.name}  {c['size'] // 1000} KB  {settings_text}  [{c['license']}]",
                flush=True,
            )
    print(f"downloaded {total} files to {OUT}")


if __name__ == "__main__":
    sys.exit(main())
