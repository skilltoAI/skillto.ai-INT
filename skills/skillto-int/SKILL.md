---
name: skillto-int
description: Route Skillto INT workflows across authorized social-content collection, Qwen3.8 multimodal analysis, Xiaoyu branded cover generation, and local or remote multimedia report-table operations.
---

# Skillto INT

Use this parent skill when a request involves the Skillto INT workflow, branded cover generation, or spans content collection, media analysis, and report-table maintenance. Route the work to the smallest relevant installed child skill and read that child's `SKILL.md` completely before acting.

## Child skills

- Use `skillto-int-douyin-xhs-crawler` for authorized Douyin/Xiaohongshu account or video collection, ownership verification, recent-period metrics, and high-interaction selection.
- Use `skillto-int-table` for local or authenticated remote multimedia report tables, semantic MCP CRUD, schemas, tags, ratings, history, and media fields.
- Use `skillto-int-qwen38-media-analysis` for LAN or configurable Qwen3.8 image/video understanding, classification, OCR, frame extraction, and shot analysis.
- Use `skillto-int-xiaoyu-cover` (display name: 小与封面图) for Xiaoyu branded video/course/AI-tutorial covers with bundled IP and style references, scene/ASR evidence, and independently composed 3:4 and 4:3 PNGs. For source-video covers, collect the requested video through the crawler, analyze its evidence, then generate through the cover child; use the media-analysis child when appropriate and an available ASR skill when speech transcription is needed.
- Combine the children in the task's dependency order—for example collect, analyze, then write to a table. Keep collection and model artifacts separate from the table's authoritative storage and verify each write through the table interface.

The parent skill does not broaden authorization. Cookies, browser sessions, API keys, remote writes, deletions, and external publication remain subject to the child skill's rules and the user's scope.
