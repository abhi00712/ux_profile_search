import json
import os
from datetime import date


def _union_links(*link_lists: list[dict]) -> list[dict]:
    links, seen = [], set()
    for link in (l for lst in link_lists for l in lst):
        if link["url"] not in seen:
            seen.add(link["url"])
            links.append(link)
    return links


def dedupe(jobs: list[dict]) -> list[dict]:
    """Collapse jobs sharing an id, keeping the fuller description and every apply link."""
    by_id: dict[str, dict] = {}
    for job in jobs:
        current = by_id.get(job["id"])
        if current is None:
            by_id[job["id"]] = job
            continue
        richer, other = (
            (job, current)
            if len(job.get("description") or "") > len(current.get("description") or "")
            else (current, job)
        )
        by_id[job["id"]] = {
            **richer,
            "apply_links": _union_links(richer["apply_links"], other["apply_links"]),
        }
    return list(by_id.values())


def merge(existing: list[dict], fresh: list[dict], today: str, expire_days: int) -> list[dict]:
    by_id = {j["id"]: j for j in existing}
    for job in fresh:
        old = by_id.get(job["id"])
        if old:
            job = {
                **job,
                "first_seen": old["first_seen"],
                "apply_links": _union_links(job["apply_links"], old.get("apply_links", [])),
            }
        else:
            job = {**job, "first_seen": today}
        by_id[job["id"]] = {**job, "last_seen": today}

    today_date = date.fromisoformat(today)
    kept = []
    for job in by_id.values():
        if (today_date - date.fromisoformat(job["first_seen"])).days > expire_days:
            continue
        kept.append({**job, "new_today": job["first_seen"] == today})
    return kept


def load_jobs(path: str) -> tuple[list[dict], str | None]:
    if not os.path.exists(path):
        return [], None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [], f"could not read {os.path.basename(path)} ({e}); started fresh"
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    return jobs, None


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
