from dataclasses import dataclass

URL = "https://jsearch.p.rapidapi.com/search"
HOST = "jsearch.p.rapidapi.com"
PAGE_SIZE = 10


class JSearchError(Exception):
    pass


@dataclass
class PageResult:
    jobs: list[dict]
    credits_left: int | None


def search_page(session, api_key: str, query: str, page: int, country: str, date_posted: str) -> PageResult:
    response = session.get(
        URL,
        params={
            "query": query,
            "page": page,
            "num_pages": 1,
            "country": country,
            "date_posted": date_posted,
        },
        headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": HOST},
        timeout=30,
    )
    if response.status_code != 200:
        raise JSearchError(f"HTTP {response.status_code}: {response.text[:200]}")

    payload = response.json()
    if payload.get("status") != "OK":
        message = (payload.get("error") or {}).get("message") or payload.get("message") or "unknown error"
        raise JSearchError(f"API error: {message}")

    data = payload.get("data") or []
    jobs = data.get("jobs", []) if isinstance(data, dict) else data

    remaining = response.headers.get("x-ratelimit-requests-remaining")
    credits_left = int(remaining) if remaining is not None and str(remaining).isdigit() else None
    return PageResult(jobs=jobs, credits_left=credits_left)
