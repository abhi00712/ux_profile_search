import re

from scripts.experience import parse_experience

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _clean(text: str) -> str:
    return _NON_ALNUM.sub(" ", (text or "").lower()).strip()


def make_key(company: str, title: str) -> str:
    return f"{_clean(company)}|{_clean(title)}"


def _experience(raw: dict, title: str, description: str) -> list | None:
    months = (raw.get("job_required_experience") or {}).get("required_experience_in_months")
    if months:
        return [round(months / 12), None]
    return parse_experience(f"{title}\n{description}")


def _salary(raw: dict) -> dict | None:
    low, high = raw.get("job_min_salary"), raw.get("job_max_salary")
    if low is None and high is None:
        return None
    return {"min": low, "max": high, "period": raw.get("job_salary_period")}


def _apply_links(raw: dict) -> list[dict]:
    candidates = [{"publisher": raw.get("job_publisher"), "url": raw.get("job_apply_link")}]
    candidates += [
        {"publisher": o.get("publisher"), "url": o.get("apply_link")}
        for o in raw.get("apply_options") or []
    ]
    links, seen = [], set()
    for link in candidates:
        if link["url"] and link["url"] not in seen:
            seen.add(link["url"])
            links.append(link)
    return links


def normalize(raw: dict) -> dict:
    title = raw.get("job_title") or ""
    company = raw.get("employer_name") or ""
    description = raw.get("job_description") or ""
    highlights = raw.get("job_highlights") or {}
    return {
        "id": make_key(company, title),
        "title": title,
        "company": company,
        "logo": raw.get("employer_logo"),
        "company_site": raw.get("employer_website"),
        "city": raw.get("job_city") or raw.get("job_location") or "",
        "posted_at": raw.get("job_posted_at_timestamp"),
        "employment_type": raw.get("job_employment_type"),
        "salary": _salary(raw),
        "experience": _experience(raw, title, description),
        "highlights": {
            "qualifications": highlights.get("Qualifications") or [],
            "responsibilities": highlights.get("Responsibilities") or [],
        },
        "description": description,
        "apply_links": _apply_links(raw),
    }
