"""Entry point. Fetches all sources, flags what's new, writes docs/index.html.

  python run.py          # real run (hits Grants.gov + your RSS feeds)
  python run.py --demo   # render a sample dashboard with fake data, no network
"""
import argparse
import datetime
import os
import sys
import zoneinfo

import yaml

import report
import state
from sources import federal, foundations


def load_config(path="config.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def now_in(tz_name):
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        tz = datetime.timezone.utc
    return datetime.datetime.now(tz)


def gather(cfg):
    keywords = cfg.get("keywords", [])
    gg = cfg.get("grants_gov", {})
    items = federal.fetch(
        keywords,
        funding_categories=gg.get("funding_categories", "EN"),
        statuses=gg.get("statuses", "posted|forecasted"),
        max_per_query=gg.get("max_per_query", 300),
        max_details=gg.get("max_details", 200),
    )
    items += foundations.fetch(cfg.get("foundation_feeds", []), keywords)
    return items


def demo_items(today):
    d = datetime.timedelta
    mk = lambda **k: k
    return [
        mk(uid="grants_gov:demo1", source="Grants.gov", source_key="federal",
           title="Advancing Long-Duration Grid-Scale Energy Storage Systems",
           agency="Department of Energy", number="DE-FOA-0003412", status="posted",
           open_date=today - d(days=1), close_date=today + d(days=2),
           award_ceiling=5_000_000, award_floor=1_000_000,
           matched_keywords=["energy storage", "grid"], url="https://grants.gov"),
        mk(uid="grants_gov:demo2", source="Grants.gov", source_key="federal",
           title="Enhanced Geothermal Systems Demonstration Program",
           agency="DOE · Geothermal Technologies Office", number="DE-FOA-0003388",
           status="posted", open_date=today - d(days=6), close_date=today + d(days=11),
           award_ceiling=12_000_000, award_floor=None,
           matched_keywords=["geothermal"], url="https://grants.gov"),
        mk(uid="grants_gov:demo3", source="Grants.gov", source_key="federal",
           title="Clean Hydrogen Electrolysis and Manufacturing R&D",
           agency="DOE · Hydrogen and Fuel Cell Technologies", number="DE-FOA-0003251",
           status="posted", open_date=today - d(days=20), close_date=today + d(days=47),
           award_ceiling=3_500_000, award_floor=500_000,
           matched_keywords=["hydrogen", "clean energy"], url="https://grants.gov"),
        mk(uid="grants_gov:demo4", source="Grants.gov", source_key="federal",
           title="Critical Materials Innovation for Energy Technologies",
           agency="ARPA-E", number="DE-FOA-0003500", status="forecasted",
           open_date=None, close_date=None, award_ceiling=2_000_000, award_floor=None,
           matched_keywords=["critical materials"], url="https://grants.gov"),
        mk(uid="grants_gov:demo5", source="Grants.gov", source_key="federal",
           title="Power Electronics for Next-Generation Grid Resilience",
           agency="National Science Foundation", number="NSF-25-512", status="posted",
           open_date=today - d(days=3), close_date=today + d(days=78),
           award_ceiling=750_000, award_floor=None,
           matched_keywords=["power electronics", "grid"], url="https://grants.gov"),
        mk(uid="foundation:demo:1", source="Example Energy Fund",
           source_key="foundation", title="Community Solar Access Innovation Grants",
           agency="Example Energy Fund", number="", status="open",
           open_date=today - d(days=2), close_date=None,
           award_ceiling=None, award_floor=None,
           matched_keywords=["solar"], url="https://example.org"),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="render sample data, no network")
    args = ap.parse_args()

    cfg = load_config()
    generated_at = now_in(cfg.get("report", {}).get("owner_timezone", "UTC"))

    if args.demo:
        items = demo_items(generated_at.date())
        st = {"seen": {}}  # everything counts as new in the demo
    else:
        items = gather(cfg)
        st = state.load()

    new_uids = state.mark_and_get_new(st, items)

    html = report.build(items, cfg, generated_at, new_uids)
    os.makedirs("docs", exist_ok=True)
    with open(os.path.join("docs", "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    if not args.demo:
        state.save(st)

    print(f"Wrote docs/index.html — {len(items)} opportunities, {len(new_uids)} new")


if __name__ == "__main__":
    sys.exit(main())
