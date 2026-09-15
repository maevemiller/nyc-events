#!/usr/bin/env python3
"""Fetch recent posts from existing NYC event-curation newsletters — the
same idea as following a known curator (e.g. Michelle Fang's SF events
thread on Twitter, which has no NYC equivalent as a Twitter thread), but via
Substack RSS feeds, which are actually fetchable. Each of these already
does taste-filtering for a similar audience, so they're higher-signal raw
material than a generic events aggregator.

All feed URLs below were verified working (real XML, real recent content)
before adding — edit FEEDS to add/remove sources as you find better ones.
"""
import datetime

import feedparser

LOOKBACK_HOURS = 9 * 24  # these publish weekly-ish, so a wider window than daily news sources
MAX_PER_FEED = 6

FEEDS = [
    {"name": "coolstuff.nyc", "url": "https://coolstuffnyc.substack.com/feed"},
    {"name": "The 'Low Down", "url": "https://thelowdownnyc.substack.com/feed"},
    {"name": "Hop The Turnstile", "url": "https://hoptheturnstile.substack.com/feed"},
    {"name": "Abril Zucchi (NYC tech this week)", "url": "https://abruzucchi.substack.com/feed"},
    {"name": "Andrew Yeung", "url": "https://www.andrew.today/feed"},
    {"name": "Nervous Laughter NYC", "url": "https://sarahsuzukiharvard.substack.com/feed"},
]


def entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if value:
            return datetime.datetime(*value[:6], tzinfo=datetime.timezone.utc)
    return None


def fetch_feed(feed_def):
    try:
        parsed = feedparser.parse(feed_def["url"])
    except Exception:
        return []

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=LOOKBACK_HOURS)
    items = []
    for entry in parsed.entries[: MAX_PER_FEED * 3]:
        dt = entry_datetime(entry)
        if dt and dt < cutoff:
            continue
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        summary = (entry.get("summary", "") or "")[:500]
        items.append({"title": title, "summary": summary, "url": entry.get("link", "")})
        if len(items) >= MAX_PER_FEED:
            break
    return items


def main():
    sections = []
    for feed_def in FEEDS:
        items = fetch_feed(feed_def)
        if not items:
            continue
        lines = [f"## {feed_def['name']} (curated NYC newsletter)"]
        for item in items:
            lines.append(f"- {item['title']} ({item['url']})")
            if item["summary"]:
                lines.append(f"  {item['summary']}")
        sections.append("\n".join(lines))

    if sections:
        print("\n\n".join(sections))


if __name__ == "__main__":
    main()
