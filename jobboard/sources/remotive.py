"""Adapter for the Remotive public API (https://remotive.com/api/remote-jobs)."""

from __future__ import annotations

import logging

from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource(SourceAdapter):
    name = "remotive"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(API_URL)
        payload = response.json()
        jobs: list[NormalizedJob] = []
        for item in payload.get("jobs", []):
            tags = list(item.get("tags") or [])
            category = item.get("category")
            if category:
                tags.append(category)
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("candidate_required_location") or "Remote",
                    url=item.get("url", ""),
                    description=strip_html(item.get("description", "")),
                    tags=tags,
                    posted_at=item.get("publication_date"),
                )
            )
        return jobs
