"""Hand-crafted sample listings for the demo build (``python main.py --demo``).

Every company name here is fictional. They're scored by exactly the same
engine that scores live listings - only the input is canned.

These deliberately mirror the *shape* of real postings: generic one-word
tags, skills mentioned only in prose, and a realistic mix of region-locked
and open locations. An earlier version gave every sample a tidy tag array
naming each profile skill, which flattered the scorer and hid the fact that
real listings scored near zero.

Each entry pairs a job with how many hours ago it was "first seen", so the
demo has a realistic mix of new and established listings.
"""

from __future__ import annotations

from jobboard.sources.base import NormalizedJob

SAMPLE_JOBS: list[tuple[NormalizedJob, int]] = [
    (
        NormalizedJob(
            source="weworkremotely",
            external_id="demo-1",
            title="SEO Specialist",
            company="Northwind Analytics",
            location="Anywhere",
            url="https://example.com/demo/northwind-seo-specialist",
            description=(
                "Northwind Analytics is a B2B SaaS platform for supply-chain teams. You'll own "
                "technical SEO for the marketing site and docs: audits, on-page fixes, and the "
                "keyword research that decides what we publish next. Day to day you'll live in "
                "Google Analytics 4 and Google Search Console, watch organic traffic against "
                "the content strategy, and work with writers on internal linking across the blog."
            ),
            tags=["seo", "marketing"],
            posted_at="2026-09-15T09:00:00Z",
        ),
        2,
    ),
    (
        NormalizedJob(
            source="himalayas",
            external_id="demo-2",
            title="Digital Marketing Manager",
            company="Fernwood Digital",
            location="Worldwide",
            url="https://example.com/demo/fernwood-digital-marketing-manager",
            description=(
                "Fernwood helps mid-market SaaS companies grow organic revenue. You'll run the "
                "content calendar end to end, brief writers, manage our Google Ads spend against "
                "the same keyword set, and report on the funnel monthly. Comfortable with "
                "landing page testing and email marketing."
            ),
            tags=["marketing"],
            posted_at="2026-09-16T09:00:00Z",
        ),
        18,
    ),
    (
        NormalizedJob(
            source="workingnomads",
            external_id="demo-3",
            title="Content Marketing Manager",
            company="Lumen Stack",
            location="Global",
            url="https://example.com/demo/lumen-content-marketing-manager",
            description=(
                "Own content strategy for a developer-tools company: editorial calendar, "
                "commissioning, and the on-page SEO that makes the work findable. You'll "
                "partner with our search lead on keyword research and report on organic "
                "traffic to the blog."
            ),
            tags=["content", "b2b"],
            posted_at="2026-09-16T09:00:00Z",
        ),
        6,
    ),
    (
        NormalizedJob(
            source="remoteok",
            external_id="demo-4",
            title="Growth Marketer",
            company="Cascade Metrics",
            location="Remote",
            url="https://example.com/demo/cascade-growth-marketer",
            description=(
                "Run acquisition experiments across the signup funnel and report on conversion "
                "in Google Analytics. You'll own paid search alongside lifecycle email, and "
                "work closely with product on activation."
            ),
            tags=["growth"],
            posted_at="2026-09-13T09:00:00Z",
        ),
        30,
    ),
    (
        NormalizedJob(
            source="remotive",
            external_id="demo-5",
            title="Marketing Specialist",
            company="Brightloop",
            location="Remote",
            url="https://example.com/demo/brightloop-marketing-specialist",
            description=(
                "Brightloop is a billing platform for B2B teams. You'll support campaign "
                "execution across channels, keep the blog publishing on schedule, and help "
                "with brand awareness work at trade events."
            ),
            tags=["marketing"],
            posted_at="2026-09-14T09:00:00Z",
        ),
        54,
    ),
    (
        NormalizedJob(
            source="jobicy",
            external_id="demo-6",
            title="SEO Manager",
            company="Halberd Group",
            location="United States",
            url="https://example.com/demo/halberd-seo-manager",
            description=(
                "Lead technical SEO and content strategy for a portfolio of brands. "
                "Applicants must reside in the United States and be authorized to work "
                "in the United States."
            ),
            tags=["seo"],
            posted_at="2026-09-16T09:00:00Z",
        ),
        4,
    ),
    (
        NormalizedJob(
            source="remoteok",
            external_id="demo-7",
            title="Backend Engineer",
            company="Ironclad Systems",
            location="Anywhere",
            url="https://example.com/demo/ironclad-backend-engineer",
            description=(
                "Build Go services and Kubernetes tooling for our payments platform. You'll "
                "also instrument the sales funnel data pipeline and campaign reporting tables."
            ),
            tags=["golang", "kubernetes"],
            posted_at="2026-09-16T09:00:00Z",
        ),
        3,
    ),
    (
        NormalizedJob(
            source="jobicy",
            external_id="demo-8",
            title="Marketing Intern",
            company="Parchment Labs",
            location="Worldwide",
            url="https://example.com/demo/parchment-marketing-intern",
            description="Support the marketing team with social scheduling and blog formatting.",
            tags=["marketing"],
            posted_at="2026-09-11T09:00:00Z",
        ),
        72,
    ),
]
