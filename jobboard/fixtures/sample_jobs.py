"""Hand-crafted sample listings for the demo build (``python main.py --demo``).

Every company name here is fictional. They're scored by exactly the same
engine that scores live listings - only the input is canned.

Each entry pairs a job with how many hours ago it was "first seen", so the
demo dashboard has a realistic mix of new and established listings.
"""

from __future__ import annotations

from jobboard.sources.base import NormalizedJob

SAMPLE_JOBS: list[tuple[NormalizedJob, int]] = [
    (
        NormalizedJob(
            source="remotive",
            external_id="demo-1",
            title="SEO Specialist - Technical SEO & Keyword Research",
            company="Northwind Analytics",
            location="Remote - Worldwide",
            url="https://example.com/demo/northwind-seo-specialist",
            description=(
                "Northwind Analytics is a B2B SaaS platform for supply-chain teams. "
                "You'll own technical SEO audits, on-page SEO improvements, and keyword "
                "research to grow organic pipeline. Day to day you will work in Google "
                "Analytics 4 and Google Search Console, coordinate internal linking across "
                "the docs and blog, and partner with content on the editorial calendar."
            ),
            tags=[
                "technical seo",
                "on-page seo",
                "keyword research",
                "google analytics 4",
                "google search console",
                "b2b saas",
                "internal linking",
                "content strategy",
                "link building",
            ],
            posted_at="2026-09-15T09:00:00Z",
        ),
        2,
    ),
    (
        NormalizedJob(
            source="jobicy",
            external_id="demo-2",
            title="SEO Manager - B2B SaaS",
            company="Fernwood Digital",
            location="Remote (Anywhere)",
            url="https://example.com/demo/fernwood-seo-manager",
            description=(
                "Fernwood Digital helps mid-market B2B SaaS companies grow organic revenue. "
                "As SEO Manager you'll set the technical SEO roadmap, run keyword research "
                "for new content clusters, lead link building outreach, and track pipeline "
                "in HubSpot alongside our content strategy lead."
            ),
            tags=[
                "technical seo",
                "content strategy",
                "keyword research",
                "link building",
                "hubspot",
                "on-page seo",
                "internal linking",
            ],
            posted_at="2026-09-16T09:00:00Z",
        ),
        18,
    ),
    (
        NormalizedJob(
            source="arbeitnow",
            external_id="demo-3",
            title="Digital Marketing Specialist",
            company="Brightloop",
            location="Remote",
            url="https://example.com/demo/brightloop-digital-marketing",
            description=(
                "Brightloop is a B2B SaaS billing platform. You'll run Google Ads campaigns, "
                "manage HubSpot lifecycle workflows, and support content strategy for our "
                "product blog, including light keyword research and on-page SEO for landing pages."
            ),
            tags=[
                "google ads",
                "hubspot",
                "content strategy",
                "keyword research",
                "on-page seo",
                "link building",
                "internal linking",
            ],
            posted_at="2026-09-14T09:00:00Z",
        ),
        60,
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
                "Cascade Metrics is looking for a Growth Marketer to run CRO experiments "
                "across the signup funnel, build growth loops, and report on acquisition in "
                "Google Analytics 4. B2B SaaS experience preferred."
            ),
            tags=["cro", "google analytics 4", "growth"],
            posted_at="2026-09-13T09:00:00Z",
        ),
        72,
    ),
    (
        NormalizedJob(
            source="weworkremotely",
            external_id="demo-5",
            title="Content Marketing Manager",
            company="Lumen Stack",
            location="Remote",
            url="https://example.com/demo/lumen-content-marketing-manager",
            description=(
                "Lumen Stack needs a Content Marketing Manager to own content strategy, "
                "on-page SEO, and internal linking for our developer blog and docs site. "
                "You'll partner with the SEO team on keyword research for our B2B SaaS audience."
            ),
            tags=[
                "content strategy",
                "on-page seo",
                "internal linking",
                "keyword research",
                "b2b saas",
                "link building",
                "hubspot",
            ],
            posted_at="2026-09-16T09:00:00Z",
        ),
        6,
    ),
    (
        NormalizedJob(
            source="jobicy",
            external_id="demo-6",
            title="Marketing Analyst",
            company="Driftwell",
            location="Remote (US or EU hours)",
            url="https://example.com/demo/driftwell-marketing-analyst",
            description=(
                "Driftwell is hiring a Marketing Analyst to build dashboards in Google "
                "Analytics 4 and support the marketing team with weekly reporting."
            ),
            tags=["google analytics 4", "reporting"],
            posted_at="2026-09-12T09:00:00Z",
        ),
        96,
    ),
    (
        NormalizedJob(
            source="remotive",
            external_id="demo-7",
            title="SEO Content Writer",
            company="Parchment Labs",
            location="Remote - Worldwide",
            url="https://example.com/demo/parchment-seo-content-writer",
            description="Write on-page SEO optimized content for a B2B SaaS audience.",
            tags=["on-page seo", "content strategy"],
            posted_at="2026-09-11T09:00:00Z",
        ),
        120,
    ),
    (
        NormalizedJob(
            source="remoteok",
            external_id="demo-8",
            title="Backend Engineer",
            company="Ironclad Systems",
            location="Remote",
            url="https://example.com/demo/ironclad-backend-engineer",
            description="Build backend services in Go and Kubernetes for our payments platform.",
            tags=["golang", "kubernetes"],
            posted_at="2026-09-16T09:00:00Z",
        ),
        3,
    ),
]
