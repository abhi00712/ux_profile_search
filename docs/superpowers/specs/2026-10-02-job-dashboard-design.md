# Daily Job Dashboard — Design

**Date:** 2026-10-02
**Status:** Approved in brainstorming, pending written-spec review

## Goal

A personal dashboard that refreshes once a day and lists open jobs relevant to a
Senior UX Designer / Product Designer with 4+ years of UX experience (background:
PlaySimple Games, BeBetta). Bengaluru only for now; more cities later via config.

Gaming and consumer-app companies are ranked higher, but they are **not** a hard
filter — quick commerce, e-commerce and other product companies are also suitable.

## Decisions

| Topic | Decision |
|---|---|
| Data source | JSearch API on RapidAPI (Google for Jobs: LinkedIn, Naukri, Indeed, Glassdoor, company sites) |
| Runner | GitHub Actions, scheduled once a day, plus manual "Run workflow" |
| Hosting | GitHub Pages, public repo on the user's GitHub account |
| Language | Python 3.12 (`requests`, `PyYAML`, `pytest`) |
| Frontend | One static `index.html` + vanilla JS, no framework, no build step |
| Storage | JSON files committed to the repo; per-user marks in browser `localStorage` |

## Architecture

```
.github/workflows/daily.yml   schedule → test → fetch → commit data → deploy Pages
config.yaml                   roles, cities, keyword lists, weights, page budget
scripts/
  fetch_jobs.py               entry point: orchestrates one daily run
  jsearch.py                  API client (one function: search page → list of raw jobs + credits left)
  normalize.py                raw JSearch job → internal Job dict
  filters.py                  keep/drop rules (title, seniority, experience, location)
  experience.py               parse "4+ years", "3-6 years" etc. from text
  scoring.py                  0–100 score + tags
  store.py                    merge with history, dedupe, expire, write JSON
tests/
  fixtures/                   saved sample JSearch responses (no live API calls in tests)
  test_*.py
data/
  jobs.json                   active jobs (with first_seen / last_seen)
  status.json                 last run time, success/failure, error message, credits left
site/
  index.html                  dashboard; loads data/jobs.json and data/status.json
```

Each module in `scripts/` is a pure function over plain dicts, except `jsearch.py`
(network) and `store.py` (file I/O). This keeps filtering, parsing and scoring
testable from fixtures.

## Daily run (data flow)

1. **Schedule:** cron `30 1 * * *` (01:30 UTC = 07:00 IST). GitHub may start it a few
   minutes late; that is acceptable.
2. **Tests:** `pytest` runs first. If tests fail, nothing is fetched or published.
3. **Fetch:** for each search in `config.yaml`, request pages one at a time:
   - Endpoint: `GET https://jsearch.p.rapidapi.com/search`
   - Headers: `X-RapidAPI-Key: ${{ secrets.RAPIDAPI_KEY }}`, `X-RapidAPI-Host: jsearch.p.rapidapi.com`
   - Params: `query="<role> in Bengaluru"`, `country=in`, `date_posted=3days`,
     `page=<n>`, `num_pages=1`
   - Each returned page (up to 10 jobs) costs 1 credit.
   - Stop a search early when a page returns fewer than 10 jobs.
4. **Page budget (default 5 credits/day ≈ 150/month of the free 200):**

   | Search | Max pages |
   |---|---|
   | `Senior UX Designer in Bengaluru` | 3 |
   | `Senior Product Designer in Bengaluru` | 2 |

   `date_posted=3days` overlaps previous runs so a missed day loses nothing.
5. **Quota guard:** read `x-ratelimit-requests-remaining` from each response. If it
   drops below 10, fetch only page 1 of any remaining search.
6. **Normalize → filter → score** each job (rules below).
7. **Merge with history (`data/jobs.json`):**
   - Dedupe key: normalized `employer_name` + normalized `job_title` (lowercased,
     punctuation removed, whitespace collapsed). Duplicates merge their apply links.
   - New jobs get `first_seen = today`; returning jobs update `last_seen`.
   - Drop jobs whose `first_seen` is more than 14 days ago.
   - `new_today = (first_seen == today)`.
8. **Write** `data/jobs.json` and `data/status.json`, commit them with the workflow's
   `GITHUB_TOKEN` (`contents: write`), then deploy `site/` + `data/` to Pages.

## Job record (normalized)

Mapped from JSearch fields (verify names against the first real response):

| Field | From JSearch |
|---|---|
| `id` | dedupe key (see above) |
| `title` | `job_title` |
| `company`, `logo`, `company_site` | `employer_name`, `employer_logo`, `employer_website` |
| `city` | `job_city` (fallback `job_location`) |
| `posted_at` | `job_posted_at_timestamp` |
| `employment_type` | `job_employment_type` |
| `salary` | `job_min_salary`, `job_max_salary`, `job_salary_period` (omitted if absent) |
| `experience` | `job_required_experience.required_experience_in_months`, else parsed from description |
| `highlights` | `job_highlights.Qualifications`, `.Responsibilities` |
| `description` | `job_description` |
| `apply_links` | `job_apply_link` + `apply_options[]` (`publisher`, `apply_link`) |
| `score`, `tags` | computed |
| `first_seen`, `last_seen` | computed |

## Filtering (drop rules)

All keyword lists live in `config.yaml`. Matching is case-insensitive on whole words.

1. **Title must contain a role keyword:** `ux`, `ui/ux`, `user experience`,
   `product designer`, `product design`, `interaction designer`, `experience designer`.
2. **Title must not contain an unrelated-designer keyword:** `graphic`, `interior`,
   `fashion`, `textile`, `jewellery`/`jewelry`, `cad`, `mechanical`, `instructional`.
3. **Title must not contain a junior keyword:** `intern`, `internship`, `trainee`,
   `junior`, `jr`, `associate`, `fresher`.
4. **Experience:** drop if the upper bound of the parsed range is under 3 years. For a
   closed range the upper bound is `max` ("0–2 years" → 2 → drop; "2–4 years" → 4 →
   keep). For an open-ended "N+ years" it is `N` ("2+ years" → drop; "3+ years" →
   keep). If no experience can be found, keep the job.
5. **Location:** keep only if city/location contains `bengaluru` or `bangalore`.
   Remote-friendly roles listed under Bengaluru are kept.

## Experience parsing

Source order: structured JSearch months field → regex over title + description.

Recognized patterns (years): `4+ years`, `4 - 8 years`, `4–8 yrs`, `4 to 8 years`,
`minimum 4 years`, `at least 4 years`. Result is `(min, max)` with `max = None` for
open-ended. If several ranges appear, use the first one that mentions design/UX/product
within the same sentence, else the first one found.

## Scoring (0–100)

| Signal | Max | Rule |
|---|---|---|
| Title fit | 35 | Seniority word (`senior`, `sr`, `lead`, `staff`, `principal`) + role keyword → 35; role keyword only → 22 |
| Experience fit | 25 | min in 3–8 → 25; min = 9 → 15; min ≥ 10 → 8 and tag **May be very senior**; unknown → 15 |
| Industry boost | 25 | Gaming match → 25 (**Gaming**); consumer app / quick commerce / e-commerce match → 20 (**Consumer app** / **Quick commerce**); none → 0. Take the highest; show all matching tags |
| Freshness | 15 | Posted today 15, 1 day 12, 2 days 9, 3 days 6, then −1/day to 0 |

**Industry matching** uses two config lists per category: company names and description
keywords.

- Gaming companies (starter list): PlaySimple, BeBetta, Dream11, MPL, Games24x7,
  WinZO, Zynga, Moonfrog, Octro, Nazara, Gameberry, SuperGaming, Junglee Games,
  Kwalee, Rooter. Keywords: `game`, `gaming`, `mobile games`, `casual games`,
  `fantasy sports`, `prediction`.
- Quick commerce / e-commerce: Zepto, Swiggy, Blinkit, Zomato, Flipkart, BigBasket,
  Meesho, Myntra, Nykaa, Dunzo. Keywords: `quick commerce`, `q-commerce`, `e-commerce`.
- Consumer app keywords: `b2c`, `consumer app`, `consumer-facing`, `consumer product`.

## Dashboard (`site/index.html`)

- **Header:** "Senior UX / Product Designer jobs · Bengaluru", last refreshed time,
  total jobs, new today, API credits left this month.
- **Failure banner:** shown when `status.json` reports the last run failed, e.g.
  "Last refresh failed on 3 Oct: quota exhausted".
- **Controls:** search box (company, title, skills); tag chips (Gaming, Consumer app,
  Quick commerce, New today); sort toggle (Best match by score / Newest by `posted_at`).
- **Job card:** title, company + logo, posted ago, publisher(s), experience,
  salary (if any), employment type, score, tags, key qualifications and
  responsibilities, "Show full description" toggle, all apply links.
- **Marks:** "Applied" and "Not interested" buttons, stored in `localStorage` by job
  `id`. Marked jobs move to the bottom (Applied) or are hidden (Not interested), with a
  "Show hidden" toggle. Marks do not sync across devices.
- Responsive layout that works on mobile.

## Error handling

- **API errors, bad key, quota exhausted (HTTP 401/403/429/5xx, network):** keep the
  existing `data/jobs.json` untouched, write `status.json` with `ok: false` and a short
  reason, still commit + deploy so the banner shows, then exit non-zero so GitHub emails
  the user that the run failed.
- **Partial failure** (one search fails, another succeeds): merge what succeeded, mark
  `status.json` as `ok: false` with the failed search named.
- **Missing fields** on a job: card omits that section; job is never dropped for a
  missing optional field.
- **Malformed history file:** start fresh from today's results and record a warning in
  `status.json`.

## Testing

- `pytest` with fixtures in `tests/fixtures/` (saved JSearch responses); no network.
- Unit tests: title include/exclude rules, junior filter, experience parsing (each
  pattern + edge cases), location filter, each scoring signal, industry tag matching,
  dedupe/merge of apply links, 14-day expiry, `new_today` flag, quota-guard behavior,
  failure path keeps old data and writes failing status.
- CI: the daily workflow runs `pytest` before fetching.
- Acceptance: one manual workflow run after setup; check the live page together.

## One-time setup (user)

1. Create a free RapidAPI account and subscribe to JSearch **Basic** (200 requests/month).
2. Create a **public** GitHub repo and push this project.
3. Add repo secret `RAPIDAPI_KEY`.
4. In repo Settings → Pages, set source to **GitHub Actions**.
5. Run the workflow manually once.

## Out of scope (for now)

- Cities other than Bengaluru (config supports adding them later).
- Other data sources (Adzuna, company career boards).
- Email/Slack daily digests.
- Syncing Applied/Not interested marks across devices.

## Known risks

- JSearch free quota is hard-capped at 200/month; heavy manual runs can exhaust it.
- GitHub disables scheduled workflows after 60 days without repository activity; daily
  data commits normally count as activity.
- Google for Jobs coverage of India can vary day to day; results may be sparse on some days.
