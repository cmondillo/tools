"""The actual product idea: a shared, TTL-based cache in front of the link
preview fetch. This is what lets link-preview-cache-api charge less than a
fresh-fetch-every-time service (link-preview-api) - most requests are served
from a cheap cache lookup instead of a real outbound fetch+parse.

SQLite, not a heavier cache service (Redis etc.): the whole point of this
project is being provably simple and cheap to run, and SQLite is more than
fast enough for a key/value cache at this traffic scale. A fresh connection
per operation (WAL mode for concurrent reads) rather than a shared
long-lived connection - simplest thing that's correct under FastAPI's
concurrent request handling, and this isn't a bottleneck at this scale.

Deliberately simple cache key: the exact URL string, unnormalized. Two
different-looking URLs for the same page (trailing slash, query param
order, etc.) are treated as different cache entries and won't share a hit.
That's an honest, stated scoping choice (like the wordlist's word-boundary
matching in content-moderation-api) - not a bug, just not attempting
canonicalization heuristics that could themselves introduce bugs.

`pinned` entries never expire regardless of ttl_seconds. This matters for
exactly one real case: an admin-seeded entry for a site that 403s any
scraper (see main.py's /admin/cache). Without it, that entry would expire
after CACHE_TTL_SECONDS like any normal fetch, and the next agent to ask
about it would trigger a real fetch attempt that's guaranteed to fail -
so a *paying* agent gets an error instead of the answer the admin entry
was seeded to guarantee. Regular (non-admin) cache entries are never
pinned - only set() callers that explicitly ask for it get this.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS previews (
            url TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            fetched_at REAL NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    try:  # migrate a pre-existing db (deployed before `pinned` existed)
        conn.execute("ALTER TABLE previews ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists - the CREATE TABLE above already had it
    return conn


@contextmanager
def _cursor(db_path: str):
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get(db_path: str, url: str, *, ttl_seconds: float) -> dict | None:
    """Return the cached preview dict for `url` if present and still fresh
    (or pinned), else None (never cached, or expired and not pinned)."""
    with _cursor(db_path) as conn:
        row = conn.execute(
            "SELECT data, fetched_at, pinned FROM previews WHERE url = ?", (url,)
        ).fetchone()
    if row is None:
        return None
    data_json, fetched_at, pinned = row
    if not pinned and (time.time() - fetched_at > ttl_seconds):
        return None
    return json.loads(data_json)


def set(db_path: str, url: str, data: dict, *, pinned: bool = False) -> None:
    with _cursor(db_path) as conn:
        conn.execute(
            "INSERT INTO previews (url, data, fetched_at, pinned) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(url) DO UPDATE SET data = excluded.data, "
            "fetched_at = excluded.fetched_at, pinned = excluded.pinned",
            (url, json.dumps(data), time.time(), int(pinned)),
        )


def delete(db_path: str, url: str) -> bool:
    """Remove a cache entry. Returns True if something was actually
    removed, False if there was no entry for that URL - used by the
    admin-only DELETE /admin/cache route."""
    with _cursor(db_path) as conn:
        cur = conn.execute("DELETE FROM previews WHERE url = ?", (url,))
        return cur.rowcount > 0


def stats(db_path: str) -> dict:
    """Cheap visibility into cache size - used by the free /cache-stats route."""
    with _cursor(db_path) as conn:
        (count,) = conn.execute("SELECT COUNT(*) FROM previews").fetchone()
        (pinned_count,) = conn.execute(
            "SELECT COUNT(*) FROM previews WHERE pinned = 1"
        ).fetchone()
    return {"cached_urls": count, "pinned_urls": pinned_count}
