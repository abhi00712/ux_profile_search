import json

from scripts.store import dedupe, load_jobs, merge, write_json

TODAY = "2026-10-02"


def make(id_, description="", links=(), first_seen=None):
    job = {
        "id": id_,
        "description": description,
        "apply_links": [{"publisher": p, "url": u} for p, u in links],
    }
    if first_seen:
        job["first_seen"] = first_seen
        job["last_seen"] = first_seen
    return job


def test_dedupe_merges_links_and_keeps_longer_description():
    a = make("x", "short", [("LinkedIn", "https://l/1")])
    b = make("x", "a much longer description", [("Naukri", "https://n/1"), ("LinkedIn", "https://l/1")])

    [merged] = dedupe([a, b])

    assert merged["description"] == "a much longer description"
    assert [l["url"] for l in merged["apply_links"]] == ["https://n/1", "https://l/1"]


def test_merge_marks_new_and_returning_jobs():
    existing = [make("old", first_seen="2026-09-28")]
    fresh = [make("old"), make("new")]

    by_id = {j["id"]: j for j in merge(existing, fresh, TODAY, 14)}

    assert by_id["new"]["first_seen"] == TODAY
    assert by_id["new"]["new_today"] is True
    assert by_id["old"]["first_seen"] == "2026-09-28"
    assert by_id["old"]["last_seen"] == TODAY
    assert by_id["old"]["new_today"] is False


def test_merge_keeps_unseen_recent_jobs_and_expires_old_ones():
    existing = [
        make("recent", first_seen="2026-09-25"),
        make("stale", first_seen="2026-09-17"),
    ]

    ids = {j["id"] for j in merge(existing, [], TODAY, 14)}

    assert ids == {"recent"}


def test_merge_keeps_links_seen_on_earlier_days():
    existing = [make("x", links=[("LinkedIn", "https://l/1")], first_seen="2026-09-30")]
    fresh = [make("x", links=[("Naukri", "https://n/1")])]

    [job] = merge(existing, fresh, TODAY, 14)

    assert [l["url"] for l in job["apply_links"]] == ["https://n/1", "https://l/1"]


def test_load_jobs_missing_file(tmp_path):
    assert load_jobs(str(tmp_path / "nope.json")) == ([], None)


def test_load_jobs_malformed_file(tmp_path):
    path = tmp_path / "jobs.json"
    path.write_text("{not json")

    jobs, warning = load_jobs(str(path))

    assert jobs == []
    assert "could not read" in warning


def test_write_then_load_round_trip(tmp_path):
    path = tmp_path / "data" / "jobs.json"
    write_json(str(path), {"updated_at": "x", "jobs": [make("a")]})

    assert json.loads(path.read_text())["jobs"][0]["id"] == "a"
    assert load_jobs(str(path)) == ([make("a")], None)
