#!/usr/bin/env python3
"""Fetch NYC events from Luma's public discover page (luma.com/nyc).

No auth needed — the page embeds a clean JSON-LD ItemList of events (name,
url, date, location, organizer) that schema.org-aware crawlers use; we just
read the same block directly.
"""
import json
import re
import urllib.error
import urllib.request

URL = "https://luma.com/nyc"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
LD_JSON_RE = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return []

    events = []
    for block in LD_JSON_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "ItemList":
            continue
        for item in data.get("itemListElement", []):
            event = item.get("item", {})
            if event.get("@type") != "Event":
                continue
            name = event.get("name", "").strip()
            if not name:
                continue
            location = (event.get("location") or {}).get("name", "New York")
            organizer_list = event.get("organizer") or []
            organizer = organizer_list[0].get("name", "") if organizer_list else ""
            events.append(
                {
                    "name": name,
                    "url": event.get("url", ""),
                    "start": event.get("startDate", ""),
                    "location": location,
                    "organizer": organizer,
                }
            )
    return events


def main():
    events = fetch()
    if not events:
        return
    lines = ["## Luma (luma.com/nyc)"]
    for e in events:
        organizer_part = f" — hosted by {e['organizer']}" if e["organizer"] else ""
        lines.append(f"- {e['name']} @ {e['location']}, {e['start']}{organizer_part} ({e['url']})")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
