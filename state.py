"""Tracks which opportunities have been seen, so the report can flag what's new.

State is a single JSON file (data/seen.json) committed back to the repo each run.
Shape: {"seen": {"<uid>": "<first-seen ISO date>"}}
"""
import json
import os
from datetime import date

STATE_PATH = os.path.join("data", "seen.json")


def load():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"seen": {}}


def save(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)


def mark_and_get_new(state, items):
    """Given current items, return the set of uids that are new (never seen),
    then record all current uids as seen. Mutates `state` in place."""
    seen = state.setdefault("seen", {})
    today = date.today().isoformat()
    new_uids = set()
    for it in items:
        uid = it["uid"]
        if uid not in seen:
            new_uids.add(uid)
            seen[uid] = today
    return new_uids
