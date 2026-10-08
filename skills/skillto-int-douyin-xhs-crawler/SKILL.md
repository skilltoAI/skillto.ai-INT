---
name: skillto-int-douyin-xhs-crawler
description: Build or repair local Python crawlers for Douyin and Xiaohongshu account/video data when the user provides authorized cookies, logged-in sessions, account URLs, or asks for SQLite/web analysis of post metrics.
---

# Douyin/Xiaohongshu Crawler

Use this skill when implementing, debugging, or extending a local crawler for Douyin or Xiaohongshu accounts, notes, videos, or interaction metrics. It is intended for authorized data collection using user-provided cookies or an already logged-in browser session.

## Operating Rules

- Treat cookies, authorization headers, browser profiles, and exported session files as secrets. Do not print them, store them in logs, expose them in a web UI, or commit them.
- Do not bypass login controls, paywalls, DRM, account restrictions, CAPTCHAs, or rate limits. A valid user-provided login state is allowed; a failed login state is a reason to ask for a fresh cookie/session or run a headed diagnostic.
- Prefer browser-rendered capture with Playwright/Scrapling when data arrives through XHR/fetch. Use DOM parsing only as a fallback for stable visible fields.
- Verify account ownership before saving a video/note row: the item author id from the captured JSON must match the configured account id. Store that author id in the database and filter analysis queries by it.
- Save media URLs and cover URLs, not downloaded media, unless the user explicitly asks to download authorized media.
- Keep crawls resilient: a failed account should record the account, error type, and time, then continue with the next account.

## Account Selection and Restricted Cookie

- The existing login account and its current cookie/session are the default for all crawler work. Keep using that account unless the user explicitly authorizes a different login account for the current task.
- The ordinary default login cookie has one explicit machine path on Windows: `E:\wwai\media-download\runtime\douyin_auth\default-cookie.txt`. On macOS/Linux its explicit default is `~/.config/skillto.ai/secrets/douyin-cookie.txt`. The bundled CLI resolves cookies in this order only: explicit `--cookies`, `DOUYIN_COOKIE_FILE`, then the platform default above. Never search unrelated runtime files or silently choose another cookie. Never place the cookie value in this skill, source code, command examples, logs, or reports.
- If no ordinary cookie is configured, stop before crawling and clearly tell the user that an authenticated Douyin cookie is required. Give the expected file path and point them to [cookie setup](references/cookie-setup.md), which explains how to obtain the cookie from their own logged-in browser and configure it without putting the secret in chat or shell history. Do not merely report `FileNotFoundError`.
- The login account named `小与AI` is restricted. Never load, inspect, validate, refresh, export, or send requests with its cookie/session unless the user explicitly authorizes use of `小与AI` for the specific task. A general request to crawl, a target account named `小与AI`, or the mere availability of its cookie is not authorization.
- Do not silently switch to `小与AI` if the default account fails or is rate limited. Ask for explicit authorization before any use; otherwise stop or continue only with the default account as appropriate.
- Keep the `小与AI` cookie in a separate secret file or browser profile, never in this skill, source control, logs, or a shared cookie file. Its Windows path is `E:\wwai\media-download\runtime\single_video_cookies\douyin_xiaoyu_ai_cookie.txt`; macOS/Linux uses `~/.config/skillto.ai/secrets/douyin-xiaoyu-cookie.txt`. `DOUYIN_XIAOYU_COOKIE_FILE` may explicitly override that path. Select it only through an explicit per-task account choice. Do not change the ordinary default cookie path or default account selection.

## Recommended Architecture

For a new project, use this shape unless the existing repository already has a better pattern:

- `config/accounts.json`: account URLs, platform, stable account id, and optional display name.
- `config/cookies.txt` or a user-specified cookie file outside source control.
- `crawler.py`: browser setup, cookie loading, XHR/fetch response capture, account ownership filtering, retry around transient empty loads.
- `parser.py`: JSON field extraction with aliases and safe integer/date parsing.
- `db.py`: SQLite schema, migrations, idempotent upserts, daily snapshots.
- `web.py` or API routes: local-only dashboard bound to `127.0.0.1`.
- `run.py`: `crawl`, `analyze`, `serve`, and `update` commands.

For concrete table shapes and analysis rules, read [references/project-template.md](references/project-template.md). For platform field aliases and ownership checks, read [references/platform-fields.md](references/platform-fields.md).

## Bundled CLI

This skill includes `scripts/crawl_recent_douyin_videos.py` for a repeatable Douyin account-list crawl. Use it when the user asks to crawl the recent month of short-video interaction data for many accounts and there is not already a better project-specific CLI.

Example:

```powershell
python <skills-directory>/skillto-int-douyin-xhs-crawler/scripts/crawl_recent_douyin_videos.py crawl \
  --accounts E:\path\accounts.json `
  --db E:\path\data\douyin_recent_videos.sqlite3 `
  --jsonl E:\path\data\douyin_recent_videos.jsonl `
  --csv E:\path\data\douyin_recent_videos.csv
```

Account lists may be JSON, CSV, or TXT. JSON/CSV fields can include `url`, `sec_uid`, `secUid`, `account_id`, `name`, and `platform`; TXT can contain one Douyin user URL or `sec_uid` per line, optionally `name,url`. The CLI defaults to a 30-day publish-time window, verifies each video's `author.sec_uid` against the configured account before saving, stores daily metric snapshots in SQLite, and exports latest interaction rows to JSONL/CSV when requested. Each exported video row includes title, detected topics/hashtags, cover, source URL, publish time, and interaction metrics. It records per-account errors and continues with the remaining accounts.

Important options:

- `--cookies` overrides the default cookie file. When omitted, the CLI checks `DOUYIN_COOKIE_FILE`, then the fixed Windows path `E:\wwai\media-download\runtime\douyin_auth\default-cookie.txt` or the fixed macOS/Linux path `~/.config/skillto.ai/secrets/douyin-cookie.txt`.
- `--headed` opens Chromium for login/session diagnostics.
- `--browser-channel` or `--browser-executable` can point Playwright at an installed Chrome/Edge when the bundled Chromium cache is unavailable.
- `--days` changes the rolling window.
- `--limit` runs only the first N accounts for diagnostics.
- `--allow-xiaoyu-cookie` is required before the CLI will load the restricted `小与AI` cookie path, and should only be used after explicit user authorization for that run.

For first-time setup or cookie diagnostics, read [cookie setup](references/cookie-setup.md). Prefer the bundled `scripts/configure_cookie.py` helper because it accepts the value interactively without echoing it and stores only the cookie file outside the skill directory.

## Capture Strategy

Use a Chromium context with the user's cookies or persistent authenticated profile. Attach a response listener before navigation. Capture only relevant JSON endpoints and ignore recommendation feeds, search results, ads, and unrelated profile payloads.

For account pages, scroll in small increments and wait after navigation so post lists and pagination endpoints load. If a page returns no verifiable owned items, retry once with a longer wait or headed mode before treating the account as failed.

## Analysis Defaults

When the user asks for high-performing content and gives no different rule, use a rolling 30-day window by publish time. Compute each account's average collect/favorite count and share/repost count separately. Mark an item as high interaction when either metric is strictly greater than 2x that account's average. Treat missing metrics as `NULL`, not zero, for averages.

## Runtime Check

Use the active Python environment with Playwright installed. Before substantial scraping work, confirm that Playwright can launch an installed Chromium, Chrome, or Edge browser. Prefer an existing project environment when one is available; do not hardcode another user's local path.
