#!/usr/bin/env python3
"""Daily step: fetch NYC event sources, curate for a 20s-30s up-and-coming/
sceney taste, send a short numbered candidate list to Telegram. Replying with
numbers adds those events to the running weekly list (see
nyc_events_review.py) — no per-day approval step, the weekly compile is the
finalize step.
"""
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).parent
sys.path.insert(0, str(Path.home() / "dev" / "ai-content"))
import telegram_lib  # noqa: E402

import seen_events
STATE_FILE = DIR / "state" / "digest_state.json"
DIGESTS_DIR = Path.home() / "content-log" / "nyc-events-digests"

EVENT_LINE_RE = re.compile(
    r"^\s*(\d+)\.\s*\[(soon|upcoming)/(tech|wellness|culture|social|sidequest)/([^\]/]+)\]\s*(.+?)\s*—\s*(.+?)(?:\s*\((https?://[^\s)]+)\))?\s*$"
)

FETCHERS = ["fetch_luma.py", "fetch_partiful.py", "fetch_timeout.py", "fetch_newsletters.py", "fetch_twitter_events.py"]
MAX_TOTAL = 7


def fetch_sources():
    sections = []
    for fetcher in FETCHERS:
        output = subprocess.run(["python3", str(DIR / fetcher)], capture_output=True, text=True).stdout
        if output.strip():
            sections.append(output.strip())

    inbox_output = subprocess.run(["python3", str(DIR / "inbox.py")], capture_output=True, text=True).stdout
    if inbox_output.strip():
        sections.append(inbox_output.strip())

    return "\n\n".join(sections)


def build_digest_prompt(already_shown):
    already_shown_block = ""
    if already_shown:
        titles = "\n".join(f"- {entry['title']}" for entry in already_shown if entry.get("title"))
        already_shown_block = (
            "Already shown in a previous digest — do NOT include these EVENTS again, even if "
            "the same event shows up again in the material below under different wording or a "
            "different source (judge by the actual event, not exact text match). Pick something "
            "genuinely different instead:\n"
            f"{titles}\n\n"
        )

    return (
        f"{already_shown_block}"
        "Below is today's raw material about NYC events/happenings from several sources (each "
        "under its own '## ' header) — Luma, Partiful, Time Out New York, possibly Twitter and "
        "manually-spotted items.\n\n"
        "AUDIENCE: curate for someone in their 20s-30s, up-and-coming, plugged into NYC's "
        "tech/startup and culture scene — 'sceney' in a discerning way, not mainstream tourist "
        "stuff. Think: a founder mixer at a cool venue, a gallery opening with an interesting "
        "crowd, a well-produced wellness event, a talk by someone actually worth hearing, a "
        "genuinely fun party, or a fun/unique 'side quest' — a weird one-off NYC experience "
        "(a stein-holding competition, pigeon embroidery class, an odd scavenger hunt, something "
        "you'd only find in this city) — not a random meetup, not a big-box tourist attraction, "
        "not something with zero social/cultural cachet. Some of the raw material below comes "
        "from newsletters/curators who already do this kind of taste-filtering (coolstuff.nyc, "
        "The 'Low Down, Hop The Turnstile, etc.) — their picks are generally higher-signal, but "
        "still apply your own judgment, don't just rubber-stamp everything they list. Be a real "
        "curator with actual taste, not a generic events aggregator — most of what's in the raw "
        "material below should probably be REJECTED. Only pick things that would make someone "
        "say 'oh that's actually cool.'\n\n"
        "Be SELECTIVE — produce only 5-7 events total, this is a tight shortlist not a roundup. "
        "Tag each with a category: tech (talks, mixers, launches, startup events), wellness "
        "(fitness, health, mindfulness), culture (galleries, lectures, clubs, arts), social "
        "(parties, pop-ups, nightlife), sidequest (quirky one-off NYC experiences that don't fit "
        "the other categories). Try for some spread across categories if the material supports "
        "it, but don't force a weak pick just for category balance.\n\n"
        "ALSO tag each with a timing: soon (happening within about the next 7 days) or upcoming "
        "(happening later this month, roughly 1-5 weeks out — something worth flagging NOW so it "
        "can be planned for/tickets grabbed, even though it's not imminent). Most of the raw "
        "material skews near-term, so most picks will naturally be 'soon' — aim for around 4-5 "
        "soon and 1-2 genuinely good upcoming picks if the material supports it. Don't force an "
        "upcoming pick if nothing later in the month is actually good.\n\n"
        "Output STRICTLY as one line per item, in exactly this format, nothing else — ONE "
        "bracket group with timing, category, and source separated by slashes:\n"
        "N. [soon/tech/Luma] Event name — one-line description with date/venue (url)\n"
        "or\n"
        "N. [upcoming/social/Partiful] Event name — one-line description with date/venue (url)\n"
        "(timing is soon or upcoming; category is tech, wellness, culture, social, or sidequest; "
        "source name must not contain a '/' character; always include the url in parens if "
        "available; include the date/venue naturally in the description since there's no "
        "separate field for it)\n\n"
        "No preamble, no headers, no extra commentary — just the numbered lines."
    )


def parse_events(digest_text, start_number):
    events = []
    number = start_number
    for line in digest_text.splitlines():
        m = EVENT_LINE_RE.match(line)
        if not m:
            continue
        _orig_number, timing, category, source, title, description, url = m.groups()
        events.append(
            {
                "number": number,
                "timing": timing,
                "category": category,
                "source": source.strip(),
                "title": title.strip(),
                "description": description.strip(),
                "url": url or "",
            }
        )
        number += 1
    return events


def format_event_line(event):
    url_part = f" ({event['url']})" if event.get("url") else ""
    return f"{event['number']}. [{event['source']}] {event['title']} — {event['description']}{url_part}"


CATEGORY_LABELS = {
    "tech": "💻 TECH",
    "wellness": "🧘 WELLNESS",
    "culture": "🎨 CULTURE",
    "social": "🎉 SOCIAL",
    "sidequest": "🗝️ SIDE QUEST",
}
CATEGORY_ORDER = list(CATEGORY_LABELS)

TIMING_LABELS = {
    "soon": "🗓️ THIS WEEK",
    "upcoming": "📅 UPCOMING THIS MONTH",
}
TIMING_ORDER = list(TIMING_LABELS)


def format_grouped_digest(events):
    # Group by timing first (this week vs. upcoming), then category within
    # each, so the daily view previews the same split the weekly newsletter
    # uses — you see at a glance which picks are "act now" vs. "plan ahead."
    by_timing = {}
    for e in events:
        by_timing.setdefault(e["timing"], []).append(e)

    sections = []
    for timing in TIMING_ORDER:
        timing_events = by_timing.get(timing)
        if not timing_events:
            continue
        by_category = {}
        for e in timing_events:
            by_category.setdefault(e["category"], []).append(e)
        category_lines = []
        for cat in CATEGORY_ORDER:
            items = by_category.get(cat)
            if items:
                category_lines.append(
                    f"{CATEGORY_LABELS[cat]}\n" + "\n".join(format_event_line(e) for e in items)
                )
        sections.append(f"{TIMING_LABELS[timing]}\n\n" + "\n\n".join(category_lines))
    return "\n\n".join(sections)


def main():
    date = datetime.date.today().strftime("%Y-%m-%d")
    already_shown = seen_events.load()

    source_text = fetch_sources()

    events = []
    generation_failed = False
    if len(source_text.strip()) >= 20:
        prompt = build_digest_prompt(already_shown)
        result = subprocess.run(
            [
                "claude", "-p", "--no-session-persistence",
                "--disallowedTools", "Write", "Edit", "Bash", "NotebookEdit", "Agent", "WebFetch", "WebSearch",
                "--", prompt,
            ],
            input=source_text,
            capture_output=True,
            text=True,
        )
        digest_text = result.stdout.strip()
        events = parse_events(digest_text, start_number=1)
        parsed_count = len(events)

        seen_keys = seen_events.seen_keys_set()
        events = [e for e in events if not seen_events.is_seen(e, seen_keys)]

        if parsed_count == 0:
            generation_failed = True
            print(
                f"Digest generation returned no parseable events despite "
                f"{len(source_text)} chars of source material. "
                f"returncode={result.returncode}, stderr={result.stderr.strip()[-500:]}, "
                f"raw stdout={digest_text[:1000]!r}",
                file=sys.stderr,
            )

    # Cap in code, not just via the prompt (same lesson as the AI news
    # pipeline) — but reserve room for "upcoming" picks rather than letting
    # a glut of "soon" events crowd them out entirely.
    category_index = {cat: i for i, cat in enumerate(CATEGORY_ORDER)}
    soon = sorted((e for e in events if e["timing"] == "soon"), key=lambda e: category_index.get(e["category"], 99))
    upcoming = sorted((e for e in events if e["timing"] == "upcoming"), key=lambda e: category_index.get(e["category"], 99))
    upcoming = upcoming[:2]
    soon = soon[: max(0, MAX_TOTAL - len(upcoming))]
    events = soon + upcoming

    # Number in display order (this week first, then upcoming; category
    # order within each) so numbers read top-to-bottom, not construction order.
    timing_index = {t: i for i, t in enumerate(TIMING_ORDER)}
    events = sorted(events, key=lambda e: (timing_index.get(e["timing"], 9), category_index.get(e["category"], 99)))
    for i, e in enumerate(events, start=1):
        e["number"] = i

    if not events:
        if generation_failed:
            telegram_lib.send_message(
                "⚠️ Today's NYC events digest generation failed — check nyc-events run logs."
            )
        else:
            print("No events available today.", file=sys.stderr)
        return

    seen_events.record(events)

    digest_text_full = format_grouped_digest(events)

    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    (DIGESTS_DIR / f"{date}.md").write_text(digest_text_full + "\n")

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "date": date,
        "events": events,
        "updated_at": datetime.datetime.now().isoformat(),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))

    warning = (
        "⚠️ Fresh generation failed today — showing whatever could be recovered.\n\n"
        if generation_failed
        else ""
    )
    message = "\n".join(
        [
            f"NYC events — {date}",
            "",
            warning + digest_text_full,
            "",
            "Reply with numbers (e.g. '2,4') to add those to this week's list. No reply needed if nothing fits.",
        ]
    )

    telegram_lib.send_message(message)
    print(f"NYC events digest sent to Telegram, {len(events)} events.")


if __name__ == "__main__":
    main()
