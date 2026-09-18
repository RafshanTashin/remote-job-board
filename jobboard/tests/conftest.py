"""Shared fixtures: a compact profile and sample normalized job listings."""

from __future__ import annotations

import pytest

from jobboard.pipeline.score import Profile, Skill
from jobboard.sources.base import NormalizedJob


@pytest.fixture
def profile() -> Profile:
    return Profile(
        target_titles=["SEO Specialist", "SEO Manager"],
        skills=[
            Skill(name="technical seo", weight=5),
            Skill(name="google analytics 4", weight=4),
            Skill(name="keyword research", weight=4),
            Skill(name="hubspot", weight=3),
            Skill(name="link building", weight=3),
        ],
        min_years=2,
        max_years=4,
        geo_hard_exclude_phrases=["must reside in", "us work authorization"],
        geo_soft_penalty_phrases=["us timezone"],
        seniority_overqualified_terms=["senior", "staff", "director"],
        seniority_underqualified_terms=["intern", "entry level"],
    )


@pytest.fixture
def perfect_match_job() -> NormalizedJob:
    return NormalizedJob(
        source="remotive",
        external_id="1",
        title="Technical SEO & Keyword Research Specialist",
        company="Acme SaaS",
        location="Remote - Worldwide",
        url="https://example.com/jobs/1",
        description=(
            "We need someone strong in technical seo, google analytics 4, "
            "and keyword research to grow our B2B SaaS blog."
        ),
        tags=["hubspot", "link building"],
        posted_at="2026-09-17T00:00:00Z",
    )


@pytest.fixture
def no_match_job() -> NormalizedJob:
    return NormalizedJob(
        source="remoteok",
        external_id="2",
        title="Backend Engineer",
        company="Widgets Inc",
        location="Remote",
        url="https://example.com/jobs/2",
        description="Build backend services in Go and Kubernetes.",
        tags=["golang", "kubernetes"],
        posted_at="2026-09-17T00:00:00Z",
    )


@pytest.fixture
def geo_excluded_job() -> NormalizedJob:
    return NormalizedJob(
        source="jobicy",
        external_id="3",
        title="SEO Specialist",
        company="Acme SaaS",
        location="Remote (US)",
        url="https://example.com/jobs/3",
        description="Strong technical seo and keyword research skills. Must reside in the United States.",
        tags=[],
        posted_at="2026-09-17T00:00:00Z",
    )


@pytest.fixture
def senior_mismatch_job() -> NormalizedJob:
    return NormalizedJob(
        source="arbeitnow",
        external_id="4",
        title="Senior SEO Manager",
        company="Acme SaaS",
        location="Remote",
        url="https://example.com/jobs/4",
        description="Lead our technical seo and keyword research strategy.",
        tags=[],
        posted_at="2026-09-17T00:00:00Z",
    )
