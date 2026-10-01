from scripts.filters import has_keyword

DAY = 86400
VERY_SENIOR_TAG = "May be very senior"
_FRESHNESS_BY_AGE = [15, 12, 9, 6]


def title_points(title: str, cfg: dict) -> int:
    title_cfg = cfg["title"]
    if not has_keyword(title, title_cfg["role_keywords"]):
        return 0
    return 35 if has_keyword(title, title_cfg["seniority_keywords"]) else 22


def experience_points(experience: list | None) -> tuple[int, list[str]]:
    if not experience:
        return 15, []
    low = experience[0]
    if low <= 8:
        return 25, []
    if low == 9:
        return 15, []
    return 8, [VERY_SENIOR_TAG]


def industry_points(job: dict, cfg: dict) -> tuple[int, list[str]]:
    text = f"{job.get('title', '')}\n{job.get('description', '')}"
    points, tags = 0, []
    for industry in cfg["industries"]:
        if has_keyword(job.get("company", ""), industry["companies"]) or has_keyword(
            text, industry["keywords"]
        ):
            points = max(points, industry["points"])
            tags.append(industry["tag"])
    return points, tags


def freshness_points(posted_at: int | None, now_ts: int) -> int:
    if posted_at is None:
        return 0
    age = max(0, (now_ts - posted_at) // DAY)
    if age < len(_FRESHNESS_BY_AGE):
        return _FRESHNESS_BY_AGE[age]
    return max(0, _FRESHNESS_BY_AGE[-1] - (age - (len(_FRESHNESS_BY_AGE) - 1)))


def score_job(job: dict, cfg: dict, now_ts: int) -> dict:
    exp_pts, exp_tags = experience_points(job.get("experience"))
    ind_pts, ind_tags = industry_points(job, cfg)
    total = (
        title_points(job["title"], cfg)
        + exp_pts
        + ind_pts
        + freshness_points(job.get("posted_at"), now_ts)
    )
    return {**job, "score": min(100, total), "tags": ind_tags + exp_tags}
