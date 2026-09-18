"""Shared HTTP fetch helpers and the contract every source adapter implements."""

from __future__ import annotations

import html as html_module
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 1.5
USER_AGENT = "remote-job-board/1.0 (+https://github.com/RafshanTashin/remote-job-board)"

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class NormalizedJob:
    """A job listing in the common shape every downstream pipeline stage expects."""

    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    tags: list[str] = field(default_factory=list)
    posted_at: str | None = None
    # Only some sources publish an explicit closing date; where they do, it
    # beats guessing staleness from posted_at.
    expires_at: str | None = None


class SourceAdapter(ABC):
    """Base class for a single job-board source."""

    name: str

    @abstractmethod
    def fetch(self) -> list[NormalizedJob]:
        """Fetch and normalize listings from this source.

        Implementations should let network/parsing errors propagate — the
        caller (``pipeline.fetch.fetch_all``) is responsible for isolating
        failures so one dead source doesn't take down the whole run.
        """
        raise NotImplementedError


def fetch_url(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> requests.Response:
    """GET a URL with retries and exponential backoff.

    Raises the last ``requests.RequestException`` if every attempt fails.
    """
    merged_headers = {"User-Agent": USER_AGENT, "Accept": "application/json, application/rss+xml, */*", **(headers or {})}
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=timeout, headers=merged_headers, params=params)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning("fetch attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(DEFAULT_BACKOFF_SECONDS**attempt)
    assert last_exc is not None
    raise last_exc


def strip_html(text: str | None) -> str:
    """Strip HTML tags, unescape entities, and collapse whitespace in one pass."""
    if not text:
        return ""
    without_tags = _TAG_RE.sub(" ", text)
    unescaped = html_module.unescape(without_tags)
    return _WHITESPACE_RE.sub(" ", unescaped).strip()
