---
name: skillto-int
description: Route Skillto INT workflows between authorized Douyin/Xiaohongshu collection and local or remote multimedia report-table operations.
---

# Skillto INT

Use this parent skill when a request involves the Skillto INT workflow or spans content collection and report-table maintenance. Route the work to the smallest relevant installed child skill and read that child's `SKILL.md` completely before acting.

## Child skills

- Use `skillto-int-douyin-xhs-crawler` for authorized Douyin/Xiaohongshu account or video collection, ownership verification, recent-period metrics, and high-interaction selection.
- Use `skillto-int-table` for local or authenticated remote multimedia report tables, semantic MCP CRUD, schemas, tags, ratings, history, and media fields.
- Use both in that order when public/account data must be collected, filtered, and then written to a report table. Keep collection artifacts separate from the table's authoritative storage and verify each write through the table interface.

The parent skill does not broaden authorization. Cookies, browser sessions, API keys, remote writes, deletions, and external publication remain subject to the child skill's rules and the user's scope.
