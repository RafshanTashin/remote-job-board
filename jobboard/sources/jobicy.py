"""Adapter for the Jobicy public API v2 (https://jobicy.com/api/v2/remote-jobs)."""

from __future__ import annotations

import logging

from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

API_URL = "https://jobicy.com/api/v2/remote-jobs"


class JobicySource(SourceAdapter):
    name = "jobicy"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(API_URL)
        payload = response.json()
        jobs: list[NormalizedJob] = []
        for item in payload.get("jobs", []):
            tags = list(item.get("jobIndustry") or []) + list(item.get("jobType") or [])
            description = item.get("jobDescription") or item.get("jobExcerpt") or ""
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=str(item.get("id", "")),
                    title=item.get("jobTitle", ""),
                    company=item.get("companyName", ""),
                    location=item.get("jobGeo") or "Remote",
                    url=item.get("url", ""),
                    description=strip_html(description),
                    tags=tags,
                    posted_at=item.get("pubDate"),
                )
            )
        return jobs
