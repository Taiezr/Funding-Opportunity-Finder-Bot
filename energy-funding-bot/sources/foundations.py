"""Foundation / non-federal opportunities from RSS feeds.

Generic and defensive: any RSS feed of funding opportunities can be added in
config.yaml. Each entry is kept only if it mentions one of your keywords.
A feed that is down or malformed is logged and skipped.
"""
import datetime
import time

import feedparser


def _entry_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.date(*t[:3])
    return None


def fetch(feeds, keywords):
    kws = [k.lower() for k in keywords]
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
            note = getattr(parsed, "bozo_exception", "no entries")
            print(f"[foundations] {name}: nothing parsed ({note})")
            continue

        kept = 0
        for e in parsed.entries:
            title = (e.get("title") or "").strip()
            summary = e.get("summary") or ""
            blob = f"{title} {summary}".lower()
            if kws and not any(k in blob for k in kws):
                continue
            link = e.get("link") or ""
            uid = f"foundation:{name}:{e.get('id') or link or title}"
            out.append({
                "uid": uid,
                "source": f"Foundation · {name}",
                "source_key": "foundation",
                "title": title,
                "agency": name,
                "number": "",
                "status": "open",
                "open_date": _entry_date(e),
                "close_date": None,   # most RFP feeds don't expose a clean deadline
                "url": link,
            })
            kept += 1
        print(f"[foundations] {name}: {kept} relevant of {len(parsed.entries)}")
    return out
