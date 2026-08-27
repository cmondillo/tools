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
    assert cache.stats(db) == {"cached_urls": 0}
    cache.set(db, "https://a.example.com", {"title": "A"})
    cache.set(db, "https://b.example.com", {"title": "B"})
    assert cache.stats(db) == {"cached_urls": 2}


def test_db_path_parent_dir_is_created(tmp_path):
    db = str(tmp_path / "nested" / "dir" / "cache.db")
    cache.set(db, "https://example.com", {"title": "Example"})
    assert cache.get(db, "https://example.com", ttl_seconds=3600)["title"] == "Example"
