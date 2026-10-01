import json
from datetime import datetime, timezone

from scripts.fetch_jobs import fetch_all, main, run
from scripts.jsearch import JSearchError, PageResult

NOW = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)


def filler(n, prefix):
    return [{"job_id": f"{prefix}{i}", "job_title": f"Designer {prefix}{i}"} for i in range(n)]


class FakeSearch:
    def __init__(self, pages, credits=150, fail_queries=()):
        self.pages = pages
        self.credits = credits
        self.fail_queries = set(fail_queries)
        self.calls = []

    def __call__(self, query, page):
        self.calls.append((query, page))
        if query in self.fail_queries:
            raise JSearchError("HTTP 500: boom")
        self.credits -= 1
        return PageResult(jobs=self.pages.get((query, page), []), credits_left=self.credits)


def two_search_cfg(cfg):
    return {
        **cfg,
        "searches": [
            {"query": "ux", "max_pages": 3},
            {"query": "product", "max_pages": 2},
        ],
    }


def test_fetch_all_stops_on_short_page_and_respects_max_pages(cfg):
    search = FakeSearch(
        {
            ("ux", 1): filler(10, "u1-"),
            ("ux", 2): filler(4, "u2-"),
            ("product", 1): filler(10, "p1-"),
            ("product", 2): filler(10, "p2-"),
        }
    )

    raw, errors, credits = fetch_all(two_search_cfg(cfg), search)

    assert search.calls == [("ux", 1), ("ux", 2), ("product", 1), ("product", 2)]
    assert len(raw) == 34
    assert errors == []
    assert credits == 146


def test_fetch_all_quota_guard_limits_to_first_page(cfg):
    search = FakeSearch({("ux", 1): filler(10, "u"), ("product", 1): filler(10, "p")}, credits=8)

    fetch_all(two_search_cfg(cfg), search)

    assert search.calls == [("ux", 1), ("product", 1)]


def test_run_success_writes_sorted_jobs_and_status(cfg, raw_jobs, tmp_path):
    jobs_path, status_path = tmp_path / "jobs.json", tmp_path / "status.json"
    search = FakeSearch({("ux", 1): raw_jobs})

    ok = run(two_search_cfg(cfg), str(jobs_path), str(status_path), search, NOW)

    assert ok is True
    jobs = json.loads(jobs_path.read_text())["jobs"]
    assert [j["company"] for j in jobs] == ["PlaySimple Games", "Zepto"]
    assert jobs[0]["score"] >= jobs[1]["score"]
    assert len(jobs[0]["apply_links"]) == 3
    assert all(j["new_today"] for j in jobs)
    status = json.loads(status_path.read_text())
    assert status["ok"] is True
    assert status["error"] is None
    assert status["credits_left"] == 148
    assert status["counts"] == {"fetched": 7, "kept": 2, "new_today": 2}


def test_run_partial_failure_keeps_successful_results(cfg, raw_jobs, tmp_path):
    jobs_path, status_path = tmp_path / "jobs.json", tmp_path / "status.json"
    search = FakeSearch({("ux", 1): raw_jobs}, fail_queries={"product"})

    ok = run(two_search_cfg(cfg), str(jobs_path), str(status_path), search, NOW)

    assert ok is False
    assert len(json.loads(jobs_path.read_text())["jobs"]) == 2
    status = json.loads(status_path.read_text())
    assert status["ok"] is False
    assert "product" in status["error"]


def test_main_without_api_key_writes_failing_status(monkeypatch, tmp_path):
    monkeypatch.delenv("RAPIDAPI_KEY", raising=False)

    assert main(["--data-dir", str(tmp_path)]) == 1
    status = json.loads((tmp_path / "status.json").read_text())
    assert status["ok"] is False
    assert "RAPIDAPI_KEY" in status["error"]


def test_run_total_failure_leaves_jobs_untouched(cfg, tmp_path):
    jobs_path, status_path = tmp_path / "jobs.json", tmp_path / "status.json"
    jobs_path.write_text('{"updated_at": "before", "jobs": []}')
    search = FakeSearch({}, fail_queries={"ux", "product"})

    ok = run(two_search_cfg(cfg), str(jobs_path), str(status_path), search, NOW)

    assert ok is False
    assert jobs_path.read_text() == '{"updated_at": "before", "jobs": []}'
    assert json.loads(status_path.read_text())["ok"] is False
