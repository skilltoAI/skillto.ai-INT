---
name: skillto-int
description: Route Skillto INT workflows across authorized social-content collection, Qwen3.8 multimodal analysis, and local or remote multimedia report-table operations.
---

# Skillto INT

Use this parent skill when a request involves the Skillto INT workflow or spans content collection and report-table maintenance. Route the work to the smallest relevant installed child skill and read that child's `SKILL.md` completely before acting.

## Child skills

- Use `skillto-int-douyin-xhs-crawler` for authorized Douyin/Xiaohongshu account or video collection, ownership verification, recent-period metrics, and high-interaction selection.
- Use `skillto-int-table` for local or authenticated remote multimedia report tables, semantic MCP CRUD, schemas, tags, ratings, history, and media fields.
- Use `skillto-int-qwen38-media-analysis` for LAN or configurable Qwen3.8 image/video understanding, classification, OCR, frame extraction, and shot analysis.
- Combine the children in the task's dependency order—for example collect, analyze, then write to a table. Keep collection and model artifacts separate from the table's authoritative storage and verify each write through the table interface.

The parent skill does not broaden authorization. Cookies, browser sessions, API keys, remote writes, deletions, and external publication remain subject to the child skill's rules and the user's scope.
