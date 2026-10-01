import re

_N = r"(\d{1,2})"
_YEARS = r"(?:years?|yrs?)"

# Highest-priority pattern first; lower-priority matches overlapping an earlier one are ignored.
_PATTERNS = [
    ("range", re.compile(rf"{_N}\s*\+?\s*(?:-|–|—|to)\s*{_N}\s*\+?\s*{_YEARS}", re.I)),
    ("min", re.compile(rf"(?:minimum(?:\s+of)?|at\s+least|min\.?)\s*{_N}\s*\+?\s*{_YEARS}", re.I)),
    ("plus", re.compile(rf"{_N}\s*\+\s*{_YEARS}", re.I)),
    ("plain", re.compile(rf"{_N}\s*{_YEARS}\s+(?:of\s+)?(?:\w+\s+)?experience", re.I)),
]
_RELEVANT = re.compile(r"design|ux|product", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;\n])\s+")
_MAX_YEARS = 30


def _matches(sentence: str) -> list[tuple[int, list]]:
    found: list[tuple[int, int, list]] = []
    for kind, pattern in _PATTERNS:
        for m in pattern.finditer(sentence):
            if any(m.start() < end and start < m.end() for start, end, _ in found):
                continue
            if kind == "range":
                lo, hi = int(m.group(1)), int(m.group(2))
                if lo > hi or hi > _MAX_YEARS:
                    found.append((m.start(), m.end(), None))
                    continue
                value = [lo, hi]
            else:
                value = [int(m.group(1)), None]
            found.append((m.start(), m.end(), value))
    return [(start, value) for start, _, value in sorted(found) if value is not None]


def parse_experience(text: str) -> list | None:
    """Return [min_years, max_years_or_None] for the most relevant mention, or None."""
    first = None
    for sentence in _SENTENCE_SPLIT.split(text or ""):
        matches = _matches(sentence)
        if not matches:
            continue
        if _RELEVANT.search(sentence):
            return matches[0][1]
        if first is None:
            first = matches[0][1]
    return first
