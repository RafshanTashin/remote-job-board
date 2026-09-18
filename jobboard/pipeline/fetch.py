"""Concurrent, fault-isolated fetching across all configured job sources."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from jobboard.sources.arbeitnow import ArbeitnowSource
from jobboard.sources.base import NormalizedJob, SourceAdapter
from jobboard.sources.jobicy import JobicySource
from jobboard.sources.remoteok import RemoteOKSource
from jobboard.sources.remotive import RemotiveSource
from jobboard.sources.weworkremotely import WeWorkRemotelySource

logger = logging.getLogger(__name__)

ALL_SOURCES: list[SourceAdapter] = [
    RemotiveSource(),
    RemoteOKSource(),
    ArbeitnowSource(),
    JobicySource(),
    WeWorkRemotelySource(),
]


@dataclass
class FetchReport:
    """Per-source outcome of a single fetch run, for structured logging."""

    source: str
    count: int
    duration_seconds: float
    error: str | None = None


def _run_one(source: SourceAdapter) -> tuple[FetchReport, list[NormalizedJob]]:
    start = time.monotonic()
    try:
        jobs = source.fetch()
        duration = time.monotonic() - start
        return FetchReport(source.name, len(jobs), duration), jobs
    except Exception as exc:  # noqa: BLE001 - one bad source must not kill the run
        duration = time.monotonic() - start
        logger.error("source=%s failed after %.2fs: %s", source.name, duration, exc)
        return FetchReport(source.name, 0, duration, error=str(exc)), []


def fetch_all(sources: list[SourceAdapter] | None = None) -> tuple[list[NormalizedJob], list[FetchReport]]:
    """Fetch every source concurrently.

    A failing or slow source is isolated: it logs an error and contributes
    zero jobs rather than aborting the run.
    """
    sources = sources if sources is not None else ALL_SOURCES
    all_jobs: list[NormalizedJob] = []
    reports: list[FetchReport] = []

    with ThreadPoolExecutor(max_workers=max(1, len(sources))) as executor:
        futures = {executor.submit(_run_one, source): source for source in sources}
        for future in as_completed(futures):
            report, jobs = future.result()
            reports.append(report)
            all_jobs.extend(jobs)
            status = "failed" if report.error else "ok"
            logger.info(
                "source=%s status=%s count=%d duration=%.2fs",
                report.source,
                status,
                report.count,
                report.duration_seconds,
            )

    return all_jobs, reports
