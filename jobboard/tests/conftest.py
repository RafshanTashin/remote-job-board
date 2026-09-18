"""Shared fixtures: a compact profile and sample normalized listings."""

from __future__ import annotations

import pytest

from jobboard.pipeline.score import Profile, Skill, TargetRole
from jobboard.sources.base import NormalizedJob


@pytest.fixture
def profile() -> Profile:
    return Profile(
        target_roles=[
            TargetRole(
                family="SEO",
                weight=1.0,
                patterns=["seo specialist", "seo manager", "technical seo", "organic growth"],
            ),
            TargetRole(
                family="Digital Marketing",
                weight=0.95,
                patterns=["digital marketing specialist", "digital marketing manager", "digital marketing"],
            ),
            TargetRole(
                family="Marketing",
                weight=0.8,
                patterns=["marketing specialist", "marketing manager", "marketing executive"],
            ),
        ],
        domain_terms=[
            "seo", "keyword", "organic traffic", "content strategy", "campaign",
            "google analytics", "backlink", "landing page", "b2b", "funnel",
        ],
        skills=[
            Skill(name="technical seo", weight=5),
            Skill(name="google analytics 4", weight=4),
            Skill(name="keyword research", weight=4),
            Skill(name="hubspot", weight=3),
            Skill(name="link building", weight=3),
        ],
        skill_target_weight=12,
        years_experience=5,
        seniority_reject_terms=["director", "head of", "intern", "student"],
        reject_years_above=10,
        geo_soft_penalty_phrases=["us timezone"],
        geo_hard_exclude_phrases=["must reside in", "us work authorization"],
        excluded_title_terms=["intern", "engineer", "developer", "frontend", "backend"],
        max_posting_age_days=45,
        eligibility={
            "country": "Bangladesh",
            "timezone_offset": 6,
            "open_location_terms": ["anywhere", "worldwide", "global", "apac", "asia"],
            "blocked_location_terms": ["usa", "united states", "canada", "uk", "europe", "latam"],
        },
    )


@pytest.fixture
def seo_job() -> NormalizedJob:
    """An exact target role, in the title, with domain language in the body."""
    return NormalizedJob(
        source="weworkremotely",
        external_id="1",
        title="SEO Specialist",
        company="Acme SaaS",
        location="Worldwide",
        url="https://example.com/jobs/1",
        description=(
            "Own technical seo and keyword research for our b2b product. You'll "
            "grow organic traffic, run campaign reporting in google analytics, and "
            "improve landing page performance alongside our content strategy lead."
        ),
        tags=["seo", "marketing"],
        posted_at="2026-09-17T00:00:00Z",
    )


@pytest.fixture
def adjacent_marketing_job() -> NormalizedJob:
    """A marketing role that isn't SEO - applicable, but a weaker fit."""
    return NormalizedJob(
        source="remoteok",
        external_id="2",
        title="Marketing Manager",
        company="Widgets Inc",
        location="Anywhere",
        url="https://example.com/jobs/2",
        description="Run our brand campaign calendar and trade show programme for a b2b audience.",
        tags=["marketing"],
        posted_at="2026-09-17T00:00:00Z",
    )


@pytest.fixture
def unrelated_job() -> NormalizedJob:
    """Not a marketing role at all - mentions 'campaign' and 'funnel' anyway."""
    return NormalizedJob(
        source="remoteok",
        external_id="3",
        title="Backend Engineer",
        company="Ironclad Systems",
        location="Anywhere",
        url="https://example.com/jobs/3",
        description=(
            "Build Go services and Kubernetes tooling. You'll support the sales "
            "funnel instrumentation and campaign data pipeline."
        ),
        tags=["golang", "kubernetes"],
        posted_at="2026-09-17T00:00:00Z",
    )


@pytest.fixture
def us_only_job() -> NormalizedJob:
    return NormalizedJob(
        source="jobicy",
        external_id="4",
        title="SEO Specialist",
        company="Acme SaaS",
        location="USA",
        url="https://example.com/jobs/4",
        description="Own technical seo and keyword research.",
        tags=[],
        posted_at="2026-09-17T00:00:00Z",
    )
