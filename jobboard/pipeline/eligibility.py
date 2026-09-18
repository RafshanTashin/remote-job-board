"""Can the candidate actually apply to this listing from their country?

Most "remote" listings on these boards are remote *within a region* - in a
sample of 308 real listings, two thirds were locked to the US, EU, UK or
LATAM. This stage classifies each listing before it is scored, so blocked
roles never reach the dashboard and genuinely open ones aren't buried.

Sources that publish structured restrictions (Himalayas) are trusted
directly; the rest are classified from their free-text location field,
which is why UNCONFIRMED exists as a distinct outcome rather than being
lumped in with either extreme.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum

from jobboard.sources.base import NormalizedJob

logger = logging.getLogger(__name__)

# Set by adapters that expose machine-readable restrictions, so this stage
# can trust them instead of parsing prose. Keys are job.external_id.
STRUCTURED_RESTRICTIONS: dict[str, dict] = {}


class Eligibility(str, Enum):
    """Whether the candidate can apply from their own country."""

    OPEN = "open"
    UNCONFIRMED = "unconfirmed"
    BLOCKED = "blocked"


@dataclass
class EligibilityResult:
    status: Eligibility
    reason: str


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _contains_term(haystack: str, term: str) -> bool:
    return re.search(r"\b" + re.escape(term) + r"\b", haystack) is not None


def classify_structured(
    restrictions: list[str],
    timezones: list[int],
    *,
    country: str,
    timezone_offset: int,
    open_terms: list[str],
) -> EligibilityResult:
    """Classify from a source's own machine-readable restriction fields.

    An empty ``locationRestrictions`` means the source imposes none, which
    these boards use to mean "hire from anywhere".
    """
    folded = [_fold(r) for r in restrictions]

    if not folded:
        if timezones and timezone_offset not in timezones:
            return EligibilityResult(
                Eligibility.BLOCKED,
                f"timezone restricted to UTC{min(timezones):+d}..{max(timezones):+d}",
            )
        return EligibilityResult(Eligibility.OPEN, "no location restrictions")

    if any(country.lower() in r for r in folded):
        return EligibilityResult(Eligibility.OPEN, f"{country} explicitly allowed")

    if any(any(_contains_term(r, term) for term in open_terms) for r in folded):
        return EligibilityResult(Eligibility.OPEN, f"open region: {', '.join(restrictions[:3])}")

    return EligibilityResult(Eligibility.BLOCKED, f"restricted to {', '.join(restrictions[:3])}")


def classify(
    job: NormalizedJob,
    *,
    country: str,
    timezone_offset: int,
    open_terms: list[str],
    blocked_terms: list[str],
    hard_exclude_phrases: list[str],
) -> EligibilityResult:
    """Classify a listing as OPEN, UNCONFIRMED, or BLOCKED for this candidate."""
    structured = STRUCTURED_RESTRICTIONS.get(job.external_id)
    if structured is not None:
        return classify_structured(
            structured.get("locations", []),
            structured.get("timezones", []),
            country=country,
            timezone_offset=timezone_offset,
            open_terms=open_terms,
        )

    location = _fold(job.location)
    description = _fold(job.description)

    # An explicit authorization/residency demand outranks a friendly location field.
    for phrase in hard_exclude_phrases:
        if phrase in description:
            return EligibilityResult(Eligibility.BLOCKED, f"posting says '{phrase}'")

    if country.lower() in location:
        return EligibilityResult(Eligibility.OPEN, f"{country} named in location")

    open_hits = [t for t in open_terms if _contains_term(location, t)]
    blocked_hits = [t for t in blocked_terms if _contains_term(location, t)]

    # "LATAM, Europe, USA, Canada, APAC" lists several regions; APAC covers
    # Bangladesh, so an open region anywhere in the list wins.
    if open_hits:
        return EligibilityResult(Eligibility.OPEN, f"open region: {open_hits[0]}")
    if blocked_hits:
        return EligibilityResult(Eligibility.BLOCKED, f"restricted to {blocked_hits[0]}")

    if not location or location in {"remote", "remote work", "fully remote", "homeoffice", "remoto"}:
        return EligibilityResult(Eligibility.UNCONFIRMED, "no region stated - verify before applying")

    return EligibilityResult(Eligibility.UNCONFIRMED, f"unrecognized location '{job.location}'")


def filter_eligible(
    jobs: list[NormalizedJob],
    *,
    country: str,
    timezone_offset: int,
    open_terms: list[str],
    blocked_terms: list[str],
    hard_exclude_phrases: list[str],
) -> list[tuple[NormalizedJob, EligibilityResult]]:
    """Drop BLOCKED listings, keeping OPEN and UNCONFIRMED ones with their verdict."""
    kept: list[tuple[NormalizedJob, EligibilityResult]] = []
    counts = {status: 0 for status in Eligibility}

    for job in jobs:
        result = classify(
            job,
            country=country,
            timezone_offset=timezone_offset,
            open_terms=open_terms,
            blocked_terms=blocked_terms,
            hard_exclude_phrases=hard_exclude_phrases,
        )
        counts[result.status] += 1
        if result.status is not Eligibility.BLOCKED:
            kept.append((job, result))

    logger.info(
        "eligibility: open=%d unconfirmed=%d blocked=%d (blocked dropped)",
        counts[Eligibility.OPEN],
        counts[Eligibility.UNCONFIRMED],
        counts[Eligibility.BLOCKED],
    )
    return kept
