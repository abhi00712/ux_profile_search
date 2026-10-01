import json
from pathlib import Path

import pytest

from scripts.config import load_config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def cfg():
    return load_config(str(ROOT / "config.yaml"))


@pytest.fixture
def raw_jobs():
    with open(ROOT / "tests" / "fixtures" / "search_page.json", encoding="utf-8") as f:
        return json.load(f)["data"]


@pytest.fixture
def raw_by_id(raw_jobs):
    return {job["job_id"]: job for job in raw_jobs}
