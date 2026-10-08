# Project Template

This template is for local, repeatable collection and analysis. Adapt names to the repository, but keep the same invariants: verified ownership, idempotent writes, daily metric snapshots, and local-only display by default.

## Configuration

Use JSON for account configuration:

```json
[
  {
    "platform": "douyin",
    "name": "optional display name",
    "account_id": "stable platform id",
    "url": "https://www.douyin.com/user/..."
  }
]
```

For Douyin, `account_id` is usually `sec_uid`. For Xiaohongshu, derive it from the profile URL or from a verified profile JSON response. Keep cookie paths configurable and add cookie files to ignore rules.

## SQLite Schema

Core tables:

- `accounts`: `id`, `platform`, `account_id`, `name`, `url`, `follower_count`, `last_crawled_at`, `last_error`
- `items`: `id`, `account_id`, `platform_item_id`, `author_platform_id`, `title`, `item_url`, `cover_url`, `published_at`, `created_at`, `updated_at`
- `item_snapshots`: `id`, `item_id`, `snapshot_date`, `captured_at`, `like_count`, `collect_count`, `share_count`, `comment_count`
- `crawl_runs`: `id`, `started_at`, `finished_at`, `status`, `account_count`, `success_count`, `item_count`, `error_count`, `error_message`

Recommended constraints:

- `UNIQUE(platform, account_id)` on accounts when accounts from multiple platforms share a table
- `UNIQUE(account_id, platform_item_id)` on items
- `UNIQUE(item_id, snapshot_date)` on snapshots
- query-time filter `items.author_platform_id = accounts.account_id`

## Commands

Expose these entry points unless the host project already has an established CLI:

```text
python run.py crawl
python run.py analyze
python run.py serve
python run.py update
```

`update` should run crawl and analysis together. `serve` should bind to `127.0.0.1` unless the user explicitly asks for LAN/public access.

## Analysis

Default high-interaction rule:

1. Use items published in the rolling last 30 days.
2. Compute averages per account using the latest snapshot per item.
3. Exclude `NULL` metrics from averages.
4. Mark an item high interaction when `collect_count > avg_collect * 2` or `share_count > avg_share * 2`.
5. Avoid divide-by-zero; if an average is zero or missing, only show a ratio when meaningful.

Pages that users usually need:

- Overview: account count, item count, latest successful crawl, success rate
- Account list: account name, follower count, recent item count, average collect/share, high item count
- High interaction list: account name, follower count, title, cover, URL, publish time, counts, ratios, trigger reason
- Account detail: all recent items for one account
- Crawl runs: timestamps, status, failures

## Validation

Use tests or scripted checks for these invariants:

- Cookie parser handles Netscape cookies and `Cookie:` header format without printing values.
- Parser handles missing metrics as `NULL`.
- Ownership filtering rejects items whose author id does not match the configured account.
- Re-running a crawl updates the same daily snapshot instead of duplicating rows.
- Analysis catches collect-only, share-only, and both-metrics high items.
- The local dashboard returns 200 and renders account names, follower counts, and item links.
