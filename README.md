# Remote Job Board

A zero-cost, serverless job aggregator that scans five free remote-job
sources daily, scores every listing as an explainable percentage match
against a candidate profile, and publishes a static dashboard - no backend,
no database server, no paid APIs.

**[Live demo](https://rafshantashin.github.io/remote-job-board/)** &middot; built with Python 3.11, SQLite, Jinja2, and GitHub Actions.

> The live demo above runs the pipeline against a handful of fictional
> sample listings (`jobboard/fixtures/sample_jobs.py`), so the page is
> always populated and reproducible. Every company name in it is invented.

![Dashboard screenshot](docs/screenshot.png)

## Architecture

```
        ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────┐
        │ Remotive │   │ RemoteOK │   │ Arbeitnow │   │  Jobicy  │   │  WWR   │
        │   API    │   │   API    │   │    API    │   │   API    │   │  RSS   │
        └────┬─────┘   └────┬─────┘   └─────┬─────┘   └────┬─────┘   └───┬────┘
             └──────────────┴───────┬───────┴──────────────┴─────────────┘
                                     │  concurrent fetch, per-source
                                     │  timeout + retry (pipeline/fetch.py)
                                     ▼
                     normalize + dedupe (pipeline/normalize.py)
                     sha256(company + title + location) as the dedupe key
                                     │
                                     ▼
                     hard filters: must be remote, drop listings that
                     demand a specific work authorization / residency
                                     │
                                     ▼
                     score against profile.json (pipeline/score.py)
                     weighted keyword hits - penalties, normalized to 0-100%
                                     │
                                     ▼
                     upsert into SQLite, keep >= 50% (pipeline/store.py)
                     first_seen tracked -> "new in the last 24h"
                                     │
                                     ▼
                     render index.html (render/build.py + template.html.j2)
                     one self-contained file, no build step, no framework
                                     │
                                     ▼
                          GitHub Actions -> GitHub Pages
```

Each source in `jobboard/sources/` is an independent adapter returning the
same normalized shape (`source, external_id, title, company, location, url,
description, tags, posted_at`). `pipeline/fetch.py` runs all five
concurrently in a thread pool; a failing or slow source is caught, logged,
and contributes zero listings rather than aborting the run.

## Scoring, explained

`profile.json` defines a list of weighted skills (e.g. `technical seo:
5`), target job titles, a seniority range, and phrase lists for geo/
authorization filtering. For every skill, `KeywordScorer`
(`pipeline/score.py`) checks for a whole-word/phrase match in three
fields, each with its own multiplier:

| Field       | Multiplier |
|-------------|-----------:|
| Title       | &times;3   |
| Tags        | &times;2   |
| Description | &times;1   |

A skill can score in more than one field - a title *and* description hit
both count. The percentage is `raw_score / max_score * 100`, where
`max_score` is calibrated against every skill appearing in the title (the
highest-weighted field). A listing that also matches in description/tags
is rewarded above that baseline, which is why the score is explicitly
capped at 100 (and floored at 0).

Two penalties subtract from `raw_score`, each as a fraction of
`max_score` so they stay meaningful regardless of profile size:

- **Geo/authorization phrases** - a hard match (e.g. "must reside in",
  "US work authorization") gets the listing dropped entirely before
  scoring; a softer signal (e.g. "must overlap with EST") just reduces the
  score.
- **Seniority mismatch** - titles/descriptions implying a more senior
  role (senior, staff, director, ...), a more junior one (intern,
  entry-level, ...), or an explicit years-of-experience ask well above the
  profile's range.

The matched and missing skill names are stored alongside the score so the
dashboard can render them as chips - the percentage is never a black box.

Matching uses word-boundary regex, not plain substring search - an early
version matched the 3-letter skill "CRO" inside ordinary words like
"across" and "cross-functional" in nearly every job description, which
would have quietly inflated every score.

## Demo mode

`python jobboard/main.py --demo` skips the network entirely and scores a
small set of hand-written fictional listings
(`jobboard/fixtures/sample_jobs.py`) instead, rendering from a throwaway
in-memory database. It's the same normalize/filter/score/render path a
live run takes - only the input differs - which makes it useful both for
the deployed demo page and for eyeballing template changes without
waiting on five APIs.

## Setup

```bash
git clone https://github.com/RafshanTashin/remote-job-board.git
cd remote-job-board
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Requires Python 3.11+.

### Run it

```bash
# Fetch and score real listings without writing anything (safe to run anytime):
python jobboard/main.py --dry-run

# Full run: fetch, score, write jobs.db and index.html:
python jobboard/main.py

# Build the demo dashboard (bundled sample data, no network calls):
python jobboard/main.py --demo

# Override where output goes:
python jobboard/main.py --db-path /path/to/jobs.db --output-path /path/to/index.html
```

### Test

```bash
pytest
```

14 tests cover the match-percentage calculation (weighting, penalties,
capping/flooring, word-boundary matching) and the dedupe/hashing logic,
using a small fixture profile and sample listings
(`jobboard/tests/conftest.py`).

## Automation

`.github/workflows/demo-pages.yml` rebuilds and redeploys the demo page on
every push to `main` (and on demand via `workflow_dispatch`). It doesn't
run on a schedule, since the sample data never changes.

For a live daily scan, point a scheduled workflow at `python
jobboard/main.py` with `--db-path`/`--output-path` set to wherever the
results should land.

## Sample output

From a real `--demo` run (see the [live demo](https://rafshantashin.github.io/remote-job-board/) for the interactive version):

| Match | Title | Company | Matched skills |
|------:|-------|---------|----------------|
| 94.7% | SEO Specialist - Technical SEO & Keyword Research | Northwind Analytics | technical seo, google analytics 4, google search console, content strategy, on-page seo, keyword research, b2b saas, link building, internal linking |
| 65.9% | SEO Manager - B2B SaaS | Fernwood Digital | technical seo, content strategy, on-page seo, keyword research, hubspot, b2b saas, link building, internal linking |
| 53.0% | Digital Marketing Specialist | Brightloop | content strategy, on-page seo, keyword research, hubspot, google ads, b2b saas, link building, internal linking |
| 52.3% | Content Marketing Manager | Lumen Stack | content strategy, on-page seo, keyword research, hubspot, b2b saas, link building, internal linking |

8 sample listings scanned, 4 matches at or above the 50% threshold,
66.5% average match, 3 flagged "new" in the last 24 hours.

## Project structure

```
jobboard/
  sources/     one adapter per job source + base.py (shared HTTP/retry helpers)
  pipeline/    fetch.py, normalize.py, score.py, store.py
  render/      template.html.j2, build.py
  fixtures/    sample_jobs.py (demo-only data)
  tests/       pytest suite
  profile.json
  main.py
```

## Extending the scorer

`pipeline/score.py` selects its scorer through `get_scorer()`, which reads
a `USE_LLM` environment variable. Only the deterministic `KeywordScorer`
is implemented; `USE_LLM=true` resolves to a placeholder `LLMScorer` that
raises `NotImplementedError`. The seam exists so an LLM-backed scorer
could be dropped in later - implementing one is out of scope for v1.
