"""Tracks events (by URL) that have already appeared in a past digest, so the
same event doesn't get re-surfaced day after day just because it's still
showing up in the raw fetched material. Adapted directly from
ai-content/seen_topics.py — same mechanism, different domain.
"""
import json
from pathlib import Path

SEEN_FILE = Path(__file__).parent / "state" / "seen_events.json"
MAX_STORED = 300  # plenty of runway; a JSON list of URLs is tiny


def load():
    if not SEEN_FILE.exists():
        return []
    return json.loads(SEEN_FILE.read_text())


def record(events):
    """Add these events' URLs (and titles, for url-less items) to the seen
    list, keeping only the most recent MAX_STORED entries."""
    seen = load()
    existing = {entry["key"] for entry in seen}
    for e in events:
        key = e.get("url") or e.get("title", "")
        if key and key not in existing:
            seen.append({"key": key, "title": e.get("title", "")})
            existing.add(key)
    seen = seen[-MAX_STORED:]
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))


def is_seen(event, seen_keys):
    key = event.get("url") or event.get("title", "")
    return bool(key) and key in seen_keys


def seen_keys_set():
    return {entry["key"] for entry in load()}
