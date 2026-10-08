# MCP server

`scripts/server.py` is a dependency-free stdio MCP server. Configure a local MCP client to run `python <agent-skill-root>/skillto-int-table/scripts/server.py`. Set `SKILLTO_TABLE_ROOT` to the desired workspace directory; otherwise it uses `~/skillto-table-data`. The process writes only inside that root. The same root must be used by the browser page service.

Tools are named for business operations: `table_workspace` (browse/create/rename/delete knowledge bases, projects, tables), `table_define` (field definitions), `table_query` (search and filters), `table_save_row` (create/update/delete), `table_review` (score and row tags), `table_select_candidates` (set a row's complete list of selected candidate image fields), and `table_tags` (list/create/rename/delete table-specific tags). Tools return readable JSON and accept structured arguments; AI should use these tools rather than shell or file edits for day-to-day changes. `table_select_candidates` accepts `tableId`, `rowId`, and `imageFields`; use `[]` to clear. It rejects images that are absent or not marked as candidates in this table.

`table_query` filters are an array of `{field, operator, value}`. Operators: `eq`, `contains`, `in`, `gte`, `lte`, `between`; `between` takes a two-item inclusive range and supports ISO dates. `search` scans field values. `scoreStatus` is `scored` or `unscored`; `tagIds` requires all selected tags. Results include a count and rows.

The MCP process is not a browser server. When creating a review page, provide a local HTTP service that reads/writes the same catalog and table files, using atomic writes and compatible history. Test that browser edits are visible in an MCP query. Do not expose the local service to a public network by default.
