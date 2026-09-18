"""Tests for role-first scoring in jobboard.pipeline.score."""

from __future__ import annotations

from dataclasses import replace

from jobboard.pipeline.score import ProfileScorer


def test_exact_target_role_scores_high(profile, seo_job):
    result = ProfileScorer().score(seo_job, profile)
    assert result.percentage >= 80
    assert result.role_match == "SEO"


def test_adjacent_marketing_role_is_applicable_but_ranks_lower(profile, seo_job, adjacent_marketing_job):
    exact = ProfileScorer().score(seo_job, profile)
    adjacent = ProfileScorer().score(adjacent_marketing_job, profile)

    assert adjacent.role_match == "Marketing"
    # Still worth surfacing, just behind the specialist role.
    assert 40 <= adjacent.percentage < exact.percentage


def test_unrelated_role_scores_near_zero_despite_domain_words(profile, unrelated_job):
    """'campaign' and 'funnel' in an engineering JD must not fake a match."""
    result = ProfileScorer().score(unrelated_job, profile)
    assert result.role_match is None
    assert result.percentage < 10


def test_role_in_title_outranks_role_only_in_description(profile, seo_job):
    body_only = replace(
        seo_job,
        title="Specialist, Digital Experience",
        description="You will act as our seo specialist across the marketing team.",
    )
    assert ProfileScorer().score(seo_job, profile).percentage > ProfileScorer().score(body_only, profile).percentage


def test_leadership_titles_are_penalized(profile, seo_job):
    director = replace(seo_job, title="Director of SEO")
    result = ProfileScorer().score(director, profile)
    assert any("director" in p for p in result.penalties)
    assert result.percentage < ProfileScorer().score(seo_job, profile).percentage


def test_junior_titles_are_penalized(profile, seo_job):
    """5+ years of experience means a student/intern posting is a mismatch."""
    intern = replace(seo_job, title="Marketing Student Assistant")
    result = ProfileScorer().score(intern, profile)
    assert any("student" in p for p in result.penalties)


def test_excessive_experience_ask_is_penalized(profile, seo_job):
    senior = replace(seo_job, description=seo_job.description + " Requires 12 years of experience.")
    result = ProfileScorer().score(senior, profile)
    assert any("12+ years" in p for p in result.penalties)


def test_score_is_clamped_between_0_and_100(profile, seo_job, unrelated_job):
    saturated = replace(
        seo_job,
        title="SEO Specialist and Digital Marketing Manager",
        tags=["technical seo", "google analytics 4", "keyword research", "hubspot", "link building"],
    )
    assert ProfileScorer().score(saturated, profile).percentage <= 100

    floored = replace(unrelated_job, title="Director of Engineering")
    assert ProfileScorer().score(floored, profile).percentage >= 0


def test_matched_and_missing_skills_are_reported(profile, seo_job):
    result = ProfileScorer().score(seo_job, profile)
    assert "technical seo" in result.matched_keywords
    assert "keyword research" in result.matched_keywords
    assert "hubspot" in result.missing_keywords
