import pytest

from scripts.scoring import (
    experience_points,
    freshness_points,
    industry_points,
    score_job,
    title_points,
)

DAY = 86400
NOW = 1790899200


def test_title_points(cfg):
    assert title_points("Senior Product Designer", cfg) == 35
    assert title_points("Lead UX Designer", cfg) == 35
    assert title_points("Product Designer", cfg) == 22


@pytest.mark.parametrize(
    "experience, points, tags",
    [
        ([4, 8], 25, []),
        ([2, 5], 25, []),
        ([9, None], 15, []),
        ([12, None], 8, ["May be very senior"]),
        (None, 15, []),
    ],
)
def test_experience_points(experience, points, tags):
    assert experience_points(experience) == (points, tags)


def test_industry_points_by_company(cfg):
    assert industry_points({"company": "PlaySimple Games", "description": ""}, cfg) == (25, ["Gaming"])


def test_industry_points_by_keyword(cfg):
    job = {"company": "Acme", "description": "We are a quick commerce startup."}
    assert industry_points(job, cfg) == (20, ["Quick commerce"])


def test_industry_points_takes_max_and_keeps_all_tags(cfg):
    job = {"company": "Acme", "description": "A B2C fantasy sports platform."}
    assert industry_points(job, cfg) == (25, ["Gaming", "Consumer app"])


def test_industry_points_none(cfg):
    job = {"company": "Acme", "description": "A game-changer for enterprise payroll."}
    assert industry_points(job, cfg) == (0, [])


@pytest.mark.parametrize(
    "age_days, points",
    [(0, 15), (1, 12), (2, 9), (3, 6), (5, 4), (20, 0)],
)
def test_freshness_points(age_days, points):
    assert freshness_points(NOW - age_days * DAY, NOW) == points


def test_freshness_unknown_date():
    assert freshness_points(None, NOW) == 0


def test_score_job_sums_and_does_not_mutate(cfg):
    job = {
        "title": "Senior UX Designer",
        "company": "PlaySimple Games",
        "description": "",
        "experience": [4, 8],
        "posted_at": NOW,
    }
    scored = score_job(job, cfg, NOW)

    assert scored["score"] == 35 + 25 + 25 + 15
    assert scored["tags"] == ["Gaming"]
    assert "score" not in job
