---
name: skillto-table
description: Build and maintain local or AMD-PAD remote multimedia tables organized by knowledge base and project, with shared report storage, human review pages and authenticated semantic MCP operations for AI.
---

# Skill To Table

Turn a user's business or product data-maintenance request into a usable local or remote review workspace. The hierarchy is **knowledge base > project > table**. People navigate and edit it in the browser; AI uses the bundled MCP tools for ordinary data operations. Read [the data contract](references/schema.md) when creating or converting data, and [the semantic mapping guide](references/semantic-workflow.md) when translating a business request.

## Existing capability

Preserve the former multimedia review-table behavior: import JSON arrays or objects with `rows`, preserve unknown fields, edit text and numbers with append-only row history, search and filter, score 1-5 with rationale, preview images and videos on hover and in a dialog, add/remove/replace media, autosave to project JSON, and export/import JSON with history. A static gallery or browser storage alone is insufficient.

## Workspace and navigation

- Show a persistent three-level navigation tree: knowledge bases, their projects, and each project's tables. Support create, rename, and delete at each level. Require confirmation before deletion; deleting a nonempty parent must explicitly name its descendants. Keep stable IDs when names change.
- Breadcrumbs and the selected table must stay in sync with the tree. Show an empty state with a create action at each level. Keep navigation usable on narrow screens.
- Each table owns its fields, rows, media, ratings, history, and tag definitions. Never share tag definitions implicitly between tables. Support tag create, rename, and delete in that table's page, plus assign/remove on each row. Renaming a tag must preserve row assignments; deletion removes those assignments and records history.
- Every row must expose an obvious **edit tags** action in its table cell, including when no tags exist yet. Open a multi-select control showing all of this table's tags and the row's current selection; let a person check several, uncheck to remove, create a new table tag without leaving the row, then save the complete selection with immediate disk persistence and visible feedback. Keep tags separate from ratings. Show assigned tag names in the row, and make the action usable by keyboard and on mobile. Never replace a row's other fields when changing tags.
- Provide field filters appropriate to the column type, including date ranges, plus text search, score status/range, and tag filters. Combine filters predictably, show active filters, and offer clear/reset.
- Support `short_video_info` as a compact table cell containing recent videos. Show cover, title, publish date, available interaction metrics, and a play icon linking to the original video page. Keep row height stable and reveal the full list on demand. Read [the schema](references/schema.md) for its data contract.
- For image comparison, mark image fields as candidates with a `candidateGroup` and optional `promptField`. Show a separate keyboard-accessible **select / selected** control beside each populated candidate image, without replacing the image-preview action. Let a person select multiple images in one row, including multiple images from the same group, and click again to remove a choice. Save the complete selection to the table immediately, make selected cells visually distinct, and expose the choice through the semantic MCP tool. Never infer a human choice from a score or tag, and never carry a choice onto a regenerated replacement image.
- Use the user's existing dataset as the default. Convert CSV columns into fields, retaining original image/video URLs while also making media entries. Preserve unknown input columns.

## Automatic Field Controls

These are built-in program responsibilities for every existing and newly generated table, not per-table AI work. Creating a table should require only field definitions and rows; never ask AI to add individual filter controls or hand-code visible columns.

- Build filter controls from every declared field's type. Retain undeclared imported fields and make them available too; infer a conservative type until explicitly defined.
- Numbers: optional minimum/maximum inputs with inclusive boundaries and decimal support. Dates: optional start/end date pickers. Text: substring search. Single/multiple choice: option selection (membership for an array). Boolean: all/yes/no. Image, video, and short video lists: all/has media/no media, rather than matching URLs.
- Combine active field filters, text search, and table-local tag filters with AND. Blank bounds are unrestricted; null/missing values never become numeric zero. Reject inverted ranges with a visible message. Show active-filter and result counts and provide one clear-all action. Hidden columns remain filterable.
- Provide a **显示字段** control listing all fields with checkboxes, select-all, and restore-default actions. A user decides which columns to display without changing the stored schema, rows, media, or export data. Keep choices scoped by stable table ID and retain them after reload. Browser-local view preferences are acceptable, but must not be described as shared table data.
- Adding fields, importing a schema, refreshing, and switching tables must rebuild available controls automatically without leaking another table's filters or column choices.
- Reuse the bundled `assets/schema-controls.js` and `assets/schema-controls.css` for the existing local review page; load them after the base page script/styles. This adapter uses the page's `state`, semantic API, render, media, and tag handlers. Other frontends must implement the same contract in their common table component, not copy table-ID-specific code.
- Verify numeric/date boundaries, choices, boolean and media presence, filter combination/reset, column hide/show persistence, independent table preferences, and a newly created table requiring no custom controls.

## Business request workflow

First identify the user's entities, relationships, fields, row identity, and desired CRUD actions in their own terminology. Choose field types and controls (text, number, date, boolean, image, video, single choice, multiple choice, or short video information), then map requested search, field filters, date ranges, ratings, and tags to concrete table interactions. Ask only when an ambiguity would change the data model or risk data loss. Expose business nouns and actions in the page; keep IDs, JSON paths, scripts, and protocol details out of user-facing controls.

For AI operations, use the bundled `skillto-table` MCP server and its semantic tools. The server owns storage, IDs, history, validation, and query mechanics; agents should not edit the JSON directly for routine CRUD. Use direct file conversion only for bulk import/migration, then validate through MCP. See [MCP usage](references/mcp.md). If MCP is unavailable in the current client, launch/register it or report that limitation explicitly; do not claim the semantic wrapper is active.

## Account Benchmark Tag Standard

For the account table `56fa8754-8d40-4225-8541-0be4729ade73`, assign the table-local tag **AI教学赛道对标账号** when all three conditions hold:

- `averageLikeCollectRatio < 6` (the table's average likes-to-collections ratio).
- `averageCollects > 200` (average collections per video).
- `videoCount30d > 4` (at least five videos in the recent 30-day collection window).

Use strict inequalities: values equal to 6, 200, or 4 do not qualify. Missing or nonnumeric values do not qualify. Use the account's stored recent-30-day statistics, and retain the collection timestamp when reporting results. This is a numeric benchmark selection rule; do not add an LLM-category condition unless the user requests it. It does not independently verify that the account teaches AI.

Create or reuse the tag by exact name within this table. Query the qualifying rows through `table_query`, then apply strict boundary checks before writing. Append the tag using `table_review`, preserving each row's existing tags, ratings, fields, media, and history. Repeated application must not create duplicate tags or assignments. On later refreshes, recalculate qualification from refreshed recent-30-day statistics; do not silently remove previously assigned benchmark tags unless the user requests synchronization/removal.

## Persistence and verification

### Local and AMD-PAD targets

- Before operating AMD-PAD reports, read [AMD-PAD synchronization and CRUD](references/amd-pad.md). It includes target selection, key configuration, semantic tool examples, media upload, explicit copy/import procedures, verification, and concrete report URLs.
- Local mode: run `scripts/server.py` with `SKILLTO_TABLE_ROOT`. Existing local reports remain independent and are never deleted during remote migration.
- Remote mode: set `SKILLTO_TABLE_API_URL=http://192.168.3.188:5173/api/report-tables/mcp` and `SKILLTO_TABLE_API_KEY_FILE` to a protected runtime key file. The same stdio entry delegates to `scripts/remote_client.py`, an authenticated Streamable HTTP MCP client. Remote errors must not fall back to local writes.
- AMD-PAD display is integrated into videoDeepInsight at `/report-tables`, not a second port-8765 service. Keys are managed at `/settings/api-keys`; only store hashes server-side and never put real keys in skill files or URLs.
- Remote storage is the shared `data/report_tables/` workspace: all authenticated collaborators see the same reports. Key ownership is only for key management, not report isolation. A read-only Key cannot mutate reports or media.
- Local and remote copies have stable IDs but no automatic synchronization. Explicitly identify the selected target before CRUD. Do not modify other tasks' MCP configuration.
- For AMD-PAD operations, query and mutate the remote workspace through its MCP/REST interfaces; editing the local 8765 table does not update AMD-PAD. "Refresh" rereads the selected workspace, not synchronization between machines. Do not describe the existing initial-copy script as an incremental merge tool.
- Share AMD-PAD links as `http://192.168.3.188:5173/report-tables?table=<tableId>`, not the bare workspace URL. The report workspace fills the viewport; selection updates the outer URL and reload/back/forward restores that report. Browser login is still required; never include credentials in a link.
- Follow the project's `技术规范.md` and `docs/多媒体报表与MCP技术规范.md` for backups, deployment, authentication and migration. Missing local media must be reported rather than replaced with broken host paths.

Use the same workspace data contract for the page and MCP. With a local page server, autosave edits to the project-side table JSON after every change. Label whether the last save reached disk or only browser recovery storage. Export/import a portable JSON copy. Keep row and table histories append-only, including deleted row snapshots. Use accessible URLs/paths for local media unless a self-contained export is requested.

Before handoff, verify three-level navigation, one field edit, date or field filtering, tag CRUD, creating a tag from a row, assigning at least two tags to one row and removing one without losing the other, scoring, media preview, selecting and unselecting multiple candidate images, export/import history, and an MCP query that sees a browser-side change. Give the page entrypoint and data location.
