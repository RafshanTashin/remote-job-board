"""Tests for location normalization, dedupe hashing, and hard filters."""

from __future__ import annotations

from dataclasses import replace

from jobboard.pipeline.normalize import compute_hash, dedupe, normalize_location


def test_normalize_location_collapses_case_and_whitespace():
    assert normalize_location("  Remote  -  Worldwide ") == normalize_location("remote worldwide")


def test_normalize_location_defaults_empty_to_remote():
    assert normalize_location("") == "remote"


def test_compute_hash_is_stable_across_formatting_variants():
    a = compute_hash("Acme Inc", "SEO Specialist", "Remote")
    b = compute_hash("acme inc", "seo specialist", "  Remote  ")
    assert a == b


def test_compute_hash_differs_for_different_jobs():
    a = compute_hash("Acme Inc", "SEO Specialist", "Remote")
    b = compute_hash("Acme Inc", "SEO Manager", "Remote")
    assert a != b


def test_dedupe_collapses_cross_posted_listing(seo_job):
    duplicate = replace(
        seo_job,
        source="remoteok",
        external_id="999",
        url="https://example.com/other-listing",
    )
    result = dedupe([seo_job, duplicate])
    assert len(result) == 1
    assert result[0] is seo_job  # first occurrence wins


def test_dedupe_keeps_distinct_jobs(seo_job, unrelated_job):
    result = dedupe([seo_job, unrelated_job])
    assert len(result) == 2


def test_engineering_and_intern_titles_are_dropped(profile, seo_job, unrelated_job):
    from jobboard.pipeline.normalize import drop_excluded_roles

    intern = replace(seo_job, external_id="5", title="Marketing Intern")
    frontend = replace(seo_job, external_id="6", title="Senior Frontend Developer")

    kept = drop_excluded_roles(
        [seo_job, unrelated_job, intern, frontend], profile.excluded_title_terms
    )

    assert [job.title for job in kept] == ["SEO Specialist"]


def test_excluded_terms_only_match_the_title(profile, seo_job):
    """A marketing role that mentions working with engineers must survive."""
    from jobboard.pipeline.normalize import drop_excluded_roles

    job = replace(seo_job, description="You'll partner with our engineering team and backend developers daily.")
    assert drop_excluded_roles([job], profile.excluded_title_terms) == [job]


def test_syndicated_listing_with_different_location_wording_collapses(seo_job):
    """The same posting appears as 'Global' on one board and 'Remote' on another."""
    other_board = replace(seo_job, source="workingnomads", location="Remote")
    assert len(dedupe([seo_job, other_board])) == 1


def test_dedupe_scored_prefers_the_location_confirmed_copy(seo_job):
    from jobboard.pipeline.eligibility import Eligibility, EligibilityResult
    from jobboard.pipeline.normalize import dedupe_scored

    unconfirmed = (replace(seo_job, location="Remote"), EligibilityResult(Eligibility.UNCONFIRMED, "no region"))
    confirmed = (seo_job, EligibilityResult(Eligibility.OPEN, "worldwide"))

    result = dedupe_scored([unconfirmed, confirmed])

    assert len(result) == 1
    assert result[0][1].status is Eligibility.OPEN
