import pytest

from scripts.jsearch import JSearchError, search_page


class StubResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


class StubSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self.response


def call(session, page=1):
    return search_page(session, "key", "Senior UX Designer in Bengaluru", page, "in", "3days")


def test_search_page_sends_expected_request_and_reads_credits():
    session = StubSession(
        StubResponse(
            payload={"status": "OK", "data": [{"job_id": "a"}]},
            headers={"x-ratelimit-requests-remaining": "187"},
        )
    )

    result = call(session, page=2)

    assert result.jobs == [{"job_id": "a"}]
    assert result.credits_left == 187
    sent = session.calls[0]
    assert sent["params"] == {
        "query": "Senior UX Designer in Bengaluru",
        "page": 2,
        "num_pages": 1,
        "country": "in",
        "date_posted": "3days",
    }
    assert sent["headers"]["X-RapidAPI-Key"] == "key"


def test_search_page_accepts_jobs_nested_under_data():
    session = StubSession(StubResponse(payload={"status": "OK", "data": {"jobs": [{"job_id": "b"}]}}))

    assert call(session).jobs == [{"job_id": "b"}]


def test_search_page_raises_on_http_error():
    session = StubSession(StubResponse(status_code=429, text="Too many requests"))

    with pytest.raises(JSearchError, match="HTTP 429"):
        call(session)


def test_search_page_raises_on_error_status():
    session = StubSession(StubResponse(payload={"status": "ERROR", "error": {"message": "bad"}}))

    with pytest.raises(JSearchError, match="bad"):
        call(session)
