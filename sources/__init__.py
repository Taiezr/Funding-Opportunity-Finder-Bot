"""Shared helpers for sources."""
import re
from functools import lru_cache


@lru_cache(maxsize=256)
def _pattern(keyword):
    # Whole-word / whole-phrase, case-insensitive. Hyphens and spaces tolerated.
    esc = re.escape(keyword.strip()).replace(r"\ ", r"[\s-]+")
    return re.compile(rf"(?<![A-Za-z]){esc}(?![A-Za-z])", re.IGNORECASE)


def match_keywords(text, keywords):
    """Return the subset of `keywords` that appear as whole words in `text`."""
    text = text or ""
    return [kw for kw in keywords if _pattern(kw).search(text)]
