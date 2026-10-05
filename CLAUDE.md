# Repo rules for Claude

live-feeds holds small data feeds that scrape public sources on a schedule and
push the result to vibeplat apps (owner-data), plus each feed's web app.

## Layout
- `lib/vibefeed/` is shared by every feed: HTTP session, parse helpers, state files, vibeplat client, push with limit checks.
- `feeds/<name>/` is self-contained: `feed.toml`, `run.py`, the source adapters, committed `state/`, `app/` (the vibeplat web app) and `listing/`.
- `.github/workflows/_run-feed.yml` holds the shared CI steps. Each feed has a ~10-line caller workflow with its own schedule.

## Scoping
- Work inside one `feeds/<name>/` at a time. Don't copy another feed's UI or style into a new one.
- Changes to `lib/` or `_run-feed.yml` affect every feed, so check that each feed still runs (`--dry-run`).

## Rules
- This repo is public. Never commit tokens. CI reads `VIBEPLAT_TOKEN_<ACCOUNT>` repo secrets; local runs read `~/code/mini-games-hub/.vibeplat-tokens.json`.
- Owner-data is public and limited to 256 KB per key, 32 keys and 1 MB per app. `push_keys` enforces this, so keep payloads compact.
- Be polite to sources: fetch only what the feed's window needs, at most hourly.
- Vanilla HTML/CSS/JS for apps, with no build step. They must work at phone width.
- Git: branch off `main`, fast-forward merge, push. English commit messages.
