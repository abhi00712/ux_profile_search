import re
from functools import lru_cache


@lru_cache(maxsize=None)
def _pattern(keyword: str) -> re.Pattern:
    return re.compile(rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])")


def has_keyword(text: str, keywords: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(_pattern(k).search(lowered) for k in keywords)


def drop_reason(job: dict, cfg: dict) -> str | None:
    """Return why a job should be dropped, or None to keep it."""
    title_cfg = cfg["title"]
    title = job["title"]
    if not has_keyword(title, title_cfg["role_keywords"]):
        return "not a UX/product design title"
    if has_keyword(title, title_cfg["exclude_keywords"]):
        return "unrelated designer"
    if has_keyword(title, title_cfg["junior_keywords"]):
        return "junior title"

    experience = job.get("experience")
    if experience:
        low, high = experience
        upper = high if high is not None else low
        if upper < cfg["experience"]["min_upper_bound"]:
            return "too little experience"

    if not has_keyword(job.get("city", ""), cfg["location"]["city_keywords"]):
        return f"outside {cfg['location']['label']}"
    return None


def apply_filters(jobs: list[dict], cfg: dict) -> list[dict]:
    return [j for j in jobs if drop_reason(j, cfg) is None]
