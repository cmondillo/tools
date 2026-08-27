#!/usr/bin/env python3
"""Bulk-seed the cache via the /admin/cache routes (see README §"Manually
seeding the cache" and app/main.py).

Not "add as many URLs as possible" - that's not actually the point (an
unrequested entry just sits there, no benefit). This is for two real
cases:
  1. A site that 403s any scraper: no automated fetch can ever populate
     it, so give its title/description by hand in the input file.
  2. A URL you already know is worth fetching for real right now (so the
     first real agent doesn't eat the fetch latency): give just the url,
     this script fetches it for real via preview.py directly (bypassing
     payment - this runs as the operator, not an agent) and seeds
     whatever it gets back.

Input: a JSON file, a list of objects. Either just {"url": "..."} (this
script fetches it for real), or a full manual entry (url + at least one
of title/description/etc, "pinned" optional, defaults true for manual
entries) - see AdminCacheEntry in app/main.py for the full field list.

Usage:
    python seed_cache.py --input urls.json --api https://your-deployment.example.com --admin-token $ADMIN_TOKEN

Example urls.json:
[
  {"url": "https://example.com/popular-article"},
  {"url": "https://coinbase.com", "title": "Coinbase", "description": "Buy and sell crypto.", "pinned": true}
]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.preview import PreviewError, fetch_preview  # noqa: E402

_MANUAL_FIELDS = {
    "title",
    "description",
    "image",
    "favicon",
    "site_name",
    "canonical_url",
    "content_type",
}
_POLITE_DELAY_SECONDS = 0.5  # sequential + a small gap, not a burst of parallel requests


async def _resolve_entry(entry: dict) -> dict | None:
    """Return the payload to POST to /admin/cache, or None if this entry
    needs a real fetch that failed (caller should report and skip it)."""
    if _MANUAL_FIELDS & entry.keys():
        # Already has real content (a manual entry, e.g. for a blocked
        # site) - use it as-is, don't try to fetch.
        return {"pinned": True, **entry}

    try:
        result = await fetch_preview(entry["url"], timeout=8, max_bytes=2 * 1024 * 1024)
    except PreviewError as exc:
        print(f"  [skip] {entry['url']}: fetch failed ({exc.message}) - add this one manually "
              f"with title/description in the input file instead.")
        return None

    data = result.to_dict()
    data.pop("final_url", None)
    data.pop("url", None)
    return {"url": entry["url"], "pinned": False, **data}


async def run(input_path: str, api_base: str, admin_token: str) -> int:
    entries = json.loads(Path(input_path).read_text())
    if not isinstance(entries, list):
        print("Input file must be a JSON list of {\"url\": ...} objects.")
        return 1

    headers = {"Authorization": f"Bearer {admin_token}"}
    seeded, skipped = 0, 0

    async with httpx.AsyncClient(base_url=api_base, timeout=15) as http:
        for i, entry in enumerate(entries):
            if "url" not in entry:
                print(f"  [skip] entry #{i}: missing \"url\"")
                skipped += 1
                continue

            payload = await _resolve_entry(entry)
            if payload is None:
                skipped += 1
                continue

            response = await http.post("/admin/cache", json=payload, headers=headers)
            if response.status_code == 200:
                print(f"  [ok]   {entry['url']} (pinned={payload['pinned']})")
                seeded += 1
            else:
                print(f"  [fail] {entry['url']}: HTTP {response.status_code} {response.text}")
                skipped += 1

            if i < len(entries) - 1:
                time.sleep(_POLITE_DELAY_SECONDS)

    print(f"\nSeeded {seeded}, skipped {skipped}, out of {len(entries)} entries.")
    return 0 if skipped == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-seed the link-preview-cache-api cache")
    parser.add_argument("--input", required=True, help="Path to a JSON file (see module docstring)")
    parser.add_argument("--api", default="http://localhost:8000", help="Base URL of the deployment")
    parser.add_argument(
        "--admin-token",
        default=None,
        help="ADMIN_TOKEN value. Falls back to the ADMIN_TOKEN env var if omitted.",
    )
    args = parser.parse_args()

    import os

    token = args.admin_token or os.environ.get("ADMIN_TOKEN")
    if not token:
        print("Need an admin token: pass --admin-token or set ADMIN_TOKEN.")
        sys.exit(1)

    sys.exit(asyncio.run(run(args.input, args.api, token)))


if __name__ == "__main__":
    main()
