# Daily job dashboard

Once a day, a GitHub Actions run fetches Senior UX / Product Designer jobs in Bengaluru from
[JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch), filters and ranks them, and
publishes a dashboard on GitHub Pages.

- Searches, cities, keywords and ranking boosts: `config.yaml`
- Design: `docs/superpowers/specs/2026-10-02-job-dashboard-design.md`

## One-time setup

1. Create a free RapidAPI account and subscribe to JSearch **Basic** (200 requests/month).
2. Add the key as a repository secret: `gh secret set RAPIDAPI_KEY`.
3. In repository Settings → Pages, set the source to **GitHub Actions**.
4. Run the workflow once: `gh workflow run daily.yml`.

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q

# Preview with sample data (no API credits used)
.venv/bin/python -m scripts.fetch_jobs --from-fixture tests/fixtures/search_page.json
mkdir -p _site && cp -r site/. _site/ && cp -r data _site/data
python3 -m http.server -d _site 8000
```

Delete `data/` after previewing so sample jobs are not committed.

## Quota

Each returned page of up to 10 jobs costs one credit. The default budget is 5 pages a day
(about 150 a month). Below 10 remaining credits, only the first page of each search is fetched.
