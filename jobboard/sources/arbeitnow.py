"""Adapter for the Arbeitnow job board API (https://www.arbeitnow.com/api/job-board-api).

Arbeitnow's feed mixes remote and on-site listings; only entries the API
itself flags as ``remote`` are kept, since that's an authoritative signal
rather than a guess from free-text location.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def _posted_at(created_at: int | None) -> str | None:
    if not created_at:
        return None
    return datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()


class ArbeitnowSource(SourceAdapter):
    name = "arbeitnow"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(API_URL)
        payload = response.json()
        jobs: list[NormalizedJob] = []
        for item in payload.get("data", []):
            if not item.get("remote"):
                continue
            tags = list(item.get("tags") or []) + list(item.get("job_types") or [])
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=str(item.get("slug", "")),
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("location") or "Remote",
                    url=item.get("url", ""),
                    description=strip_html(item.get("description", "")),
                    tags=tags,
                    posted_at=_posted_at(item.get("created_at")),
                )
            )
        return jobs
