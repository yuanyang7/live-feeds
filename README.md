# live-feeds

Scheduled scrapers that push public data to [vibeplat](https://vibeplat.ai) apps through
owner-data (app-wide JSON every viewer can read with `window.vibe.ownerData`). Each feed
lives in its own folder with its scraper, its committed state and the web app that displays it.

| Feed | App | Schedule | Sources |
|---|---|---|---|
| [warn](feeds/warn) | [WARN Watch](https://vibeplat.ai/apps/warn-watch-v899yx) | every 3 hours | CA, NY, WA, NJ WARN notice lists |

## How a feed works

```
GitHub Actions (cron) ─▶ feeds/<name>/run.py ─▶ fetch + parse sources
                                             ─▶ merge into state/ (rolling window, first-seen times)
                                             ─▶ PUT owner-data keys that changed ─▶ vibeplat CDN ─▶ app polls
                         commit state/ back to the repo
```

- **State in git.** `state/` keeps a rolling window of records with the time each was first
  seen, so the app can badge new items and records survive sources that reset (California's
  spreadsheet restarts every July 1).
- **Only changed keys are pushed.** Hashes live in `state/pushed.json`; `meta` (with
  `checkedAt` and per-key hashes) is pushed every run so the app knows what to refetch.
- **One broken source doesn't break the rest.** It's reported in `meta`, the run exits non-zero
  (GitHub emails you), and the other sources still update.

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

GitHub's scheduled runs start late and sometimes don't run at all, so this machine
can fill the gaps:

```sh
scripts/install-local-timer.sh warn        # launchd agent, :47 past every hour
tail -f ~/Library/Logs/live-feeds-warn.log
launchctl bootout gui/$(id -u)/com.live-feeds.warn   # remove it
```

`scripts/local_timer.py` reads `meta.checkedAt` from vibeplat first and does nothing
if the feed was checked in the last 50 minutes, so the laptop timer and the hourly
Actions schedule together still mean at most one fetch an hour. It commits and pushes
state the way CI does; if that races with a CI run the state commit is dropped and the
next run rebuilds it from origin.

## Adding a feed

1. Create `feeds/<name>/` with `feed.toml` (`slug`, `account`), `run.py`, `app/` and `listing/listing.json`.
   Use `lib/vibefeed` for HTTP, parsing and pushing.
2. Add `.github/workflows/<name>.yml` that calls `_run-feed.yml` with `feed` and `account`.
3. Add the account's token as a repo secret if it's a new account.
4. Run `python scripts/publish_app.py <name> --listing` once to create the vibeplat app, then run the feed.

WARN parsing approach credit: Big Local News' [warn-scraper](https://github.com/biglocalnews/warn-scraper).
