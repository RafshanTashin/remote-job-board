"""Adapter for the Himalayas public API (https://himalayas.app/jobs/api).

Himalayas is the only source here that publishes machine-readable hiring
restrictions (``locationRestrictions``, ``timezoneRestrictions``), so this
adapter records them for the eligibility stage instead of leaving it to
parse a free-text location field.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from jobboard.pipeline import eligibility
from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

API_URL = "https://himalayas.app/jobs/api"
PAGE_LIMIT = 100


def _from_unix(value: int | None) -> str | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


class HimalayasSource(SourceAdapter):
    name = "himalayas"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(API_URL, params={"limit": str(PAGE_LIMIT)})
        payload = response.json()

        jobs: list[NormalizedJob] = []
        for item in payload.get("jobs", []):
            external_id = str(item.get("guid") or item.get("applicationLink", ""))
            restrictions = list(item.get("locationRestrictions") or [])
            timezones = [int(t) for t in (item.get("timezoneRestrictions") or []) if isinstance(t, (int, float))]

            eligibility.STRUCTURED_RESTRICTIONS[external_id] = {
                "locations": restrictions,
                "timezones": timezones,
            }

            tags = list(item.get("categories") or []) + list(item.get("seniority") or [])
            description = item.get("description") or item.get("excerpt") or ""

            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=external_id,
                    title=item.get("title", ""),
                    company=item.get("companyName", ""),
                    location=", ".join(restrictions) if restrictions else "Worldwide",
                    url=item.get("applicationLink", ""),
                    description=strip_html(description),
                    tags=tags,
                    posted_at=_from_unix(item.get("pubDate")),
                    expires_at=_from_unix(item.get("expiryDate")),
                )
            )
        return jobs
