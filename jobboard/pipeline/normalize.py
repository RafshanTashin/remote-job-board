"""Location normalization, dedupe hashing, and hard geo/authorization filters."""

from __future__ import annotations

import hashlib
import logging
import re

from jobboard.sources.base import NormalizedJob

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_location(location: str) -> str:
    """Lowercase, collapse whitespace, and canonicalize a free-text location string."""
    if not location:
        return "remote"
    cleaned = _WHITESPACE_RE.sub(" ", location).strip().lower()
    cleaned = cleaned.replace("worldwide", "").replace("anywhere", "")
    cleaned = cleaned.strip(" ,-")
    return cleaned or "remote"


def compute_hash(company: str, title: str, location: str) -> str:
    """Stable dedupe key: sha256 of lowercased company + title + normalized location."""
    key = f"{company.strip().lower()}|{title.strip().lower()}|{normalize_location(location)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def dedupe(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """Collapse jobs that hash to the same key, keeping the first occurrence."""
    seen: dict[str, NormalizedJob] = {}
    collisions = 0
    for job in jobs:
        key = compute_hash(job.company, job.title, job.location)
        if key in seen:
            collisions += 1
            continue
        seen[key] = job
    if collisions:
        logger.info("dedupe collapsed %d duplicate listing(s)", collisions)
    return list(seen.values())


def find_hard_exclude_phrase(job: NormalizedJob, phrases: list[str]) -> str | None:
    """Return the first hard-exclude phrase found in the job's text, or None."""
    haystack = f"{job.title}\n{job.description}\n{job.location}".lower()
    for phrase in phrases:
        if phrase in haystack:
            return phrase
    return None


def apply_hard_filters(jobs: list[NormalizedJob], geo_hard_exclude_phrases: list[str]) -> list[NormalizedJob]:
    """Drop jobs that fail the must-be-remote / no-authorization-restriction hard filters.

    Adapters that mix remote and on-site listings (Arbeitnow) already filter
    to remote-only at the source; this stage additionally drops anything
    that explicitly demands a specific work authorization or residency,
    regardless of source.
    """
    kept: list[NormalizedJob] = []
    dropped = 0
    for job in jobs:
        hit = find_hard_exclude_phrase(job, geo_hard_exclude_phrases)
        if hit:
            logger.debug("hard-filtered title=%r company=%r phrase=%r", job.title, job.company, hit)
            dropped += 1
            continue
        kept.append(job)
    if dropped:
        logger.info("hard filters dropped %d listing(s)", dropped)
    return kept
