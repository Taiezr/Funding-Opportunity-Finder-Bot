"""Foundation / non-federal opportunities from RSS feeds.

Generic and defensive: any RSS feed of funding opportunities can be added in
config.yaml. An item is kept only if it mentions one of your keywords. A feed
that is down or malformed is logged and skipped.
"""
import datetime

import feedparser

from sources import match_keywords


def _entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.date(*t[:3])
    return None


def fetch(feeds, keywords):
    out = []
    for feed in feeds or []:
        url = feed.get("url", "")
        name = feed.get("name") or url
        try:
            parsed = feedparser.parse(url)
        except Exception as e:  # noqa: BLE001
            print(f"[foundations] {name}: fetch error: {e}")
            continue
        if not parsed.entries:
            print(f"[foundations] {name}: nothing parsed "
                  f"({getattr(parsed, 'bozo_exception', 'no entries')})")
            continue

        kept = 0
        for e in parsed.entries:
            title = (e.get("title") or "").strip()
            summary = e.get("summary") or ""
            matched = match_keywords(f"{title} {summary}", keywords)
            if keywords and not matched:
                continue
            link = e.get("link") or ""
            out.append({
                "uid": f"foundation:{name}:{e.get('id') or link or title}",
                "source": name,
                "source_key": "foundation",
                "title": title,
                "agency": name,
                "number": "",
                "status": "open",
                "open_date": _entry_date(e),
                "close_date": None,        # RFP feeds rarely expose a clean deadline
                "award_ceiling": None,
                "award_floor": None,
                "matched_keywords": matched,
                "url": link,
            })
            kept += 1
        print(f"[foundations] {name}: {kept} relevant of {len(parsed.entries)}")
    return out
