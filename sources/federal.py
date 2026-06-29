"""Federal funding via the Grants.gov Search2 + fetchOpportunity APIs (no key).

Two-stage:
  1) search2 collects candidate opportunity IDs (Energy category + each keyword).
  2) fetchOpportunity pulls each candidate's full record so we can (a) enforce a
     real keyword match against the actual description and (b) read the award
     amount. Anything that doesn't truly mention a keyword is dropped.

Docs: https://grants.gov/api/common/search2  +  /api/common/fetchopportunity
"""
import datetime
import time

import requests

from sources import match_keywords

SEARCH = "https://api.grants.gov/v1/api/search2"
FETCH = "https://api.grants.gov/v1/api/fetchOpportunity"
DETAIL = "https://grants.gov/search-results-detail/{oid}"

_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def _post(url, body, tries=4):
    delay = 1.0
    for attempt in range(tries):
        r = _session.post(url, json=body, timeout=30)
        if r.status_code == 429:           # rate limited — back off and retry
            time.sleep(delay)
            delay *= 2
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def _parse_mdy(s):
    s = (s or "").strip()
    try:
        return datetime.datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        return None


def _to_int(s):
    try:
        n = int(float(str(s).replace(",", "").strip()))
        return n if n > 0 else None
    except (ValueError, TypeError):
        return None


def _search_candidates(keywords, funding_categories, statuses, max_per_query):
    """Collect unique candidate hits (id -> basic fields) from search2."""
    queries = []
    if funding_categories:
        queries.append({"fundingCategories": funding_categories})
    for kw in keywords:
        queries.append({"keyword": kw})

    rows = 100
    by_id = {}
    for q in queries:
        start = 0
        while start < max_per_query:
            body = {"rows": rows, "oppStatuses": statuses, "startRecordNum": start}
            body.update(q)
            try:
                data = _post(SEARCH, body).get("data", {})
            except Exception as e:  # noqa: BLE001
                print(f"[federal] search {q} @ {start} failed: {e}")
                break
            hits = data.get("oppHits") or []
            for h in hits:
                oid = str(h.get("id", "")).strip()
                if oid and oid not in by_id:
                    by_id[oid] = h
            total = data.get("hitCount", len(hits))
            start += rows
            if len(hits) < rows or start >= total:
                break
    return by_id


def _detail(oid):
    """Award amounts + description text for one opportunity (or {} on failure)."""
    try:
        data = _post(FETCH, {"opportunityId": int(oid)}).get("data", {})
    except Exception as e:  # noqa: BLE001
        print(f"[federal] detail {oid} failed: {e}")
        return {}
    syn = data.get("synopsis") or {}
    return {
        "description": syn.get("synopsisDesc") or "",
        "award_ceiling": _to_int(syn.get("awardCeiling")),
        "award_floor": _to_int(syn.get("awardFloor")),
        "agency_name": syn.get("agencyName") or "",
    }


def fetch(keywords, funding_categories="EN", statuses="posted|forecasted",
          max_per_query=300, max_details=200, pause=0.1):
    candidates = _search_candidates(keywords, funding_categories, statuses,
                                    max_per_query)
    print(f"[federal] {len(candidates)} candidates; fetching details "
          f"(cap {max_details})")

    results = []
    for i, (oid, h) in enumerate(candidates.items()):
        if i >= max_details:
            print(f"[federal] hit detail cap at {max_details}; "
                  f"{len(candidates) - max_details} not enriched")
            break
        det = _detail(oid)
        if pause:
            time.sleep(pause)

        title = (h.get("title") or "").strip()
        agency = det.get("agency_name") or h.get("agencyName") or \
            h.get("agencyCode") or ""
        matched = match_keywords(f"{title} {det.get('description', '')}", keywords)
        if not matched:                    # the real relevance gate
            continue

        results.append({
            "uid": f"grants_gov:{oid}",
            "source": "Grants.gov",
            "source_key": "federal",
            "title": title,
            "agency": agency.strip(),
            "number": (h.get("number") or "").strip(),
            "status": (h.get("oppStatus") or "").strip(),
            "open_date": _parse_mdy(h.get("openDate")),
            "close_date": _parse_mdy(h.get("closeDate")),
            "award_ceiling": det.get("award_ceiling"),
            "award_floor": det.get("award_floor"),
            "matched_keywords": matched,
            "url": DETAIL.format(oid=oid),
        })

    print(f"[federal] {len(results)} relevant after keyword filter")
    return results
