"""Daily run: fetch jobs from JSearch, filter, score, merge with history, write data/*.json."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from functools import partial
from zoneinfo import ZoneInfo

from scripts.config import load_config
from scripts.filters import apply_filters
from scripts.jsearch import PAGE_SIZE, JSearchError, PageResult, search_page
from scripts.normalize import normalize
from scripts.scoring import score_job
from scripts.store import dedupe, load_jobs, merge, write_json

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def fetch_all(cfg: dict, search_fn) -> tuple[list[dict], list[str], int | None]:
    raw, errors, credits_left = [], [], None
    for search in cfg["searches"]:
        query = search["query"]
        for page in range(1, search["max_pages"] + 1):
            if page > 1 and credits_left is not None and credits_left < cfg["quota_guard"]:
                break
            try:
                result = search_fn(query, page)
            except JSearchError as e:
                errors.append(f"{query} (page {page}): {e}")
                break
            raw.extend(result.jobs)
            if result.credits_left is not None:
                credits_left = result.credits_left
            if len(result.jobs) < PAGE_SIZE:
                break
    return raw, errors, credits_left


def run(cfg: dict, jobs_path: str, status_path: str, search_fn, now: datetime) -> bool:
    existing, warning = load_jobs(jobs_path)
    raw, errors, credits_left = fetch_all(cfg, search_fn)
    status = {
        "ok": not errors,
        "ran_at": now.astimezone(LOCAL_TZ).isoformat(timespec="minutes"),
        "error": "; ".join(errors) or None,
        "warning": warning,
        "credits_left": credits_left,
        "location": cfg["location"]["label"],
    }

    if errors and not raw:
        write_json(status_path, {**status, "counts": None})
        return False

    today = now.astimezone(LOCAL_TZ).date().isoformat()
    fresh = dedupe([normalize(r) for r in raw])
    merged = merge(existing, fresh, today, cfg["expire_days"])
    now_ts = int(now.timestamp())
    jobs = sorted(
        (score_job(j, cfg, now_ts) for j in apply_filters(merged, cfg)),
        key=lambda j: (j["score"], j.get("posted_at") or 0),
        reverse=True,
    )

    write_json(jobs_path, {"updated_at": status["ran_at"], "jobs": jobs})
    status["counts"] = {
        "fetched": len(raw),
        "kept": len(jobs),
        "new_today": sum(1 for j in jobs if j["new_today"]),
    }
    write_json(status_path, status)
    return not errors


def _fixture_search(path: str):
    with open(path, encoding="utf-8") as f:
        jobs = json.load(f)["data"]
    return lambda query, page: PageResult(jobs=jobs if page == 1 else [], credits_left=None)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--from-fixture", help="use a saved JSearch response instead of the API")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    jobs_path = os.path.join(args.data_dir, "jobs.json")
    status_path = os.path.join(args.data_dir, "status.json")
    now = datetime.now(timezone.utc)

    if args.from_fixture:
        search_fn = _fixture_search(args.from_fixture)
    else:
        api_key = os.environ.get("RAPIDAPI_KEY")
        if not api_key:
            write_json(
                status_path,
                {
                    "ok": False,
                    "ran_at": now.astimezone(LOCAL_TZ).isoformat(timespec="minutes"),
                    "error": "RAPIDAPI_KEY secret is not set",
                    "warning": None,
                    "credits_left": None,
                    "location": cfg["location"]["label"],
                    "counts": None,
                },
            )
            print("RAPIDAPI_KEY is not set", file=sys.stderr)
            return 1
        import requests

        search_fn = partial(
            _search_with_session,
            requests.Session(),
            api_key,
            cfg["location"]["country"],
            cfg["date_posted"],
        )

    ok = run(cfg, jobs_path, status_path, search_fn, now)
    with open(status_path, encoding="utf-8") as f:
        print(f.read())
    return 0 if ok else 1


def _search_with_session(session, api_key, country, date_posted, query, page):
    return search_page(session, api_key, query, page, country, date_posted)


if __name__ == "__main__":
    sys.exit(main())
