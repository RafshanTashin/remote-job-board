"""Adapter for the RemoteOK public API (https://remoteok.com/api).

The API's first array element is a legal/meta notice rather than a job, so
entries lacking an ``id``/``position`` are skipped.
"""

from __future__ import annotations

import logging

from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"


class RemoteOKSource(SourceAdapter):
    name = "remoteok"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(API_URL)
        payload = response.json()
        jobs: list[NormalizedJob] = []
        for item in payload:
            if "id" not in item or "position" not in item:
                continue
            slug = item.get("slug", "")
            url = item.get("url") or (f"https://remoteok.com/remote-jobs/{slug}" if slug else "")
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=str(item["id"]),
                    title=item.get("position", ""),
                    company=item.get("company", ""),
                    location=item.get("location") or "Remote",
                    url=url,
                    description=strip_html(item.get("description", "")),
                    tags=list(item.get("tags") or []),
                    posted_at=item.get("date"),
                )
            )
        return jobs
