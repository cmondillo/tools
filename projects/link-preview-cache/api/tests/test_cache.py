from app import cache


def test_miss_when_never_set(tmp_path):
    db = str(tmp_path / "cache.db")
    assert cache.get(db, "https://example.com", ttl_seconds=3600) is None


def test_hit_returns_what_was_set(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://example.com", {"title": "Example"})
    assert cache.get(db, "https://example.com", ttl_seconds=3600) == {"title": "Example"}


def test_different_urls_dont_collide(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://a.example.com", {"title": "A"})
    cache.set(db, "https://b.example.com", {"title": "B"})
    assert cache.get(db, "https://a.example.com", ttl_seconds=3600)["title"] == "A"
    assert cache.get(db, "https://b.example.com", ttl_seconds=3600)["title"] == "B"


def test_expired_entry_is_a_miss(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://example.com", {"title": "Stale"})
    # ttl_seconds=0 means "expired the instant it was written" - avoids
    # sleeping in the test suite to prove expiry actually works.
    assert cache.get(db, "https://example.com", ttl_seconds=0) is None


def test_set_overwrites_existing_entry(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://example.com", {"title": "Old"})
    cache.set(db, "https://example.com", {"title": "New"})
    assert cache.get(db, "https://example.com", ttl_seconds=3600) == {"title": "New"}


def test_stats_counts_distinct_urls(tmp_path):
    db = str(tmp_path / "cache.db")
    assert cache.stats(db) == {"cached_urls": 0, "pinned_urls": 0}
    cache.set(db, "https://a.example.com", {"title": "A"})
    cache.set(db, "https://b.example.com", {"title": "B"})
    assert cache.stats(db) == {"cached_urls": 2, "pinned_urls": 0}


def test_db_path_parent_dir_is_created(tmp_path):
    db = str(tmp_path / "nested" / "dir" / "cache.db")
    cache.set(db, "https://example.com", {"title": "Example"})
    assert cache.get(db, "https://example.com", ttl_seconds=3600)["title"] == "Example"


def test_pinned_entry_never_expires(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://coinbase.com", {"title": "Coinbase"}, pinned=True)
    # ttl_seconds=0 would expire a normal entry instantly - pinned ignores it.
    assert cache.get(db, "https://coinbase.com", ttl_seconds=0)["title"] == "Coinbase"


def test_unpinned_entry_still_expires_normally(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://example.com", {"title": "Example"}, pinned=False)
    assert cache.get(db, "https://example.com", ttl_seconds=0) is None


def test_stats_counts_pinned_separately(tmp_path):
    db = str(tmp_path / "cache.db")
    cache.set(db, "https://a.example.com", {"title": "A"}, pinned=True)
    cache.set(db, "https://b.example.com", {"title": "B"}, pinned=False)
    assert cache.stats(db) == {"cached_urls": 2, "pinned_urls": 1}


def test_migration_adds_pinned_column_to_a_pre_existing_db(tmp_path):
    """Simulates a db created before the `pinned` column existed (the
    already-deployed cache.db on Render) - inserting a row with the
    old 3-column schema, then confirming the new code still works
    against it without crashing or losing the row."""
    import sqlite3

    db = str(tmp_path / "cache.db")
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE previews (url TEXT PRIMARY KEY, data TEXT NOT NULL, fetched_at REAL NOT NULL)"
    )
    conn.execute(
        "INSERT INTO previews VALUES (?, ?, ?)",
        ("https://example.com", '{"title": "Pre-migration"}', 0.0),
    )
    conn.commit()
    conn.close()

    # ttl_seconds=1e12 so the very old fetched_at=0 timestamp doesn't just
    # look expired - this test is about the migration, not TTL.
    assert cache.get(db, "https://example.com", ttl_seconds=1e12)["title"] == "Pre-migration"
    cache.set(db, "https://new.example.com", {"title": "New"}, pinned=True)
    assert cache.get(db, "https://new.example.com", ttl_seconds=0)["title"] == "New"
