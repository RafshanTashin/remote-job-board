"""CLI entrypoint: fetch, normalize, score, store, and render the job board.

Run with ``python jobboard/main.py`` from the repo root, or ``python main.py``
from inside ``jobboard/`` - both work because of the sys.path bootstrap below.
"""

from __future__ import annotations

import sys
from pathlib import Path

# jobboard/pipeline/*.py and jobboard/sources/*.py import each other with
# absolute `from jobboard...` paths (so they also work unmodified under
# pytest and `python -m`). That requires the repo root - the parent of this
# file's own `jobboard/` package directory - to be on sys.path, which is not
# guaranteed when this file is invoked directly as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import logging
from datetime import datetime, timedelta, timezone

from jobboard.fixtures.sample_jobs import SAMPLE_JOBS
from jobboard.pipeline.fetch import fetch_all
from jobboard.pipeline.normalize import apply_hard_filters, dedupe
from jobboard.pipeline.score import Profile, get_scorer
from jobboard.pipeline.store import init_db, query_matches, upsert_job
from jobboard.render.build import build_dashboard

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
PROFILE_PATH = PACKAGE_ROOT / "profile.json"
DB_PATH = REPO_ROOT / "jobs.db"
OUTPUT_PATH = REPO_ROOT / "index.html"
MIN_MATCH_SCORE = 50.0

logger = logging.getLogger("jobboard")


def configure_logging(verbose: bool = False) -> None:
    """Configure structured logging for the whole pipeline run."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run(
    *,
    dry_run: bool,
    demo: bool = False,
    db_path: Path = DB_PATH,
    output_path: Path = OUTPUT_PATH,
) -> int:
    """Run the full pipeline once. Returns the number of current matches.

    In ``demo`` mode, live fetching is skipped in favor of the bundled
    sample listings (see ``jobboard.fixtures.sample_jobs``) and results are
    scored and rendered from a throwaway in-memory database, so no
    persistent state is written.
    """
    started = datetime.now(timezone.utc)
    profile = Profile.load(PROFILE_PATH)
    scorer = get_scorer()

    if demo:
        jobs_scanned = len(SAMPLE_JOBS)
        deduped = dedupe([job for job, _ in SAMPLE_JOBS])
        filtered = apply_hard_filters(deduped, profile.geo_hard_exclude_phrases)
        first_seen_by_id = {job.external_id: started - timedelta(hours=hours_ago) for job, hours_ago in SAMPLE_JOBS}
        scored = [(job, scorer.score(job, profile)) for job in filtered]
    else:
        all_jobs, reports = fetch_all()
        jobs_scanned = len(all_jobs)
        for report in reports:
            status = "failed" if report.error else "ok"
            logger.info(
                "source=%s status=%s count=%d duration=%.2fs%s",
                report.source,
                status,
                report.count,
                report.duration_seconds,
                f" error={report.error}" if report.error else "",
            )
        deduped = dedupe(all_jobs)
        filtered = apply_hard_filters(deduped, profile.geo_hard_exclude_phrases)
        first_seen_by_id = None
        scored = [(job, scorer.score(job, profile)) for job in filtered]

    if dry_run:
        matches = sorted(
            (pair for pair in scored if pair[1].percentage >= MIN_MATCH_SCORE),
            key=lambda pair: pair[1].percentage,
            reverse=True,
        )
        logger.info(
            "[dry-run] scanned=%d after-filters=%d matches>=%.0f%%=%d",
            jobs_scanned,
            len(filtered),
            MIN_MATCH_SCORE,
            len(matches),
        )
        for job, result in matches[:20]:
            logger.info("  %5.1f%%  %-45s  %s", result.percentage, job.title[:45], job.company)
        return len(matches)

    conn = init_db(":memory:" if demo else db_path)
    try:
        for job, result in scored:
            seen_at = first_seen_by_id[job.external_id] if first_seen_by_id else started
            upsert_job(conn, job, result, seen_at)
        conn.commit()
        current_matches = query_matches(conn, MIN_MATCH_SCORE, started)
    finally:
        conn.close()

    build_dashboard(
        current_matches,
        jobs_scanned=jobs_scanned,
        generated_at=started,
        output_path=output_path,
        is_demo=demo,
    )
    new_count = sum(1 for job in current_matches if job.is_new)
    logger.info("wrote %s (%d matches, %d new)", output_path, len(current_matches), new_count)
    return len(current_matches)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and run the pipeline."""
    parser = argparse.ArgumentParser(description="Fetch, score, and publish the remote job board.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and score without writing jobs.db or index.html.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Score the bundled sample listings instead of fetching live APIs. Used for the public demo build.",
    )
    parser.add_argument("--db-path", type=Path, default=DB_PATH, help="Where to write the SQLite database.")
    parser.add_argument("--output-path", type=Path, default=OUTPUT_PATH, help="Where to write the dashboard HTML.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    args = parser.parse_args(argv)

    configure_logging(args.verbose)
    run(dry_run=args.dry_run, demo=args.demo, db_path=args.db_path, output_path=args.output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
