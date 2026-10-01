from scripts.normalize import make_key, normalize


def test_make_key_lowercases_and_strips_punctuation():
    assert make_key("Swiggy ", "Sr. Product Designer!") == "swiggy|sr product designer"


def test_normalize_maps_fields(raw_by_id):
    job = normalize(raw_by_id["a1"])

    assert job["id"] == "playsimple games|senior ux designer"
    assert job["title"] == "Senior UX Designer"
    assert job["company"] == "PlaySimple Games"
    assert job["logo"] == "https://example.com/playsimple.png"
    assert job["city"] == "Bengaluru"
    assert job["posted_at"] == 1790899200
    assert job["employment_type"] == "Full-time"
    assert job["salary"] is None
    assert job["experience"] == [4, 8]
    assert job["highlights"]["qualifications"][0] == "4-8 years of UX design experience"
    assert job["highlights"]["responsibilities"] == ["Own end-to-end UX for live games"]
    assert job["apply_links"] == [
        {"publisher": "LinkedIn", "url": "https://www.linkedin.com/jobs/view/a1"},
        {"publisher": "PlaySimple Careers", "url": "https://careers.playsimple.in/a1"},
    ]


def test_normalize_prefers_structured_experience_and_maps_salary(raw_by_id):
    job = normalize(raw_by_id["e1"])

    assert job["experience"] == [6, None]
    assert job["salary"] == {"min": 3000000, "max": 4500000, "period": "YEAR"}


def test_normalize_tolerates_missing_optional_fields(raw_by_id):
    job = normalize(raw_by_id["f1"])

    assert job["logo"] is None
    assert job["city"] == "Bangalore, Karnataka"
    assert job["employment_type"] is None
    assert job["highlights"] == {"qualifications": [], "responsibilities": []}
    assert job["apply_links"] == [{"publisher": "Indeed", "url": "https://in.indeed.com/f1"}]
