# Platform Fields

Use these aliases as starting points, then confirm them against the captured JSON in the current session. Douyin and Xiaohongshu change response shapes; do not rely on visible DOM text when a verified JSON author object is available.

## Douyin

Common account identifiers:

- User URL id: `/user/<sec_uid>`
- Item author id: `author.sec_uid` or `author.secUid`
- Account name: `author.nickname`, profile `user.nickname`, or profile `user_info.nickname`
- Follower count: profile `user.follower_count`, `user.followerCount`, or equivalent profile payload field

Common post fields:

- Video id: `aweme_id`, `awemeId`, `video_id`, `videoId`
- Description/title: `desc`, `description`, `title`, `text`
- Publish time: `create_time`, `createTime`, `publish_time`, `publishTime`
- Cover URL: `video.cover.url_list[0]`, `video.origin_cover.url_list[0]`, `video.dynamic_cover.url_list[0]`, or top-level cover aliases
- Detail URL: `https://www.douyin.com/video/<aweme_id>`
- Like count: `statistics.digg_count`, `statistics.like_count`, `statistics.diggCount`
- Collect count: `statistics.collect_count`, `statistics.collectCount`, `statistics.save_count`
- Share count: `statistics.share_count`, `statistics.shareCount`, `statistics.repost_count`
- Comment count: `statistics.comment_count`, `statistics.commentCount`

Useful endpoint patterns observed on web account pages include `/aweme/v1/web/aweme/post/` for account posts and `/aweme/v1/web/user/profile/other/` for profile information. Check the request query's `sec_user_id` against the configured account id before accepting a response.

## Xiaohongshu

Treat Xiaohongshu as XHR-first: capture JSON from the web app and inspect the current response structure. Common naming patterns include:

- User/account id: `user_id`, `userId`, `user.userid`, or URL profile id
- Item author id: `user.user_id`, `user.userId`, `author.user_id`, `author.userId`
- Nickname: `user.nickname`, `author.nickname`, or profile `basic_info.nickname`
- Follower count: profile stats fields such as `fans`, `follows`, `fans_count`, `follower_count`, or `interactions.fans`
- Note id: `note_id`, `noteId`, `id`, or `note_card.note_id`
- Title: `title`, `display_title`, `desc`, or `note_card.display_title`
- Publish time: `time`, `timestamp`, `last_update_time`, `create_time`
- Cover URL: `cover.url`, `image_list[0].url`, `note_card.cover.url`
- Like count: `interact_info.liked_count`, `liked_count`, `like_count`
- Collect count: `interact_info.collected_count`, `collected_count`, `collect_count`
- Share count: `interact_info.share_count`, `share_count`
- Comment count: `interact_info.comment_count`, `comment_count`

For Xiaohongshu, do not assume one endpoint is stable. Build the parser around recursive extraction of candidate note objects, then require an author-id match before saving. If the page contains mixed recommendation data, author verification is mandatory.

## Parsing Rules

- Convert numeric strings with commas or localized formatting to integers when possible.
- Convert second or millisecond timestamps to UTC ISO strings.
- Preserve unavailable metrics as `NULL`.
- Deduplicate by platform, account id, and item id. If the same item appears under multiple accounts, keep only rows whose stored author id matches the account id.
