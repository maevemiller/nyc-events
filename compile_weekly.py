#!/usr/bin/env python3
"""Weekly step: compile the events flagged over the past week
(state/weekly_list.json) into a clean, grouped newsletter draft, send it to
Telegram for final review, then reset the list for the new week.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).parent
sys.path.insert(0, str(Path.home() / "dev" / "ai-content"))
import telegram_lib  # noqa: E402

import nyc_events_review

NEWSLETTER_DIR = Path.home() / "content-log" / "nyc-events-newsletters"


def build_prompt(events_text):
    return (
        "Here are the NYC events flagged this week for a personal weekly newsletter, aimed at a "
        "20s-30s up-and-coming, sceney, tech-adjacent NYC audience. Each is tagged with a timing "
        "(soon = this week, upcoming = later this month) and a category:\n\n"
        f"{events_text}\n\n"
        "Format this into a clean, readable weekly newsletter draft in markdown, structured as "
        "TWO top-level sections in this order (use these exact headers, nothing appended to them):\n"
        "## This Week\n"
        "(events tagged 'soon' go here)\n"
        "## This Month & Upcoming\n"
        "(events tagged 'upcoming' go here — skip this whole section, header included, if there "
        "are none)\n\n"
        "Within each section, group by category with a short, punchy one-line writeup for each "
        "event (not just repeating the raw description verbatim — make it read like a real "
        "curator wrote it, with personality). Include the date/venue detail and the link for "
        "each. Add a brief, casual intro line at the very top (1-2 sentences, no corporate "
        "newsletter tone, no 'Hey everyone!' greeting) before the two sections. "
        "No em dashes, no AI-sounding filler ('it's worth noting', 'game-changer', etc). Output "
        "ONLY the raw markdown newsletter as plain text — no code fence wrapper (no ``` at the "
        "start or end), no preamble, no commentary."
    )


def main():
    events = nyc_events_review.load_weekly_list()
    if not events:
        telegram_lib.send_message("No events flagged this week — skipping the weekly newsletter compile.")
        return

    events_text = "\n\n".join(
        f"[{e.get('timing', 'soon')}/{e.get('category', '?')}] {e['title']} — "
        f"{e.get('description', '')} ({e.get('url', '')})"
        for e in events
    )

    prompt = build_prompt(events_text)
    result = subprocess.run(
        [
            "claude", "-p", "--no-session-persistence",
            "--disallowedTools", "Write", "Edit", "Bash", "NotebookEdit", "Agent", "WebFetch", "WebSearch",
            "--", prompt,
        ],
        capture_output=True,
        text=True,
    )
    draft = result.stdout.strip()

    if not draft:
        telegram_lib.send_message(
            f"⚠️ Weekly newsletter compile failed — check logs. {len(events)} events are still saved "
            f"in weekly_list.json, nothing lost."
        )
        print(f"compile_weekly.py failed: returncode={result.returncode}, stderr={result.stderr[-500:]}", file=sys.stderr)
        return

    week_label = datetime.date.today().strftime("%Y-W%V")
    NEWSLETTER_DIR.mkdir(parents=True, exist_ok=True)
    draft_path = NEWSLETTER_DIR / f"{week_label}.md"
    draft_path.write_text(draft + "\n")

    telegram_lib.send_message(f"This week's NYC events newsletter draft ({len(events)} events):\n\n{draft}")

    # Reset for the new week now that it's compiled — events are preserved
    # in the dated draft file above, so nothing is actually lost by clearing this.
    nyc_events_review.save_weekly_list([])

    print(f"Weekly newsletter compiled to {draft_path}, {len(events)} events, list reset.")


if __name__ == "__main__":
    main()
