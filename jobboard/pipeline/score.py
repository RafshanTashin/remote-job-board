"""Deterministic keyword-based scoring of a job against the candidate profile.

The scorer is intentionally isolated behind ``get_scorer()`` so a future
LLM-backed implementation can be swapped in via the ``USE_LLM`` environment
flag without any caller needing to change. Only the keyword scorer is
implemented for v1.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from jobboard.sources.base import NormalizedJob

logger = logging.getLogger(__name__)

TITLE_WEIGHT = 3
DESCRIPTION_WEIGHT = 1
TAG_WEIGHT = 2

# Penalties are expressed as a fraction of a profile's max_score rather than
# a fixed point value, so they stay meaningful regardless of how many
# skills (and how heavily weighted) a given profile.json defines.
GEO_HARD_PENALTY_FRACTION = 0.35
GEO_SOFT_PENALTY_FRACTION = 0.15
SENIORITY_PENALTY_FRACTION = 0.25

_YEARS_RE = re.compile(r"(\d{1,2})\+?\s*(?:-|to)?\s*(\d{1,2})?\+?\s*years?", re.IGNORECASE)

_KEYWORD_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _fold(text: str) -> str:
    """Lowercase and treat hyphens as spaces so 'on-page SEO' matches 'on page seo'."""
    return text.lower().replace("-", " ")


def _contains_keyword(haystack: str, keyword: str) -> bool:
    """Whole-word/phrase containment check.

    Plain substring containment lets short acronyms like "CRO" match inside
    unrelated words ("acr" + "oss" -> "across", "cr" + "oss-functional"),
    which silently inflated scores for almost every listing. Word-boundary
    matching keeps "CRO" as its own token while still matching multi-word
    phrases like "keyword research" as a contiguous unit.
    """
    pattern = _KEYWORD_PATTERN_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
        _KEYWORD_PATTERN_CACHE[keyword] = pattern
    return pattern.search(haystack) is not None


@dataclass
class Skill:
    """A single weighted keyword from the candidate's profile."""

    name: str
    weight: float


@dataclass
class Profile:
    """The candidate profile a job is scored against."""

    target_titles: list[str]
    skills: list[Skill]
    min_years: int
    max_years: int
    geo_hard_exclude_phrases: list[str]
    geo_soft_penalty_phrases: list[str]
    seniority_overqualified_terms: list[str]
    seniority_underqualified_terms: list[str]

    @property
    def max_score(self) -> float:
        """The ceiling used to normalize raw points into a percentage.

        Calibrated against a skill appearing in the title (the
        highest-weighted field) for every skill, rather than the (unrealistic)
        case of every skill appearing in title *and* description *and* tags.
        A listing that also matches in description/tags is rewarded above
        this ceiling, which is why scores must be capped at 100 downstream.
        """
        return sum(skill.weight for skill in self.skills) * TITLE_WEIGHT

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        """Load a profile from a profile.json file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        skills = [Skill(name=s["name"], weight=float(s["weight"])) for s in data["skills"]]
        seniority = data.get("seniority", {})
        return cls(
            target_titles=list(data.get("target_titles", [])),
            skills=skills,
            min_years=int(seniority.get("min_years", 0)),
            max_years=int(seniority.get("max_years", 99)),
            geo_hard_exclude_phrases=[p.lower() for p in data.get("geo_hard_exclude_phrases", [])],
            geo_soft_penalty_phrases=[p.lower() for p in data.get("geo_soft_penalty_phrases", [])],
            seniority_overqualified_terms=[t.lower() for t in data.get("seniority_overqualified_terms", [])],
            seniority_underqualified_terms=[t.lower() for t in data.get("seniority_underqualified_terms", [])],
        )


@dataclass
class ScoreResult:
    """The outcome of scoring one job: the percentage plus what drove it."""

    percentage: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    raw_score: float
    max_score: float
    penalties: list[str] = field(default_factory=list)


def _required_years(text: str) -> int | None:
    """Best-effort extraction of the highest years-of-experience figure mentioned."""
    matches = _YEARS_RE.findall(text)
    years = [int(group) for pair in matches for group in pair if group]
    return max(years) if years else None


def _seniority_penalty(job: NormalizedJob, profile: Profile) -> str | None:
    haystack = _fold(f"{job.title} {job.description}")
    for term in profile.seniority_overqualified_terms:
        if _contains_keyword(haystack, _fold(term)):
            return f"seniority: '{term.strip()}' suggests a more senior role than targeted"
    for term in profile.seniority_underqualified_terms:
        if _contains_keyword(haystack, _fold(term)):
            return f"seniority: '{term.strip()}' suggests a more junior role than targeted"
    required = _required_years(haystack)
    if required is not None and required > profile.max_years + 2:
        return f"seniority: posting asks for {required}+ years"
    return None


def _geo_penalty(job: NormalizedJob, profile: Profile) -> tuple[str | None, float]:
    haystack = _fold(f"{job.title} {job.description} {job.location}")
    for phrase in profile.geo_hard_exclude_phrases:
        if _contains_keyword(haystack, _fold(phrase)):
            return f"geo: '{phrase}'", GEO_HARD_PENALTY_FRACTION
    for phrase in profile.geo_soft_penalty_phrases:
        if _contains_keyword(haystack, _fold(phrase)):
            return f"geo: '{phrase}'", GEO_SOFT_PENALTY_FRACTION
    return None, 0.0


class Scorer(Protocol):
    """The interface every scorer implementation (keyword-based or LLM) must satisfy."""

    def score(self, job: NormalizedJob, profile: Profile) -> ScoreResult: ...


class KeywordScorer:
    """Weighted keyword hits across title/description/tags, minus penalties, normalized to 0-100."""

    def score(self, job: NormalizedJob, profile: Profile) -> ScoreResult:
        title = _fold(job.title)
        description = _fold(job.description)
        tags = _fold(" ".join(job.tags))

        raw_score = 0.0
        matched: list[str] = []
        missing: list[str] = []

        for skill in profile.skills:
            keyword = _fold(skill.name)
            hit = False
            if _contains_keyword(title, keyword):
                raw_score += skill.weight * TITLE_WEIGHT
                hit = True
            if _contains_keyword(description, keyword):
                raw_score += skill.weight * DESCRIPTION_WEIGHT
                hit = True
            if _contains_keyword(tags, keyword):
                raw_score += skill.weight * TAG_WEIGHT
                hit = True
            (matched if hit else missing).append(skill.name)

        penalties: list[str] = []

        geo_reason, geo_fraction = _geo_penalty(job, profile)
        if geo_reason:
            raw_score -= geo_fraction * profile.max_score
            penalties.append(geo_reason)

        seniority_reason = _seniority_penalty(job, profile)
        if seniority_reason:
            raw_score -= SENIORITY_PENALTY_FRACTION * profile.max_score
            penalties.append(seniority_reason)

        if profile.max_score:
            percentage = max(0.0, min(100.0, (raw_score / profile.max_score) * 100))
        else:
            percentage = 0.0

        return ScoreResult(
            percentage=round(percentage, 1),
            matched_keywords=matched,
            missing_keywords=missing,
            raw_score=raw_score,
            max_score=profile.max_score,
            penalties=penalties,
        )


class LLMScorer:
    """Placeholder seam for a future LLM-backed scorer. Not implemented in v1."""

    def score(self, job: NormalizedJob, profile: Profile) -> ScoreResult:
        raise NotImplementedError(
            "LLM scoring is not implemented yet. Unset USE_LLM (or set it to false) to use KeywordScorer."
        )


def get_scorer() -> Scorer:
    """Return the active scorer, selected by the USE_LLM environment flag."""
    use_llm = os.getenv("USE_LLM", "false").strip().lower() in {"1", "true", "yes"}
    if use_llm:
        logger.warning("USE_LLM is set but no LLM scorer is implemented yet")
        return LLMScorer()
    return KeywordScorer()
