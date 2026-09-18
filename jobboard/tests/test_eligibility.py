"""Tests for country-eligibility classification."""

from __future__ import annotations

from dataclasses import replace

import pytest

from jobboard.pipeline import eligibility
from jobboard.pipeline.eligibility import Eligibility, classify, filter_eligible


@pytest.fixture(autouse=True)
def clear_structured():
    eligibility.STRUCTURED_RESTRICTIONS.clear()
    yield
    eligibility.STRUCTURED_RESTRICTIONS.clear()


def _classify(job, profile):
    elig = profile.eligibility
    return classify(
        job,
        country=elig["country"],
        timezone_offset=elig["timezone_offset"],
        open_terms=elig["open_location_terms"],
        blocked_terms=elig["blocked_location_terms"],
        hard_exclude_phrases=profile.geo_hard_exclude_phrases,
    )


def test_worldwide_location_is_open(profile, seo_job):
    assert _classify(seo_job, profile).status is Eligibility.OPEN


def test_us_only_location_is_blocked(profile, us_only_job):
    assert _classify(us_only_job, profile).status is Eligibility.BLOCKED


def test_bare_remote_is_unconfirmed(profile, seo_job):
    """No region stated is genuinely unknown - not a silent pass or fail."""
    assert _classify(replace(seo_job, location="Remote"), profile).status is Eligibility.UNCONFIRMED


def test_multi_region_list_containing_apac_is_open(profile, seo_job):
    """'LATAM, Europe, USA, APAC' includes a region covering Bangladesh."""
    job = replace(seo_job, location="LATAM, Europe, USA, Canada, APAC")
    assert _classify(job, profile).status is Eligibility.OPEN


def test_authorization_demand_in_body_blocks_a_friendly_location(profile, seo_job):
    job = replace(seo_job, location="Anywhere", description="Great role. Must reside in the United States.")
    result = _classify(job, profile)
    assert result.status is Eligibility.BLOCKED
    assert "must reside in" in result.reason


def test_structured_restrictions_are_trusted_over_text(profile, seo_job):
    eligibility.STRUCTURED_RESTRICTIONS[seo_job.external_id] = {
        "locations": ["United States"],
        "timezones": [],
    }
    assert _classify(seo_job, profile).status is Eligibility.BLOCKED


def test_structured_empty_restrictions_mean_open(profile, seo_job):
    eligibility.STRUCTURED_RESTRICTIONS[seo_job.external_id] = {"locations": [], "timezones": []}
    assert _classify(seo_job, profile).status is Eligibility.OPEN


def test_structured_timezone_outside_dhaka_offset_is_blocked(profile, seo_job):
    """Dhaka is UTC+6; a US-hours-only posting excludes it."""
    eligibility.STRUCTURED_RESTRICTIONS[seo_job.external_id] = {
        "locations": [],
        "timezones": [-8, -7, -6, -5],
    }
    assert _classify(seo_job, profile).status is Eligibility.BLOCKED


def test_filter_keeps_open_and_unconfirmed_drops_blocked(profile, seo_job, us_only_job):
    unconfirmed = replace(seo_job, external_id="9", location="Remote")
    elig = profile.eligibility

    kept = filter_eligible(
        [seo_job, us_only_job, unconfirmed],
        country=elig["country"],
        timezone_offset=elig["timezone_offset"],
        open_terms=elig["open_location_terms"],
        blocked_terms=elig["blocked_location_terms"],
        hard_exclude_phrases=profile.geo_hard_exclude_phrases,
    )

    assert [job.external_id for job, _ in kept] == ["1", "9"]
