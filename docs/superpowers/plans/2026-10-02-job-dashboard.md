# Daily Job Dashboard Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A GitHub Actions job that fetches Senior UX / Product Designer jobs in Bengaluru from JSearch once a day, filters and ranks them, and publishes a static dashboard on GitHub Pages.

**Architecture:** Pure-function Python modules (`experience`, `normalize`, `filters`, `scoring`, `store`) wired together by `fetch_jobs.py`, with the network isolated in `jsearch.py` so everything else is tested from fixtures. Output is two JSON files read by one vanilla-JS `index.html`.

**Tech Stack:** Python 3.11+ (CI uses 3.12), `requests`, `PyYAML`, `pytest`; vanilla HTML/CSS/JS; GitHub Actions + GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-02-job-dashboard-design.md`

## Global Constraints

- Free JSearch quota: 200 credits/month; 1 credit per returned page of up to 10 jobs. Default budget 5 pages/day.
- Request params: `country=in`, `date_posted=3days`, `num_pages=1`, page-by-page.
- Quota guard: below 10 remaining credits, only page 1 of each remaining search.
- History expiry: 14 days after `first_seen`. "Today" is computed in `Asia/Kolkata`.
- Tests never touch the network.
- Public repo; API key only in the `RAPIDAPI_KEY` secret.
- Commits: conventional commits, author is the GitHub no-reply email.

## File map

| File | Responsibility |
|---|---|
| `config.yaml` | searches, location, keyword lists, industry boosts, budgets |
| `scripts/config.py` | `load_config(path) -> dict` |
| `scripts/experience.py` | `parse_experience(text) -> list[int, int \| None] \| None` |
| `scripts/normalize.py` | `make_key(company, title) -> str`, `normalize(raw) -> dict` |
| `scripts/filters.py` | `has_keyword(text, keywords) -> bool`, `drop_reason(job, cfg) -> str \| None`, `apply_filters(jobs, cfg) -> list` |
| `scripts/scoring.py` | `score_job(job, cfg, now_ts) -> dict` (returns copy with `score`, `tags`) |
| `scripts/store.py` | `dedupe(jobs)`, `merge(existing, fresh, today, expire_days)`, `load_jobs(path)`, `write_json(path, data)` |
| `scripts/jsearch.py` | `JSearchError`, `PageResult`, `search_page(session, api_key, query, page, country, date_posted)` |
| `scripts/fetch_jobs.py` | `fetch_all(cfg, search_fn)`, `run(cfg, jobs_path, status_path, search_fn, now)`, `main()` |
| `site/index.html` | dashboard |
| `.github/workflows/daily.yml` | schedule → test → fetch → commit → deploy |

## Tasks

### Task 1: Scaffold and config
- [ ] Create `requirements.txt`, `pyproject.toml` (pytest `pythonpath = ["."]`), `.gitignore`, `scripts/__init__.py`, `config.yaml`, `scripts/config.py`.
- [ ] Test `tests/test_config.py`: `load_config("config.yaml")` returns two searches with `max_pages` 3 and 2, and `location.city_keywords == ["bengaluru", "bangalore"]`.
- [ ] Run `pytest -q` → pass. Commit `chore: scaffold project and config`.

### Task 2: Experience parser
- [ ] Tests `tests/test_experience.py`, each input → expected:
  - `"4+ years of UX experience"` → `[4, None]`
  - `"4 - 8 years"` → `[4, 8]`; `"4–8 yrs"` → `[4, 8]`; `"4 to 8 years"` → `[4, 8]`
  - `"Minimum 5 years in product design"` → `[5, None]`; `"at least 3 years"` → `[3, None]`
  - `"5 years of experience"` → `[5, None]`
  - `"0-2 years"` → `[0, 2]`
  - `"Company founded 10 years ago. You need 4+ years of UX design."` → `[4, None]` (sentence mentioning design wins)
  - `"Great team, no numbers here"` → `None`
- [ ] Run → fail; implement regexes (range, minimum, plus, plain "N years of experience"); run → pass. Commit `feat: parse required experience from text`.

### Task 3: Normalize JSearch jobs
- [ ] Fixture `tests/fixtures/search_page.json` in JSearch `/search` shape (`status`, `data: [...]`) containing: a senior UX job at a gaming company with `apply_options`; the same job from another publisher; an interior designer; a junior/intern role; a Pune job; a job with a structured months field.
- [ ] Tests `tests/test_normalize.py`: `make_key("Swiggy ", "Sr. Product Designer!")` == `"swiggy|sr product designer"`; `normalize` maps title/company/city/posted_at/salary/highlights/apply_links (deduped by URL); months field 60 → `[5, None]`; missing optional fields → `None`/empty lists, no exception.
- [ ] Implement; run → pass. Commit `feat: normalize JSearch job records`.

### Task 4: Filters
- [ ] Tests `tests/test_filters.py` (`drop_reason` returns `None` to keep):
  - "Senior Product Designer", Bengaluru → keep; "UI/UX Designer", Bangalore → keep
  - "Interior Designer" → `"not a UX/product design title"`; "Graphic & UX Designer" → `"unrelated designer"`
  - "Product Design Intern" / "Junior UX Designer" / "Associate Product Designer" → `"junior title"`
  - experience `[0, 2]` / `[2, None]` → `"too little experience"`; `[2, 4]` / `[3, None]` / `None` → keep
  - city "Pune" → `"outside Bengaluru"`
  - `has_keyword("Sr. Designer", ["sr"])` true; `has_keyword("Academy", ["cad"])` false
- [ ] Implement; run → pass. Commit `feat: filter out irrelevant jobs`.

### Task 5: Scoring
- [ ] Tests `tests/test_scoring.py`:
  - title: senior + role → 35; role only → 22
  - experience: `[4, 8]` → 25, `[2, 5]` → 25, `[9, None]` → 15, `[12, None]` → 8 + tag "May be very senior", `None` → 15
  - industry: company "PlaySimple Games" → 25 + "Gaming"; description "quick commerce" → 20 + "Quick commerce"; both gaming and consumer keywords → 25 with both tags; none → 0
  - freshness by age in days: 0→15, 1→12, 2→9, 3→6, 5→4, 20→0, unknown→0
  - total = sum, capped at 100; input job not mutated
- [ ] Implement; run → pass. Commit `feat: score and tag jobs`.

### Task 6: Store (dedupe, merge, expiry)
- [ ] Tests `tests/test_store.py`:
  - `dedupe` merges two jobs with the same `id`, unions `apply_links` by URL, keeps the longer description
  - `merge`: new job gets `first_seen=today`, `new_today=True`; existing keeps old `first_seen`, `new_today=False`, `last_seen=today`; job not in fresh but within 14 days is kept; job with `first_seen` 15 days ago is dropped
  - `load_jobs` on missing file → `([], None)`; on malformed JSON → `([], "<warning>")`; accepts `{"jobs": [...]}`
- [ ] Implement; run → pass. Commit `feat: merge daily results with history`.

### Task 7: JSearch client and daily run
- [ ] Tests `tests/test_fetch_jobs.py` with a fake `search_fn(query, page) -> PageResult`:
  - stops a search when a page has fewer than 10 jobs; respects `max_pages`
  - quota guard: credits below 10 → no page 2+
  - one search raises `JSearchError` → other search still merged, status `ok: false` naming the failed query, returns `False`
  - all searches fail → existing `jobs.json` unchanged, status `ok: false`
  - success → `jobs.json` sorted by score desc, status has `credits_left` and counts
- [ ] Tests `tests/test_jsearch.py` with a stub session: non-200 → `JSearchError("HTTP 429 …")`; reads `x-ratelimit-requests-remaining`; accepts `data` as list or `{"jobs": [...]}`.
- [ ] Implement `jsearch.py`, `fetch_jobs.py` (`main` reads `RAPIDAPI_KEY`; missing key → failing status, exit 1). Run → pass. Commit `feat: fetch jobs from JSearch and write daily data`.

### Task 8: Dashboard
- [ ] `site/index.html`: header (title, refreshed time, totals, new today, credits left), failure banner, search box, tag chips, sort toggle, cards (all spec fields, expandable description, apply links), Applied / Not interested marks in `localStorage`, "Show hidden" toggle, responsive. All API text inserted via `textContent` (no HTML injection).
- [ ] Seed `data/jobs.json` and `data/status.json` from the fixture via `python -m scripts.fetch_jobs --from-fixture tests/fixtures/search_page.json` so the page can be previewed locally with `python -m http.server` from a built `_site/`.
- [ ] Manually check in a browser: filters, sort, marks, banner. Commit `feat: add job dashboard page`.

### Task 9: Workflow and setup docs
- [ ] `.github/workflows/daily.yml`: cron `30 1 * * *` + `workflow_dispatch`; permissions `contents: write`, `pages: write`, `id-token: write`; steps: checkout, setup-python 3.12, install, `pytest -q`, fetch (`continue-on-error`, `RAPIDAPI_KEY` secret), commit `data/` if changed, build `_site/`, upload + deploy Pages, then fail the job if fetch failed. Use the latest major versions of the official actions.
- [ ] `README.md` with the one-time setup steps from the spec. Commit `ci: add daily refresh and Pages deploy`.

### Task 10: Publish (needs the user)
- [ ] `gh repo create abhi00712/ux_profile_search --public --source . --push`.
- [ ] User creates the RapidAPI key; `gh secret set RAPIDAPI_KEY`.
- [ ] Enable Pages with source "GitHub Actions" (`gh api` call).
- [ ] `gh workflow run daily.yml`, watch it, open the Pages URL, compare a real response against the field mapping and fix any mismatches.
