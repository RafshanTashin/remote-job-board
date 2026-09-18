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


def compute_hash(company: str, title: str, location: str = "") -> str:
    """Stable dedupe key: sha256 of lowercased company + title.

    Location is accepted but deliberately not hashed. The same posting is
    routinely syndicated across boards with different location wording
    ("Global" on one, "Remote" on another); including it produced duplicate
    cards for a single job.
    """
    key = f"{company.strip().lower()}|{title.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def drop_excluded_roles(jobs: list[NormalizedJob], excluded_title_terms: list[str]) -> list[NormalizedJob]:
    """Remove whole categories of role the candidate never applies to.

    Engineering and internship postings scored low anyway, but they were
    still taking up space on the dashboard. Matching is on the title only -
    a marketing role that merely mentions working with engineers stays.
    """
    kept: list[NormalizedJob] = []
    dropped = 0
    for job in jobs:
        title = _WHITESPACE_RE.sub(" ", job.title.lower()).replace("-", " ")
        if any(re.search(r"\b" + re.escape(term.strip()), title) for term in excluded_title_terms):
            dropped += 1
            continue
        kept.append(job)
    if dropped:
        logger.info("dropped %d listing(s) in excluded role categories", dropped)
    return kept


def dedupe(jobs: list[NormalizedJob]) -> list[NormalizedJob]:
    """Collapse jobs that hash to the same key, keeping the first occurrence."""
    seen: dict[str, NormalizedJob] = {}
    collisions = 0
    for job in jobs:
        key = compute_hash(job.company, job.title)
        if key in seen:
            collisions += 1
            continue
        seen[key] = job
    if collisions:
        logger.info("dedupe collapsed %d duplicate listing(s)", collisions)
    return list(seen.values())


def dedupe_scored(pairs: list[tuple]) -> list[tuple]:
    """Collapse duplicate (job, verdict) pairs, keeping the best-eligibility copy.

    When a syndicated posting appears once as OPEN and once as UNCONFIRMED,
    the confirmed copy is the useful one to show.
    """
    best: dict[str, tuple] = {}
    collisions = 0
    for job, verdict in pairs:
        key = compute_hash(job.company, job.title)
        existing = best.get(key)
        if existing is None:
            best[key] = (job, verdict)
            continue
        collisions += 1
        if verdict.status.value == "open" and existing[1].status.value != "open":
            best[key] = (job, verdict)
    if collisions:
        logger.info("dedupe collapsed %d duplicate listing(s)", collisions)
    return list(best.values())


