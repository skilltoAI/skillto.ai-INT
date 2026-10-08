# Workspace data contract

The MCP server stores `catalog.json` at `SKILLTO_TABLE_ROOT` (default: `~/skillto-table-data`). It stores each table at `tables/<table-id>.json`. The page and MCP must use these same files through the local page service; do not maintain parallel authoritative copies. IDs are stable UUIDs. Names may change without changing IDs.

`catalog.json`:

```json
{
  "version": 2,
  "knowledgeBases": [{
    "id": "uuid", "name": "Product research", "description": "",
    "projects": [{
      "id": "uuid", "name": "Launch", "description": "",
      "tables": [{"id": "uuid", "name": "Assets", "description": ""}]
    }]
  }]
}
```

Each table JSON:

```json
{
  "version": 2,
  "id": "uuid", "title": "Assets", "subtitle": "",
  "fields": [{"name": "publishedAt", "label": "Published at", "type": "date"}],
  "tags": [{"id": "uuid", "name": "Approved", "color": "#2d7d69"}],
  "rows": [{
    "id": "uuid",
    "fields": {"title": "Example", "publishedAt": "2026-09-30"},
    "media": [{"id": "uuid", "type": "image", "src": "https://example.com/a.jpg", "label": "Example", "alt": ""}],
    "tagIds": [],
    "rating": {"score": null, "note": ""},
    "history": [], "createdAt": "2026-09-30T00:00:00Z", "updatedAt": "2026-09-30T00:00:00Z"
  }],
  "history": []
}
```

Field types: `text`, `number`, `date`, `boolean`, `image`, `video`, `single_choice`, `multiple_choice`, `short_video_info`. Choice fields include `options`. Unknown imported field values remain in `row.fields`, even without a declaration. Image/video field values may also be represented in `row.media`; retain original URL values.

Candidate-image comparison uses existing `image` fields with a `candidateGroup` string (for example `wardrobe` or `scene`) and optional `promptField` naming the related text field. Store the human choices as `row.fields.selectedCandidateImages`, an array of selected **image field names**, not image URLs. Declare it as a `multiple_choice` field with the candidate names in `options`. An empty array means no choices; multiple choices in one group are allowed. Use `table_select_candidates` to set the complete list. A choice is removed automatically when its image field is replaced, so a regenerated image cannot inherit approval of the previous image. Selection changes append `select_candidate_images` row-history events and persist to the same table JSON used by the page and MCP.

`short_video_info` is an array stored in one `row.fields` value. Use one object per video:

```json
{
  "id": "platform-video-id",
  "coverUrl": "https://example.com/cover.jpg",
  "title": "Video title",
  "publishedAt": "2026-09-30T08:00:00Z",
  "playCount": null,
  "likeCount": 120,
  "collectCount": 20,
  "shareCount": 4,
  "commentCount": 8,
  "videoUrl": "https://www.douyin.com/video/123"
}
```

Unavailable interaction counts are `null`, never fabricated as zero. `videoUrl` is a navigable source-page URL; the play icon opens it in a new tab. `coverUrl` is a reference, not a downloaded copy. Sort recent videos newest first and cap at the requested number. Render a compact preview and expand the full list on demand.

Events contain `id`, `at` (ISO UTC), `action`, `before`, and `after`. Row deletion uses a table event with `rowId`, `rowLabel`, and the deleted row snapshot in `before`. Tag rename/delete uses table history and updates affected rows; append a row event for each changed assignment. The old version-1 single-table JSON is accepted on import and normalized when copied into a workspace, preserving IDs, fields, media, ratings, and history.
