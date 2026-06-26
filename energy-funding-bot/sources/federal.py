"""Federal funding via the Grants.gov Search2 API.

Search2 is public (no API key) and aggregates grant postings across federal
agencies, including DOE, ARPA-E, NSF, EPA, and USDA. We run one sweep of the
Energy funding category plus one search per keyword, then de-duplicate by id.

Docs: https://grants.gov/api/common/search2
"""
import datetime

import requests

API = "https://api.grants.gov/v1/api/search2"
DETAIL = "https://grants.gov/search-results-detail/{oid}"


def _post(body):
    r = requests.post(API, json=body, timeout=30,
                      headers={"Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        return None


def _normalize(h):
    oid = str(h.get("id", "")).strip()
    return {
        "uid": f"grants_gov:{oid}",
        "source": "Federal · Grants.gov",
        "source_key": "federal",
        "title": (h.get("title") or "").strip(),
        "agency": (h.get("agencyName") or h.get("agencyCode") or "").strip(),
        "number": (h.get("number") or "").strip(),
        "status": (h.get("oppStatus") or "").strip(),
        "open_date": _parse_date(h.get("openDate")),
        "close_date": _parse_date(h.get("closeDate")),
        "url": DETAIL.format(oid=oid),
    }


def _paged_query(query, statuses, max_results):
    """Run one search query, paging until exhausted or max_results reached."""
    rows = 100
    start = 0
    out = []
    while start < max_results:
        body = {"rows": rows, "oppStatuses": statuses, "startRecordNum": start}
        body.update(query)
        data = _post(body).get("data", {})
        hits = data.get("oppHits") or []
        out.extend(hits)
        total = data.get("hitCount", len(out))
        start += rows
        if len(hits) < rows or start >= total:
            break
    return out


def fetch(keywords, funding_categories="EN", statuses="posted|forecasted",
          max_per_query=300):
    """Return a de-duplicated list of normalized federal opportunities."""
    queries = []
    if funding_categories:
        queries.append({"fundingCategories": funding_categories})
    for kw in keywords:
        queries.append({"keyword": kw})

    by_id = {}
    for q in queries:
        try:
            hits = _paged_query(q, statuses, max_per_query)
        except Exception as e:  # noqa: BLE001 — one bad query shouldn't kill the run
            print(f"[federal] query {q} failed: {e}")
            continue
        for h in hits:
            oid = str(h.get("id", "")).strip()
            if oid and oid not in by_id:
                by_id[oid] = _normalize(h)
    print(f"[federal] {len(by_id)} unique opportunities")
    return list(by_id.values())
