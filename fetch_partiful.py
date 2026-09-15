#!/usr/bin/env python3
"""Fetch NYC events from Partiful's public explore page (partiful.com/explore).

No auth needed — the page embeds its Next.js hydration data (__NEXT_DATA__)
with a "NYC" trending section we read directly. Coverage is partial by
design (only events hosts opted to make publicly visible); private
invite-only events aren't discoverable here — that gap is what the manual
inbox is for.
"""
import json
import re
import urllib.error
import urllib.request

URL = "https://partiful.com/explore"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.DOTALL
)


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return []

    m = NEXT_DATA_RE.search(html)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    nyc = data.get("props", {}).get("pageProps", {}).get("trendingSections", {}).get("NYC", {})
    events = []
    for item in nyc.get("items", []):
        event = item.get("event")
        if not event:
            continue
        title = (event.get("title") or "").strip()
        if not title:
            continue
        location = (event.get("locationInfo") or {}).get("approximateLocation", "New York, NY")
        events.append(
            {
                "title": title,
                "url": f"https://partiful.com/e/{event['id']}",
                "start": event.get("startDate", ""),
                "location": location,
                "interested": event.get("interestedGuestCount", 0),
            }
        )
    return events


def main():
    events = fetch()
    if not events:
        return
    lines = ["## Partiful (partiful.com/explore, NYC)"]
    for e in events:
        lines.append(
            f"- {e['title']} @ {e['location']}, {e['start']} "
            f"({e['interested']} interested) ({e['url']})"
        )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
