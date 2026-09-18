"""Tests for location normalization, dedupe hashing, and hard filters."""

from __future__ import annotations

from dataclasses import replace

from jobboard.pipeline.normalize import apply_hard_filters, compute_hash, dedupe, normalize_location


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


def test_dedupe_collapses_cross_posted_listing(perfect_match_job):
    duplicate = replace(
        perfect_match_job,
        source="remoteok",
        external_id="999",
        url="https://example.com/other-listing",
    )
    result = dedupe([perfect_match_job, duplicate])
    assert len(result) == 1
    assert result[0] is perfect_match_job  # first occurrence wins


def test_dedupe_keeps_distinct_jobs(perfect_match_job, no_match_job):
    result = dedupe([perfect_match_job, no_match_job])
    assert len(result) == 2


def test_apply_hard_filters_drops_authorization_restricted_jobs(geo_excluded_job, no_match_job):
    kept = apply_hard_filters([geo_excluded_job, no_match_job], ["must reside in"])
    assert kept == [no_match_job]
