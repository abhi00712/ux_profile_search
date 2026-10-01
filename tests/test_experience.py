import pytest

from scripts.experience import parse_experience


@pytest.mark.parametrize(
    "text, expected",
    [
        ("4+ years of UX experience", [4, None]),
        ("4 - 8 years", [4, 8]),
        ("4–8 yrs", [4, 8]),
        ("4 to 8 years", [4, 8]),
        ("Minimum 5 years in product design", [5, None]),
        ("at least 3 years", [3, None]),
        ("5 years of experience", [5, None]),
        ("0-2 years", [0, 2]),
        ("Company founded 10 years ago. You need 4+ years of UX design.", [4, None]),
        ("Great team, no numbers here", None),
        ("", None),
    ],
)
def test_parse_experience(text, expected):
    assert parse_experience(text) == expected


def test_prefers_range_over_plus_inside_same_match():
    assert parse_experience("We want 3+ - 6 years in UX") == [3, 6]


def test_ignores_reversed_or_absurd_ranges():
    assert parse_experience("8-4 years") is None
    assert parse_experience("5-50 years") is None
