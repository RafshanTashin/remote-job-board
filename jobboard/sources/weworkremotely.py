"""Adapter for the We Work Remotely marketing RSS feed.

WWR titles are formatted as "Company: Job Title", so the company name is
split out of the title rather than provided as a separate field.
"""

from __future__ import annotations

import logging

import feedparser

from jobboard.sources.base import NormalizedJob, SourceAdapter, fetch_url, strip_html

logger = logging.getLogger(__name__)

# The per-category feeds (…/categories/remote-marketing-jobs.rss) now answer
# 301 with an empty body, which silently yielded zero listings. The all-jobs
# feed still works; relevance is decided by scoring anyway.
FEED_URL = "https://weworkremotely.com/remote-jobs.rss"


def _split_title(raw_title: str) -> tuple[str, str]:
    company, sep, title = raw_title.partition(": ")
    if not sep:
        return "", raw_title.strip()
    return company.strip(), title.strip()


class WeWorkRemotelySource(SourceAdapter):
    name = "weworkremotely"

    def fetch(self) -> list[NormalizedJob]:
        response = fetch_url(FEED_URL)
        parsed = feedparser.parse(response.content)
        jobs: list[NormalizedJob] = []
        for entry in parsed.entries:
            company, title = _split_title(entry.get("title", ""))
            tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
            jobs.append(
                NormalizedJob(
                    source=self.name,
                    external_id=entry.get("id") or entry.get("link", ""),
                    title=title,
                    company=company,
                    location="Remote",
                    url=entry.get("link", ""),
                    description=strip_html(entry.get("summary", "")),
                    tags=tags,
                    posted_at=entry.get("published"),
                )
            )
        return jobs
