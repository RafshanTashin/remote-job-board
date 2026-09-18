"""Score how well a listing's role fits the candidate's profile.

The question this answers is "is this a job I could apply for?", not "how
many of my tools does it name". A Marketing Specialist posting that never
mentions GA4 is still a job worth seeing, so the job title carries most of
the weight, the description's subject matter carries some, and named skills
only add confidence on top.

The scorer is isolated behind ``get_scorer()`` so an LLM-backed
implementation can replace it via the ``USE_LLM`` flag without changing any
caller. Only the deterministic scorer is implemented.
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

# The three signals, weighted to sum to 100 before penalties. Role fit
# dominates deliberately: the candidate applies by job title, and a
# marketing role they could do shouldn't be marked down for describing a
# domain that happens not to name their usual tools.
ROLE_FIT_WEIGHT = 65
DOMAIN_FIT_WEIGHT = 20
SKILL_FIT_WEIGHT = 15

# A title match is worth full role credit. A job ad that merely mentions
# "digital marketing" somewhere in its body is usually describing a team it
# works with, not the role itself - a Product Manager JD naming the
# marketing org shouldn't read as a marketing job - so body-only evidence
# is worth much less.
ROLE_IN_TITLE = 1.0
ROLE_IN_DESCRIPTION = 0.25

# Domain vocabulary saturates - a marketing JD naming 12 domain terms is no
# more "a marketing job" than one naming 8.
DOMAIN_TERMS_FOR_FULL_CREDIT = 8

SENIORITY_PENALTY = 25.0
GEO_SOFT_PENALTY = 12.0

_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:-|to)?\s*(\d{1,2})?\s*\+?\s*years?", re.IGNORECASE)
_KEYWORD_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _fold(text: str) -> str:
    """Lowercase and treat hyphens as spaces so 'on-page SEO' matches 'on page seo'."""
    return (text or "").lower().replace("-", " ")


def _contains_keyword(haystack: str, keyword: str) -> bool:
    """Whole-word/phrase containment.

    Plain substring matching let the acronym "CRO" match inside "across" and
    "cross-functional", which inflated nearly every listing's score.
    """
    pattern = _KEYWORD_PATTERN_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
        _KEYWORD_PATTERN_CACHE[keyword] = pattern
    return pattern.search(haystack) is not None


@dataclass
class TargetRole:
    """A family of job titles the candidate would apply to, and how well it fits."""

    family: str
    weight: float
    patterns: list[str]


@dataclass
class Skill:
    name: str
    weight: float


@dataclass
class Profile:
    """The candidate profile a listing is scored against."""

    target_roles: list[TargetRole]
    domain_terms: list[str]
    skills: list[Skill]
    skill_target_weight: float
    years_experience: int
    seniority_reject_terms: list[str]
    reject_years_above: int
    geo_soft_penalty_phrases: list[str]
    geo_hard_exclude_phrases: list[str]
    excluded_title_terms: list[str]
    max_posting_age_days: int
    eligibility: dict

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        """Load a profile from a profile.json file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        seniority = data.get("seniority", {})
        return cls(
            target_roles=[
                TargetRole(
                    family=r["family"],
                    weight=float(r["weight"]),
                    patterns=[_fold(p) for p in r["patterns"]],
                )
                for r in data["target_roles"]
            ],
            domain_terms=[_fold(t) for t in data.get("domain_terms", [])],
            skills=[Skill(name=s["name"], weight=float(s["weight"])) for s in data.get("skills", [])],
            skill_target_weight=float(data.get("skill_target_weight", 25)),
            years_experience=int(seniority.get("years_experience", 0)),
            seniority_reject_terms=[_fold(t) for t in seniority.get("reject_terms", [])],
            reject_years_above=int(seniority.get("reject_years_above", 99)),
            geo_soft_penalty_phrases=[_fold(p) for p in data.get("geo_soft_penalty_phrases", [])],
            geo_hard_exclude_phrases=[p.lower() for p in data.get("geo_hard_exclude_phrases", [])],
            excluded_title_terms=[_fold(t) for t in data.get("excluded_title_terms", [])],
            max_posting_age_days=int(data.get("max_posting_age_days", 60)),
            eligibility=data.get("eligibility", {}),
        )


@dataclass
class ScoreResult:
    """A listing's fit, plus the components that produced it."""

    percentage: float
    role_match: str | None
    matched_keywords: list[str]
    missing_keywords: list[str]
    role_fit: float
    domain_fit: float
    skill_fit: float
    penalties: list[str] = field(default_factory=list)


def _required_years(text: str) -> int | None:
    """Highest years-of-experience figure the posting asks for, if any."""
    years = [int(g) for pair in _YEARS_RE.findall(text) for g in pair if g]
    return max(years) if years else None


def _seniority_penalty(job: NormalizedJob, profile: Profile) -> str | None:
    """Flag roles clearly above the candidate's band.

    Only leadership titles and far-out experience asks count. "Senior" and
    "Manager" are deliberately not penalized - the candidate has 5+ years
    and applies at both executive and manager level.
    """
    title = _fold(job.title)
    for term in profile.seniority_reject_terms:
        if _contains_keyword(title, term):
            return f"seniority: '{term.strip()}' is above the target band"

    required = _required_years(_fold(f"{job.title} {job.description}"))
    if required is not None and required > profile.reject_years_above:
        return f"seniority: posting asks for {required}+ years"
    return None


def _geo_soft_penalty(job: NormalizedJob, profile: Profile) -> str | None:
    haystack = _fold(f"{job.description} {job.location}")
    for phrase in profile.geo_soft_penalty_phrases:
        if _contains_keyword(haystack, phrase):
            return f"timezone/region preference: '{phrase}'"
    return None


def _role_fit(job: NormalizedJob, profile: Profile) -> tuple[float, str | None]:
    """Best-matching target role family, as a 0-1 fraction plus its name.

    Returns the strongest single match rather than summing - a listing is
    one role, not several.
    """
    title = _fold(job.title)
    description = _fold(job.description)

    best_score = 0.0
    best_family: str | None = None

    for role in profile.target_roles:
        for pattern in role.patterns:
            if _contains_keyword(title, pattern):
                score = role.weight * ROLE_IN_TITLE
            elif _contains_keyword(description, pattern):
                score = role.weight * ROLE_IN_DESCRIPTION
            else:
                continue
            if score > best_score:
                best_score = score
                best_family = role.family

    return min(1.0, best_score), best_family


def _domain_fit(job: NormalizedJob, profile: Profile) -> float:
    """How strongly the listing's text reads as marketing/SEO work, 0-1."""
    haystack = _fold(f"{job.title} {job.description} {' '.join(job.tags)}")
    hits = sum(1 for term in profile.domain_terms if _contains_keyword(haystack, term))
    return min(1.0, hits / DOMAIN_TERMS_FOR_FULL_CREDIT)


def _skill_fit(job: NormalizedJob, profile: Profile) -> tuple[float, list[str], list[str]]:
    """Weighted profile skills present anywhere in the listing, 0-1, plus the chip lists."""
    haystack = _fold(f"{job.title} {job.description} {' '.join(job.tags)}")

    matched: list[str] = []
    missing: list[str] = []
    matched_weight = 0.0

    for skill in profile.skills:
        if _contains_keyword(haystack, _fold(skill.name)):
            matched.append(skill.name)
            matched_weight += skill.weight
        else:
            missing.append(skill.name)

    fraction = min(1.0, matched_weight / profile.skill_target_weight) if profile.skill_target_weight else 0.0
    return fraction, matched, missing


class Scorer(Protocol):
    """The interface every scorer implementation must satisfy."""

    def score(self, job: NormalizedJob, profile: Profile) -> ScoreResult: ...


class ProfileScorer:
    """Role fit, domain fit, and skill overlap, minus penalties, as a 0-100 percentage."""

    def score(self, job: NormalizedJob, profile: Profile) -> ScoreResult:
        role_fraction, role_family = _role_fit(job, profile)
        domain_fraction = _domain_fit(job, profile)
        skill_fraction, matched, missing = _skill_fit(job, profile)

        role_points = role_fraction * ROLE_FIT_WEIGHT
        domain_points = domain_fraction * DOMAIN_FIT_WEIGHT
        skill_points = skill_fraction * SKILL_FIT_WEIGHT

        # Domain vocabulary and tool names are everywhere in job ads - a sales
        # role mentions "campaign" and "funnel" too. Without a role match they
        # are not evidence of a fit, so they can't carry a listing on their own.
        if role_fraction == 0:
            domain_points *= 0.25
            skill_points *= 0.25

        total = role_points + domain_points + skill_points

        penalties: list[str] = []
        seniority_reason = _seniority_penalty(job, profile)
        if seniority_reason:
            total -= SENIORITY_PENALTY
            penalties.append(seniority_reason)

        geo_reason = _geo_soft_penalty(job, profile)
        if geo_reason:
            total -= GEO_SOFT_PENALTY
            penalties.append(geo_reason)

        return ScoreResult(
            percentage=round(max(0.0, min(100.0, total)), 1),
            role_match=role_family,
            matched_keywords=matched,
            missing_keywords=missing,
            role_fit=round(role_points, 1),
            domain_fit=round(domain_points, 1),
            skill_fit=round(skill_points, 1),
            penalties=penalties,
        )


class LLMScorer:
    """Placeholder seam for a future LLM-backed scorer. Not implemented."""

    def score(self, job: NormalizedJob, profile: Profile) -> ScoreResult:
        raise NotImplementedError(
            "LLM scoring is not implemented. Unset USE_LLM (or set it false) to use ProfileScorer."
        )


def get_scorer() -> Scorer:
    """Return the active scorer, selected by the USE_LLM environment flag."""
    if os.getenv("USE_LLM", "false").strip().lower() in {"1", "true", "yes"}:
        logger.warning("USE_LLM is set but no LLM scorer is implemented yet")
        return LLMScorer()
    return ProfileScorer()
