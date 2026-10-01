import pytest

from scripts.filters import apply_filters, drop_reason, has_keyword
from scripts.normalize import normalize


def job(title="Senior Product Designer", city="Bengaluru", experience=None):
    return {"title": title, "city": city, "experience": experience}


@pytest.mark.parametrize(
    "kwargs, reason",
    [
        ({}, None),
        ({"title": "UI/UX Designer", "city": "Bangalore, Karnataka"}, None),
        ({"title": "Interior Designer"}, "not a UX/product design title"),
        ({"title": "Graphic & UX Designer"}, "unrelated designer"),
        ({"title": "Product Design Intern"}, "junior title"),
        ({"title": "Junior UX Designer"}, "junior title"),
        ({"title": "Associate Product Designer"}, "junior title"),
        ({"experience": [0, 2]}, "too little experience"),
        ({"experience": [2, None]}, "too little experience"),
        ({"experience": [2, 4]}, None),
        ({"experience": [3, None]}, None),
        ({"city": "Pune"}, "outside Bengaluru"),
    ],
)
def test_drop_reason(cfg, kwargs, reason):
    assert drop_reason(job(**kwargs), cfg) == reason


def test_has_keyword_matches_whole_words_only():
    assert has_keyword("Sr. Designer", ["sr"])
    assert not has_keyword("Design Academy", ["cad"])
    assert has_keyword("UI/UX Designer", ["ux"])


def test_apply_filters_on_fixture(cfg, raw_jobs):
    kept = apply_filters([normalize(r) for r in raw_jobs], cfg)

    assert sorted({j["company"] for j in kept}) == ["PlaySimple Games", "Zepto"]
    assert [j["title"] for j in kept if j["company"] == "Zepto"] == ["Lead Product Designer"]
