"""Tests for SQLite persistence and the live-listing window."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from jobboard.pipeline.score import ProfileScorer
from jobboard.pipeline.store import init_db, query_matches, upsert_job


@pytest.fixture
def conn():
    connection = init_db(":memory:")
    yield connection
    connection.close()


def test_stale_listings_are_not_rendered(conn, profile, seo_job, adjacent_marketing_job):
    """A listing that stopped appearing in the feeds is closed or filled."""
    now = datetime.now(timezone.utc)
    scorer = ProfileScorer()

    upsert_job(conn, seo_job, scorer.score(seo_job, profile), now)
    upsert_job(
        conn,
        adjacent_marketing_job,
        scorer.score(adjacent_marketing_job, profile),
        now - timedelta(days=10),
    )
    conn.commit()

    live = query_matches(conn, 0, now)

    assert [job.title for job in live] == ["SEO Specialist"]


def test_first_seen_survives_a_refresh(conn, profile, seo_job):
    """Re-seeing a listing must not reset how long it has been known."""
    discovered = datetime.now(timezone.utc) - timedelta(days=3)
    now = datetime.now(timezone.utc)
    scorer = ProfileScorer()

    upsert_job(conn, seo_job, scorer.score(seo_job, profile), discovered)
    upsert_job(conn, seo_job, scorer.score(seo_job, profile), now)
    conn.commit()

    stored = query_matches(conn, 0, now)

    assert len(stored) == 1
    assert stored[0].first_seen == discovered.isoformat()
    assert stored[0].is_new is False


def test_newly_discovered_listing_is_flagged_new(conn, profile, seo_job):
    now = datetime.now(timezone.utc)
    upsert_job(conn, seo_job, ProfileScorer().score(seo_job, profile), now)
    conn.commit()

    assert query_matches(conn, 0, now)[0].is_new is True


def test_eligibility_verdict_round_trips(conn, profile, seo_job):
    now = datetime.now(timezone.utc)
    upsert_job(conn, seo_job, ProfileScorer().score(seo_job, profile), now, "open", "worldwide")
    conn.commit()

    stored = query_matches(conn, 0, now)[0]

    assert stored.eligibility == "open"
    assert stored.eligibility_reason == "worldwide"
    assert stored.role_match == "SEO"
