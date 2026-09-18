"""Render the scored, stored job list into a single self-contained dashboard HTML file."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from jobboard.pipeline.store import StoredJob

TEMPLATE_DIR = Path(__file__).parent
TEMPLATE_NAME = "template.html.j2"


def _safe_json_for_html(payload: object) -> str:
    """JSON-encode and neutralize '<', '>' and '&' so the result is safe to
    embed inside an inline <script> tag even though job data comes from
    untrusted third-party APIs (guards against a job description containing
    a literal '</script>' breaking out of the tag).
    """
    encoded = json.dumps(payload)
    return encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def build_dashboard(
    jobs: list[StoredJob],
    *,
    jobs_scanned: int,
    generated_at: datetime,
    output_path: str | Path,
    is_demo: bool = False,
) -> None:
    """Render index.html from the current match set and this run's pipeline stats."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template(TEMPLATE_NAME)

    match_count = len(jobs)
    new_count = sum(1 for job in jobs if job.is_new)
    avg_match = round(sum(job.match_score for job in jobs) / match_count, 1) if match_count else 0.0
    sources = sorted({job.source for job in jobs})

    jobs_json = _safe_json_for_html([asdict(job) for job in jobs])

    html = template.render(
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        jobs_scanned=jobs_scanned,
        match_count=match_count,
        new_count=new_count,
        avg_match=avg_match,
        sources=sources,
        jobs_json=jobs_json,
        is_demo=is_demo,
    )
    Path(output_path).write_text(html, encoding="utf-8")
