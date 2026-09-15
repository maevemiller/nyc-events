#!/usr/bin/env python3
"""Fetch recent NYC event/things-to-do posts from Time Out New York's RSS feed."""
import datetime

import feedparser

FEED_URL = "https://www.timeout.com/newyork/blog/feed.rss"
LOOKBACK_HOURS = 7 * 24
MAX_ITEMS = 15


def entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed"):
        value = entry.get(field)
        if value:
            return datetime.datetime(*value[:6], tzinfo=datetime.timezone.utc)
    return None


def fetch():
    try:
        parsed = feedparser.parse(FEED_URL)
    except Exception:
        return []

    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=LOOKBACK_HOURS)
    items = []
    for entry in parsed.entries[: MAX_ITEMS * 2]:
        dt = entry_datetime(entry)
        if dt and dt < cutoff:
            continue
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        summary = (entry.get("summary", "") or "")[:300]
        items.append({"title": title, "summary": summary, "url": entry.get("link", "")})
        if len(items) >= MAX_ITEMS:
            break
    return items


def main():
    items = fetch()
    if not items:
        return
    lines = ["## Time Out New York (RSS)"]
    for i in items:
        lines.append(f"- {i['title']} ({i['url']})")
        if i["summary"]:
            lines.append(f"  {i['summary']}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
