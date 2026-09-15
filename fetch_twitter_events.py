#!/usr/bin/env python3
"""Fetch recent NYC-event-related tweets via the X API v2 recent-search endpoint.

Same gating as ai-content/fetch_twitter.py: requires a paid API tier for
read/search access, reads the bearer token from the same Keychain entry
(same underlying X account/subscription) since this is just a different set
of search queries against the same API. Gracefully prints nothing if no
bearer token is configured.
"""
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

KEYCHAIN_SERVICE = "ai-content-twitter"
QUERIES = [
    "(NYC OR \"New York\") (event OR pop-up OR popup OR party OR opening) -is:retweet lang:en",
    "(NYC OR \"New York\") (gallery OR exhibit OR mixer OR launch) -is:retweet lang:en",
]
MAX_RESULTS_PER_QUERY = 15


def get_secret(account):
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def search(query, bearer_token):
    params = {
        "query": query,
        "max_results": MAX_RESULTS_PER_QUERY,
        "tweet.fields": "public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username",
    }
    url = f"https://api.twitter.com/2/tweets/search/recent?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer_token}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def main():
    bearer_token = get_secret("bearer_token")
    if not bearer_token:
        print("(X/Twitter API not configured — see SETUP.md. Skipping.)", file=sys.stderr)
        return

    lines = ["## X/Twitter (recent, NYC events)"]
    found = False

    for query in QUERIES:
        data = search(query, bearer_token)
        if not data or "data" not in data:
            continue
        users = {u["id"]: u.get("username", "?") for u in data.get("includes", {}).get("users", [])}
        for tweet in data["data"]:
            text = tweet.get("text", "").replace("\n", " ").strip()
            if not text:
                continue
            username = users.get(tweet.get("author_id"), "?")
            metrics = tweet.get("public_metrics", {})
            likes = metrics.get("like_count", 0)
            tweet_url = f"https://x.com/{username}/status/{tweet['id']}"
            lines.append(f"- [@{username}, {likes} likes] {text} ({tweet_url})")
            found = True

    if found:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
