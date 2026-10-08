# From business language to table operations

Translate the user's nouns into knowledge base, project, table, and row. Prefer a table per repeatable entity (for example, campaigns and assets only need separate tables if each has its own fields or review workflow). Use stable business identifiers as ordinary fields; let the service assign internal UUIDs.

For each table, list fields with their business labels, type, and any allowed options. Examples: "publish date" -> `date`; "budget" -> `number`; "channel" -> `single_choice`; "references" -> image/video media. Keep field names short and stable; labels can be changed for display.

Map verbs to the semantic MCP tools: "create an activity" -> save a row; "find last month's unreviewed videos" -> query with date range, score status, and media type; "mark approved" -> assign a table tag; "score 4 because..." -> rate a row. Do not ask the user for JSON, UUIDs, file paths, or commands. Resolve names to IDs using `table_workspace` and `table_query` before a write. If names are ambiguous, ask which visible item they mean.

Browser controls follow field types: date picker and inclusive range filter for dates, numeric input and min/max filter for numbers, checkbox for boolean, option menu for choices, media upload/URL and previews for images/videos, search for text. Use multi-select for tags. For `short_video_info`, show a dense cover/title/date/metrics preview and a play icon opening the original page; expand for the full list. Keep filters combinable and show result counts.
For human row tagging, show a visible edit-tags control on every row, including untagged rows. Preselect the row's current tags; allow multiple checks, unchecks, and creation of a new tag in the same dialog. Saving sends the complete selected tag set for that row, not a single tag or a field overwrite. Show the resulting chips and persisted-save status immediately.

For destructive operations, identify exactly what will be removed. Nonempty hierarchy nodes require explicit cascading deletion. Row deletion records a snapshot; tag deletion removes assignments and records those changes. Do not silently discard imported columns or history.
