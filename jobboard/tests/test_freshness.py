"""Tests for dropping closed and stale postings."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from jobboard.pipeline.normalize import drop_expired, parse_date

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "value",
    [
        "2026-09-15T09:00:00Z",
        "2026-09-15T09:00:00+00:00",
        "2026-09-15T09:00:00",
        "Tue, 15 Sep 2026 09:00:00 +0000",
        "2026-09-15T05:00:00-04:00",
    ],
)
def test_parse_date_handles_every_source_format(value):
    """JSON APIs emit ISO variants, RSS emits RFC 2822."""
    parsed = parse_date(value)
    assert parsed is not None
    assert parsed.tzinfo is not None


@pytest.mark.parametrize("value", [None, "", "not a date", "yesterday"])
def test_parse_date_returns_none_for_unusable_values(value):
    assert parse_date(value) is None


def test_listing_past_its_closing_date_is_dropped(seo_job):
    closed = replace(seo_job, expires_at="2026-09-01T00:00:00Z")
    assert drop_expired([closed], 45, NOW) == []


def test_listing_with_a_future_closing_date_is_kept(seo_job):
    open_job = replace(seo_job, posted_at="2026-09-17T00:00:00Z", expires_at="2026-10-30T00:00:00Z")
    assert drop_expired([open_job], 45, NOW) == [open_job]


def test_closing_date_beats_age(seo_job):
    """An old posting the source still lists as open is kept."""
    old_but_open = replace(
        seo_job,
        posted_at="2026-01-01T00:00:00Z",
        expires_at="2026-12-01T00:00:00Z",
    )
    assert drop_expired([old_but_open], 45, NOW) == [old_but_open]


def test_stale_posting_without_a_closing_date_is_dropped(seo_job):
    stale = replace(seo_job, posted_at=(NOW - timedelta(days=90)).isoformat())
    assert drop_expired([stale], 45, NOW) == []


def test_recent_posting_is_kept(seo_job):
    fresh = replace(seo_job, posted_at=(NOW - timedelta(days=3)).isoformat())
    assert drop_expired([fresh], 45, NOW) == [fresh]


def test_listing_without_any_date_is_kept(seo_job):
    """A missing date is unknown, not expired - don't discard a good role over it."""
    undated = replace(seo_job, posted_at=None, expires_at=None)
    assert drop_expired([undated], 45, NOW) == [undated]
