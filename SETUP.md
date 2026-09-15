# NYC Events Newsletter — Setup

Personal curation for now (not distributed to subscribers) — a weekly list you read to decide what to attend, built from daily candidates you flag via Telegram.

## What runs, and when

1. **`com.minmiller.nycevents.plist`, 8:00am daily** — fetches Luma, Partiful, Time Out NY, a curated set of existing NYC event newsletters, and (if configured) X/Twitter search + your manual drop-in, curates down to 5-7 genuinely good picks for a 20s-30s up-and-coming/sceney taste. Each gets a **category** (💻 tech / 🧘 wellness / 🎨 culture / 🎉 social / 🗝️ side quest) and a **timing** — 🗓️ this week (happening within ~7 days) or 📅 upcoming this month (worth flagging now, ~1-5 weeks out, so it can be planned for) — and the Telegram message is grouped by timing first, then category. Capped in code (not just the prompt): up to 2 upcoming picks are kept in full, remaining slots go to "this week" ones, so upcoming events can't get crowded out by a glut of near-term ones. Reply with any numbers (e.g. `2,4`) to add those events to this week's running list — no per-day approval needed, replying is entirely optional.
2. **`com.minmiller.nycevents.weekly.plist`, Sunday 7:30pm** — compiles the week's flagged events into a clean markdown newsletter draft, structured the same way: a **This Week** section, then a **This Month & Upcoming** section (skipped if empty), each grouped by category with real curator-voice writeups, not just the raw descriptions, via `claude -p`. Sends it to Telegram, saves it to `~/content-log/nyc-events-newsletters/YYYY-Www.md`, and resets the list for the new week.

Both jobs run through the **same shared Telegram bot and poller** as the AI content pipeline and the daily tweet thread (`ai-content/handle_telegram_reply.py`) — one chat for everything, no separate bot to set up. No additional Telegram credentials needed; if that bot is already configured (see `ai-content/SETUP.md`), this works immediately.

## Sources — what's automatic vs. what needs setup

**Already working, no setup needed:**
- `fetch_luma.py` — `luma.com/nyc`'s public discover page embeds clean JSON-LD event data, no auth.
- `fetch_partiful.py` — `partiful.com/explore`'s NYC trending section, embedded in the page's Next.js data, no auth. Coverage is partial by design (only events hosts opted to make publicly visible).
- `fetch_timeout.py` — Time Out New York's RSS feed.
- `fetch_newsletters.py` — a curated list of existing NYC event-curation newsletters (the closest analogs found to "Michelle Fang's SF events list," which is a Twitter thread with no direct NYC equivalent): coolstuff.nyc, The 'Low Down, Hop The Turnstile, Abril Zucchi's NYC tech-week roundup, Andrew Yeung, Nervous Laughter NYC. All via verified-working Substack RSS feeds. Edit `FEEDS` in that file to add more as you find them.

**Optional — paid X API, same pattern as the AI news pipeline:**
- `fetch_twitter_events.py` reads the same Keychain bearer token as `ai-content/fetch_twitter.py` (`ai-content-twitter` service) — if you've already set that up, this works too, just with event-focused search queries instead of AI-news ones. If not configured, it gracefully skips (see `ai-content/SETUP.md` for setup steps — same cost caveat applies).

**Always available — manual drop-in:**
- `manual_inbox.md` — paste anything you personally spot from any source (a friend's text, an Instagram post, a brand email) — not Twitter-specific. Gets folded into the next digest, then archived to `manual_inbox_archive.md` and cleared.

## Day to day

- Reply to the morning digest whenever — no time pressure, replying is optional (unflagged events just don't make the newsletter, nothing to clean up).
- Drop things into `manual_inbox.md` anytime.
- Run the morning step manually instead of waiting for 8am: `bash ~/dev/nyc-events/run_daily.sh`
- Run the weekly compile manually: `bash ~/dev/nyc-events/run_weekly.sh`
- Check what's flagged so far this week: `cat ~/dev/nyc-events/state/weekly_list.json`
- Change run times: edit `Hour`/`Minute` (or `Weekday`) in the relevant `.plist`, then `launchctl unload`/`launchctl load` it.
- Stop entirely: `launchctl unload ~/Library/LaunchAgents/com.minmiller.nycevents.plist` and the `.weekly.plist` one.

## Curation quality — expect a feedback round

The persona/taste prompt in `generate_digest.py`'s `build_digest_prompt()` is a first pass, not tuned yet — same situation the daily tweet thread was in before several rounds of real feedback. Check the first several days of real output against your actual taste and give feedback (the same way tone got tuned elsewhere in this system) before trusting it to run unattended for a while.

## How dedup works

`seen_events.py` (adapted directly from `ai-content/seen_topics.py`) tracks every event ever shown by URL/title, and the digest prompt is told to judge by the underlying event, not exact text match, so the same event doesn't resurface under a different newsletter's wording or a follow-up post. Same mechanism, same reasoning, as the AI news pipeline's dedup — see `ai-content/SETUP.md`'s "don't repeat a story already shown" section for the full explanation of why exact-match alone doesn't work.

## Known limitation: 3-way Telegram routing

The shared poller now routes between three flows (AI news, daily tweet thread, NYC events) using "whichever was most recently active wins" plus a 20-hour staleness expiry per flow — extended directly from the 2-flow version already in use. This hasn't caused a problem with 2 flows; a third increases the chance of a genuinely ambiguous reply (e.g. a bare number that could plausibly mean either an AI news topic pick or an NYC event flag, if both digests are outstanding at once) getting routed to the wrong one. Not solved preemptively — revisit if it actually happens.

## Changelog

- Added 2026-09-14: **this week / this month & upcoming split**, both in the daily digest and the compiled weekly newsletter. Each event gets a `timing` tag (soon/upcoming) alongside its category — the prompt aims for ~4-5 "soon" + 1-2 genuinely good "upcoming" picks per day, and the code-level cap reserves up to 2 upcoming slots so they can't get crowded out. Hit the same code-fence-wrapping bug seen elsewhere in this system (the newsletter prompt's own header instructions leaked verbatim into the output the first time — "## This Week — events tagged 'soon'" showed up literally) — fixed by separating the exact-header instruction from the explanatory parenthetical.
