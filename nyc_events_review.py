"""Telegram reply handler for the NYC events digest — reply with numbers to
add those events to this week's running list (state/weekly_list.json). No
per-day approval/finalize cycle; the weekly compile (run_weekly.sh) is the
finalize step. Mirrors learning-tweet/thread_review.py's shape so the shared
poller in ai-content/handle_telegram_reply.py can route to it the same way.
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "dev" / "ai-content"))
import telegram_lib  # noqa: E402

DIR = Path(__file__).parent
DIGEST_STATE_FILE = DIR / "state" / "digest_state.json"
WEEKLY_LIST_FILE = DIR / "state" / "weekly_list.json"

STALE_AFTER = datetime.timedelta(hours=20)
NUMBER_LIST_RE = re.compile(r"\d+")


def load_digest_state():
    if not DIGEST_STATE_FILE.exists():
        return None
    return json.loads(DIGEST_STATE_FILE.read_text())


def is_awaiting(state):
    """A digest older than STALE_AFTER stops being eligible for routing —
    matches the same staleness pattern used for the news/thread flows, so
    an unanswered digest from a previous day doesn't hijack a later reply."""
    if not state:
        return False
    updated_at = state.get("updated_at")
    if not updated_at:
        return True
    age = datetime.datetime.now() - datetime.datetime.fromisoformat(updated_at)
    return age < STALE_AFTER


def load_weekly_list():
    if not WEEKLY_LIST_FILE.exists():
        return []
    return json.loads(WEEKLY_LIST_FILE.read_text())


def save_weekly_list(events):
    WEEKLY_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    WEEKLY_LIST_FILE.write_text(json.dumps(events, indent=2))


def handle_reply(state, message):
    numbers = [int(n) for n in NUMBER_LIST_RE.findall(message)]
    by_number = {e["number"]: e for e in state.get("events", [])}
    valid = [by_number[n] for n in numbers if n in by_number]

    if not valid:
        telegram_lib.send_message(
            f"Didn't recognize any of those numbers from today's list (1-{len(by_number)})."
        )
        state["updated_at"] = datetime.datetime.now().isoformat()
        return state

    weekly = load_weekly_list()
    existing_urls = {e.get("url") for e in weekly if e.get("url")}
    added = 0
    for e in valid:
        if e.get("url") and e["url"] in existing_urls:
            continue
        weekly.append(e)
        existing_urls.add(e.get("url"))
        added += 1
    save_weekly_list(weekly)

    telegram_lib.send_message(f"Added {added} event(s) to this week's list ({len(weekly)} total so far).")
    state["updated_at"] = datetime.datetime.now().isoformat()
    return state


def save_state(state):
    """No-op placeholder for router symmetry with the other flows — digest
    state is written by generate_digest.py, not mutated here beyond
    updated_at (used only for staleness, harmless if not persisted)."""
    DIGEST_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_STATE_FILE.write_text(json.dumps(state, indent=2))
