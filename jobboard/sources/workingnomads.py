"""Adapter for the Working Nomads API (https://www.workingnomads.com/api/exposed_jobs/).

Remote-first board that states region eligibility plainly in its location
field ("Global", "Internationally located (not in the US, CA, UK...)"),
which the eligibility stage reads directly.
"""

from __future__ import annotations

import logging

from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

API_URL = "https://www.workingnomads.com/api/exposed_jobs/"


class WorkingNomadsSource(SourceAdapter):
    name = "workingnomads"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(API_URL)
        payload = response.json()

        jobs: list[NormalizedJob] = []
        for item in payload:
            raw_tags = item.get("tags") or ""
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            category = item.get("category_name")
            if category:
                tags.append(category)

            url = item.get("url", "")
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=str(item.get("id") or url),
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("location") or "Remote",
                    url=url,
                    description=strip_html(item.get("description", "")),
                    tags=tags,
                    posted_at=item.get("pub_date"),
                )
            )
        return jobs
