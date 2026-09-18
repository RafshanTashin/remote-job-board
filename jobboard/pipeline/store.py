"""SQLite persistence: upsert scored jobs and query the current match set."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from jobboard.pipeline.normalize import compute_hash
from jobboard.pipeline.score import ScoreResult
from jobboard.sources.base import NormalizedJob

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT NOT NULL,
    tags TEXT NOT NULL,
    posted_at TEXT,
    match_score REAL NOT NULL,
    matched_keywords TEXT NOT NULL,
    missing_keywords TEXT NOT NULL,
    role_match TEXT,
    eligibility TEXT NOT NULL DEFAULT 'unconfirmed',
    eligibility_reason TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
"""


ADDED_COLUMNS = {
    "role_match": "TEXT",
    "eligibility": "TEXT NOT NULL DEFAULT 'unconfirmed'",
    "eligibility_reason": "TEXT",
}


def init_db(path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the jobs database and ensure the schema exists."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)

    # A database written before these columns existed keeps its rows (and
    # their first_seen history) rather than being rebuilt from scratch.
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
    for column, definition in ADDED_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")

    conn.commit()
    return conn


def upsert_job(
    conn: sqlite3.Connection,
    job: NormalizedJob,
    score: ScoreResult,
    now: datetime,
    eligibility: str = "unconfirmed",
    eligibility_reason: str | None = None,
) -> str:
    """Insert a new job (first_seen=now) or refresh an existing one (last_seen=now).

    Returns the job's stable id (the dedupe hash).
    """
    job_id = compute_hash(job.company, job.title, job.location)
    now_iso = now.isoformat()
    existing = conn.execute("SELECT first_seen FROM jobs WHERE id = ?", (job_id,)).fetchone()
    first_seen = existing["first_seen"] if existing else now_iso

    conn.execute(
        """
        INSERT INTO jobs (
            id, source, external_id, title, company, location, url, description,
            tags, posted_at, match_score, matched_keywords, missing_keywords,
            role_match, eligibility, eligibility_reason, first_seen, last_seen
        ) VALUES (:id, :source, :external_id, :title, :company, :location, :url, :description,
                  :tags, :posted_at, :match_score, :matched_keywords, :missing_keywords,
                  :role_match, :eligibility, :eligibility_reason, :first_seen, :last_seen)
        ON CONFLICT(id) DO UPDATE SET
            source = excluded.source,
            external_id = excluded.external_id,
            title = excluded.title,
            company = excluded.company,
            location = excluded.location,
            url = excluded.url,
            description = excluded.description,
            tags = excluded.tags,
            posted_at = excluded.posted_at,
            match_score = excluded.match_score,
            matched_keywords = excluded.matched_keywords,
            missing_keywords = excluded.missing_keywords,
            role_match = excluded.role_match,
            eligibility = excluded.eligibility,
            eligibility_reason = excluded.eligibility_reason,
            last_seen = excluded.last_seen
        """,
        {
            "id": job_id,
            "source": job.source,
            "external_id": job.external_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "url": job.url,
            "description": job.description,
            "tags": json.dumps(job.tags),
            "posted_at": job.posted_at,
            "match_score": score.percentage,
            "matched_keywords": json.dumps(score.matched_keywords),
            "missing_keywords": json.dumps(score.missing_keywords),
            "role_match": score.role_match,
            "eligibility": eligibility,
            "eligibility_reason": eligibility_reason,
            "first_seen": first_seen,
            "last_seen": now_iso,
        },
    )
    return job_id


@dataclass
class StoredJob:
    """A job row read back from SQLite, ready for rendering."""

    id: str
    source: str
    title: str
    company: str
    location: str
    url: str
    tags: list[str]
    posted_at: str | None
    match_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    role_match: str | None
    eligibility: str
    eligibility_reason: str | None
    first_seen: str
    last_seen: str
    is_new: bool


def query_matches(
    conn: sqlite3.Connection,
    min_score: float,
    now: datetime,
    new_within_hours: int = 24,
) -> list[StoredJob]:
    """Return jobs at or above ``min_score``, sorted by match percentage descending."""
    cutoff = now - timedelta(hours=new_within_hours)
    rows = conn.execute(
        "SELECT * FROM jobs WHERE match_score >= ? ORDER BY match_score DESC, last_seen DESC",
        (min_score,),
    ).fetchall()

    results: list[StoredJob] = []
    for row in rows:
        first_seen_dt = datetime.fromisoformat(row["first_seen"])
        results.append(
            StoredJob(
                id=row["id"],
                source=row["source"],
                title=row["title"],
                company=row["company"],
                location=row["location"],
                url=row["url"],
                tags=json.loads(row["tags"]),
                posted_at=row["posted_at"],
                match_score=row["match_score"],
                matched_keywords=json.loads(row["matched_keywords"]),
                missing_keywords=json.loads(row["missing_keywords"]),
                role_match=row["role_match"],
                eligibility=row["eligibility"] or "unconfirmed",
                eligibility_reason=row["eligibility_reason"],
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                is_new=first_seen_dt >= cutoff,
            )
        )
    return results
