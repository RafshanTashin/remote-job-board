"""Tests for the deterministic keyword scorer in jobboard.pipeline.score."""

from __future__ import annotations

from dataclasses import replace

from jobboard.pipeline.score import KeywordScorer


def test_strong_match_scores_high_with_no_missing_keywords(profile, perfect_match_job):
    result = KeywordScorer().score(perfect_match_job, profile)
    assert result.percentage >= 90
    assert set(result.matched_keywords) == {s.name for s in profile.skills}
    assert result.missing_keywords == []


def test_no_match_scores_zero(profile, no_match_job):
    result = KeywordScorer().score(no_match_job, profile)
    assert result.percentage == 0
    assert result.matched_keywords == []
    assert set(result.missing_keywords) == {s.name for s in profile.skills}


def test_geo_hard_phrase_reduces_score(profile, geo_excluded_job):
    result = KeywordScorer().score(geo_excluded_job, profile)
    clean_job = replace(
        geo_excluded_job,
        description="Strong technical seo and keyword research skills.",
    )
    clean_result = KeywordScorer().score(clean_job, profile)

    assert any("must reside in" in penalty for penalty in result.penalties)
    assert result.percentage < clean_result.percentage


def test_seniority_mismatch_reduces_score(profile, senior_mismatch_job):
    result = KeywordScorer().score(senior_mismatch_job, profile)
    assert any("senior" in penalty for penalty in result.penalties)
    assert result.percentage < 50


def test_score_never_exceeds_100_even_with_redundant_matches(profile):
    every_field_job_kwargs = dict(
        source="remotive",
        external_id="5",
        company="Acme SaaS",
        location="Remote",
        url="https://example.com/jobs/5",
        posted_at="2026-09-17T00:00:00Z",
    )
    from jobboard.sources.base import NormalizedJob

    saturated_job = NormalizedJob(
        title="Technical SEO Google Analytics 4 Keyword Research HubSpot Link Building",
        description="technical seo google analytics 4 keyword research hubspot link building",
        tags=["technical seo", "google analytics 4", "keyword research", "hubspot", "link building"],
        **every_field_job_kwargs,
    )

    result = KeywordScorer().score(saturated_job, profile)

    assert result.percentage == 100.0
    assert result.missing_keywords == []


def test_score_never_drops_below_zero(profile, no_match_job):
    stacked_penalty_job = replace(
        no_match_job,
        description=no_match_job.description + " Must reside in the United States. Senior director role.",
    )
    result = KeywordScorer().score(stacked_penalty_job, profile)
    assert result.percentage == 0
    assert len(result.penalties) == 2


def test_max_score_is_weighted_title_ceiling(profile):
    expected = sum(skill.weight for skill in profile.skills) * 3
    assert profile.max_score == expected
