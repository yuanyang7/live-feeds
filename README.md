# live-feeds

Scheduled scrapers that push public data to [vibeplat](https://vibeplat.ai) apps through
owner-data (app-wide JSON every viewer can read with `window.vibe.ownerData`). Each feed
lives in its own folder with its scraper, its committed state and the web app that displays it.

| Feed | App | Schedule | Sources |
|---|---|---|---|
| [warn](feeds/warn) | [WARN Watch](https://vibeplat.ai/apps/warn-watch-v899yx) | every 3 hours | CA, NY, WA, NJ WARN notice lists |

## How a feed works

```
a timer (see below) ──▶ feeds/<name>/run.py ─▶ fetch + parse sources
                                             ─▶ merge into state/ (rolling window, first-seen times)
                                             ─▶ PUT owner-data keys that changed ─▶ vibeplat CDN ─▶ app polls
                         commit state/ back to the repo
```

- **State in git.** `state/` keeps a rolling window of records with the time each was first
  seen, so the app can badge new items and records survive sources that reset (California's
  spreadsheet restarts every July 1).
- **Only changed keys are pushed.** Hashes live in `state/pushed.json`; `meta` (with
  `checkedAt` and per-key hashes) is pushed every run so the app knows what to refetch.
- **One broken source doesn't break the rest.** It's reported in `meta` (the app shows it),
  the run exits non-zero, and the other sources still update.

## Local use

```sh
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python feeds/warn/run.py --dry-run            # scrape only; writes feeds/warn/app/dev-data/
cd feeds/warn/app && python3 -m http.server   # the app reads dev-data/ when not on vibeplat
python feeds/warn/run.py                      # scrape + push (needs the account's token)
python scripts/publish_app.py warn [--listing] # upload a new build of the web app
```

Tokens: CI uses the repo secret `VIBEPLAT_TOKEN_<ACCOUNT>` (e.g. `VIBEPLAT_TOKEN_ALEX`).
Locally, `$VIBEPLAT_TOKEN` or `~/code/mini-games-hub/.vibeplat-tokens.json`.

## Local timer (macOS)

GitHub's scheduled runs start late and sometimes don't run at all, so the feed is
driven from this machine instead (`.github/workflows/<name>.yml` keeps only
`workflow_dispatch`, for manual runs):

```sh
scripts/install-local-timer.sh warn        # launchd agent, :47 past every hour
tail -f ~/Library/Logs/live-feeds-warn.log
launchctl bootout gui/$(id -u)/com.live-feeds.warn   # remove it
```

The agent wakes every hour, but `scripts/local_timer.py` reads `meta.checkedAt` from
vibeplat first and does nothing unless the feed is overdue by its own `check_every_hours`.
So the sources see one fetch per `check_every_hours`, and an hour is just how quickly the
feed recovers after the laptop has been asleep or offline. It commits and pushes state the
way a CI run would; if that races with one, the state commit is dropped and the next run
rebuilds it from origin.

With nothing running in the cloud, a laptop that stays shut means a stale feed: the app
says so (`meta.checkedAt` drives its "updates may be delayed" line), but nothing emails
you. `gh workflow run warn.yml` still runs the feed on Actions when that matters.

## Adding a feed

1. Create `feeds/<name>/` with `feed.toml` (`slug`, `account`), `run.py`, `app/` and `listing/listing.json`.
   Use `lib/vibefeed` for HTTP, parsing and pushing.
2. Add `.github/workflows/<name>.yml` that calls `_run-feed.yml` with `feed` and `account`.
3. Add the account's token as a repo secret if it's a new account.
4. Run `python scripts/publish_app.py <name> --listing` once to create the vibeplat app, then run the feed.

WARN parsing approach credit: Big Local News' [warn-scraper](https://github.com/biglocalnews/warn-scraper).
