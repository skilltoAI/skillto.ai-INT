from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse


DOUYIN_HOST = "www.douyin.com"
DOUYIN_POST_ENDPOINT = "/aweme/v1/web/aweme/post/"
DOUYIN_PROFILE_ENDPOINT = "/aweme/v1/web/user/profile/other/"


def secret_path(env_name: str, filename: str) -> Path:
    configured = os.environ.get(env_name)
    if configured:
        return Path(configured).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "skillto.ai" / "secrets" / filename
    return Path.home() / ".config" / "skillto.ai" / "secrets" / filename


XIAOYU_COOKIE_PATH = secret_path("DOUYIN_XIAOYU_COOKIE_FILE", "douyin-xiaoyu-cookie.txt")
DEFAULT_COOKIE_PATH = secret_path("DOUYIN_DEFAULT_COOKIE_FILE", "douyin-cookie.txt")


@dataclass(frozen=True)
class Account:
    platform: str
    account_id: str
    url: str
    name: str


@dataclass
class CrawlResult:
    account: Account
    success: bool
    videos_seen: int = 0
    recent_saved: int = 0
    error: str | None = None
    coverage: str = "unknown"
    follower_count: int | None = None
    avatar_url: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def console_safe(value: Any, *, stream=sys.stdout) -> str:
    text = str(value)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    unit_map = {"万": 10_000, "w": 10_000, "W": 10_000, "k": 1_000, "K": 1_000}
    multiplier = 1
    if text[-1:] in unit_map:
        multiplier = unit_map[text[-1]]
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except (TypeError, ValueError):
        return None


def parse_timestamp(value: Any) -> str | None:
    stamp = parse_int(value)
    if not stamp:
        return None
    if stamp > 10_000_000_000:
        stamp //= 1000
    try:
        return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return None


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def first_path(mapping: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value: Any = mapping
        for key in path.split("."):
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(key)
        if value is not None:
            return value
    return None


def first_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            found = first_url(item)
            if found:
                return found
    if isinstance(value, dict):
        for key in ("url", "url_list", "origin_cover", "dynamic_cover", "cover", "uri"):
            found = first_url(value.get(key))
            if found:
                return found
    return None


def extract_topics(raw: dict[str, Any]) -> list[str]:
    topics: list[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        text = text[1:].strip() if text.startswith("#") else text
        if text and text not in topics:
            topics.append(text)

    for key in ("text_extra", "textExtra", "cha_list", "chaList", "challenge_list", "challengeList"):
        value = raw.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            add(
                item.get("hashtag_name")
                or item.get("hashtagName")
                or item.get("cha_name")
                or item.get("chaName")
                or item.get("tag_name")
                or item.get("tagName")
                or item.get("title")
                or item.get("name")
            )
    desc = first_path(raw, "desc", "description", "title", "text")
    if isinstance(desc, str):
        for match in re.finditer(r"#([\w\u4e00-\u9fff·\-.]+)", desc):
            add(match.group(1))
    return topics


def sec_uid_from_url(url: str) -> str | None:
    match = re.search(r"/user/([^/?#]+)", url)
    if match:
        return match.group(1)
    return None


def normalize_douyin_url(account_id: str, url: str | None) -> str:
    url = (url or "").strip()
    return url or f"https://www.douyin.com/user/{account_id}"


def load_accounts(path: Path, *, default_platform: str = "douyin") -> list[Account]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = raw.get("accounts", raw) if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            raise ValueError("JSON account list must be an array or an object with an 'accounts' array")
        return [account_from_mapping(item, default_platform) for item in rows]
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return [account_from_mapping(row, default_platform) for row in reader]
    return load_text_accounts(path, default_platform=default_platform)


def account_from_mapping(item: dict[str, Any], default_platform: str) -> Account:
    platform = str(item.get("platform") or default_platform).strip().lower()
    url = str(item.get("url") or item.get("profile_url") or item.get("profileUrl") or "").strip()
    account_id = str(
        item.get("account_id")
        or item.get("sec_uid")
        or item.get("secUid")
        or item.get("uid")
        or sec_uid_from_url(url)
        or ""
    ).strip()
    if not account_id:
        raise ValueError(f"Account row is missing account_id/sec_uid/url: {item}")
    if platform != "douyin":
        raise ValueError(f"Unsupported platform in this CLI: {platform}")
    name = str(item.get("name") or item.get("accountName") or item.get("nickname") or account_id).strip()
    return Account(platform=platform, account_id=account_id, url=normalize_douyin_url(account_id, url), name=name)


def load_text_accounts(path: Path, *, default_platform: str) -> list[Account]:
    accounts: list[Account] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name = ""
        value = line
        if "," in line:
            left, right = [part.strip() for part in line.split(",", 1)]
            if "douyin.com/user/" in left:
                value, name = left, right
            else:
                name, value = left, right
        account_id = sec_uid_from_url(value) or value
        if not account_id:
            raise ValueError(f"Line {line_number} is not an account url or sec_uid")
        accounts.append(Account(default_platform, account_id, normalize_douyin_url(account_id, value), name or account_id))
    return accounts


def parse_cookie_file(path: Path, *, domain: str = ".douyin.com") -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    if not path.exists():
        raise FileNotFoundError(f"Cookie file not found: {path}")
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if "\t" not in text and ";" in text:
        header = text.strip()
        if header.lower().startswith("cookie:"):
            header = header.split(":", 1)[1].strip()
        for pair in header.split(";"):
            if "=" not in pair:
                continue
            name, value = pair.strip().split("=", 1)
            if name:
                cookies.append({"domain": domain, "path": "/", "name": name.strip(), "value": value.strip(), "secure": True})
        return cookies

    for raw in text.splitlines():
        line = raw.strip()
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")):
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_") :]
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        cookie_domain, _include_subdomains, cookie_path, secure, expires, name = parts[:6]
        value = "\t".join(parts[6:])
        item: dict[str, Any] = {
            "domain": cookie_domain or domain,
            "path": cookie_path or "/",
            "name": name,
            "value": value,
            "secure": secure.upper() == "TRUE",
        }
        expiry = parse_int(expires)
        if expiry and expiry > 0:
            item["expires"] = expiry
        cookies.append(item)
    return cookies


def guard_restricted_cookie(path: Path, allow: bool) -> None:
    try:
        is_xiaoyu = path.resolve() == XIAOYU_COOKIE_PATH.resolve()
    except OSError:
        is_xiaoyu = False
    if is_xiaoyu and not allow:
        raise PermissionError(
            "Refusing to load the restricted 小与AI cookie. Pass --allow-xiaoyu-cookie only when the user explicitly authorizes it for this run."
        )


def parse_video(raw: dict[str, Any], account_id: str) -> dict[str, Any] | None:
    author = raw.get("author") if isinstance(raw.get("author"), dict) else {}
    author_id = author.get("sec_uid") or author.get("secUid")
    if author_id != account_id:
        return None
    item_id = first_path(raw, "aweme_id", "awemeId", "video_id", "videoId")
    if item_id is None:
        return None
    stats = first_path(raw, "statistics", "stats", "interaction_info")
    if not isinstance(stats, dict):
        stats = {}
    video = raw.get("video") if isinstance(raw.get("video"), dict) else {}
    cover = first_url(first_path(video, "cover", "origin_cover", "dynamic_cover")) or first_url(
        first_path(raw, "cover", "cover_url", "coverUrl")
    )
    title = first_path(raw, "desc", "description", "title", "text")
    return {
        "platform": "douyin",
        "platform_item_id": str(item_id),
        "author_platform_id": str(author_id),
        "account_name": author.get("nickname"),
        "title": str(title or "").strip() or None,
        "item_url": f"https://www.douyin.com/video/{item_id}",
        "cover_url": cover,
        "published_at": parse_timestamp(first_path(raw, "create_time", "createTime", "publish_time", "publishTime")),
        "topics": extract_topics(raw),
        "like_count": parse_int(first_path(stats, "digg_count", "like_count", "diggCount", "likeCount")),
        "collect_count": parse_int(first_path(stats, "collect_count", "save_count", "collectCount", "saveCount")),
        "share_count": parse_int(first_path(stats, "share_count", "repost_count", "shareCount", "repostCount")),
        "comment_count": parse_int(first_path(stats, "comment_count", "commentCount")),
        "play_count": parse_int(first_path(stats, "play_count", "playCount")),
    }


def parse_profile(payload: dict[str, Any], account_id: str) -> tuple[str | None, int | None, str | None]:
    user = first_path(payload, "user", "user_info", "userInfo")
    if not isinstance(user, dict):
        return None, None, None
    user_id = user.get("sec_uid") or user.get("secUid")
    if user_id and user_id != account_id:
        return None, None, None
    name = user.get("nickname") or user.get("nick_name") or user.get("nicknameText")
    follower_count = parse_int(user.get("follower_count", user.get("followerCount")))
    avatar = first_url(user.get("avatar_thumb") or user.get("avatar_medium") or user.get("avatar_larger"))
    return str(name).strip() if name else None, follower_count, avatar


def owned_videos_from_payload(payload: dict[str, Any], account_id: str) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in payload.get("aweme_list") or payload.get("awemeList") or []:
        if not isinstance(raw, dict):
            continue
        item = parse_video(raw, account_id)
        if item:
            result[item["platform_item_id"]] = item
    return list(result.values())


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    follower_count INTEGER,
    avatar_url TEXT,
    last_crawled_at TEXT,
    last_error TEXT,
    UNIQUE(platform, account_id)
);
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_row_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    platform_item_id TEXT NOT NULL,
    author_platform_id TEXT,
    title TEXT,
    item_url TEXT NOT NULL,
    cover_url TEXT,
    topics_json TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(account_row_id, platform_item_id)
);
CREATE TABLE IF NOT EXISTS item_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    snapshot_date TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    like_count INTEGER,
    collect_count INTEGER,
    share_count INTEGER,
    comment_count INTEGER,
    play_count INTEGER,
    UNIQUE(item_id, snapshot_date)
);
CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    account_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    item_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_platform_item ON items(platform, platform_item_id);
CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON item_snapshots(snapshot_date);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def sync_accounts(self, accounts: list[Account]) -> None:
        with self.connect() as conn:
            for account in accounts:
                conn.execute(
                    """
                    INSERT INTO accounts(platform, account_id, name, url) VALUES(?,?,?,?)
                    ON CONFLICT(platform, account_id) DO UPDATE SET name=excluded.name, url=excluded.url
                    """,
                    (account.platform, account.account_id, account.name, account.url),
                )

    def start_run(self, account_count: int) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO crawl_runs(started_at,status,account_count) VALUES(?,?,?)",
                (utc_now(), "running", account_count),
            )
            return int(cursor.lastrowid)

    def finish_run(self, run_id: int, *, success: int, items: int, errors: int, error_message: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE crawl_runs
                SET finished_at=?, status=?, success_count=?, item_count=?, error_count=?, error_message=?
                WHERE id=?
                """,
                (utc_now(), "success" if errors == 0 else "partial", success, items, errors, error_message, run_id),
            )

    def account_row_id(self, account: Account) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT id FROM accounts WHERE platform=? AND account_id=?",
                (account.platform, account.account_id),
            ).fetchone()
            if not row:
                raise KeyError(account.account_id)
            return int(row["id"])

    def save_account_error(self, account: Account, error: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE accounts SET last_crawled_at=?, last_error=? WHERE platform=? AND account_id=?",
                (utc_now(), error, account.platform, account.account_id),
            )

    def update_account_profile(
        self,
        account: Account,
        *,
        name: str | None,
        follower_count: int | None,
        avatar_url: str | None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE accounts
                SET name=COALESCE(?,name), follower_count=COALESCE(?,follower_count), avatar_url=COALESCE(?,avatar_url)
                WHERE platform=? AND account_id=?
                """,
                (name, follower_count, avatar_url, account.platform, account.account_id),
            )

    def save_videos(self, account: Account, videos: list[dict[str, Any]]) -> int:
        account_row_id = self.account_row_id(account)
        now = utc_now()
        snapshot_date = now[:10]
        saved = 0
        with self.connect() as conn:
            for item in videos:
                if item.get("author_platform_id") != account.account_id:
                    continue
                if item.get("account_name"):
                    conn.execute("UPDATE accounts SET name=? WHERE id=?", (item["account_name"], account_row_id))
                conn.execute(
                    """
                    INSERT INTO items(account_row_id, platform, platform_item_id, author_platform_id, title, item_url, cover_url, topics_json, published_at, created_at, updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(account_row_id, platform_item_id) DO UPDATE SET
                        author_platform_id=COALESCE(excluded.author_platform_id,items.author_platform_id),
                        title=COALESCE(excluded.title,items.title),
                        item_url=excluded.item_url,
                        cover_url=COALESCE(excluded.cover_url,items.cover_url),
                        topics_json=excluded.topics_json,
                        published_at=COALESCE(excluded.published_at,items.published_at),
                        updated_at=excluded.updated_at
                    """,
                    (
                        account_row_id,
                        item["platform"],
                        item["platform_item_id"],
                        item.get("author_platform_id"),
                        item.get("title"),
                        item["item_url"],
                        item.get("cover_url"),
                        json.dumps(item.get("topics") or [], ensure_ascii=False),
                        item.get("published_at"),
                        now,
                        now,
                    ),
                )
                row = conn.execute(
                    "SELECT id FROM items WHERE account_row_id=? AND platform_item_id=?",
                    (account_row_id, item["platform_item_id"]),
                ).fetchone()
                conn.execute(
                    """
                    INSERT INTO item_snapshots(item_id, snapshot_date, captured_at, like_count, collect_count, share_count, comment_count, play_count)
                    VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(item_id, snapshot_date) DO UPDATE SET
                        captured_at=excluded.captured_at,
                        like_count=excluded.like_count,
                        collect_count=excluded.collect_count,
                        share_count=excluded.share_count,
                        comment_count=excluded.comment_count,
                        play_count=excluded.play_count
                    """,
                    (
                        int(row["id"]),
                        snapshot_date,
                        now,
                        item.get("like_count"),
                        item.get("collect_count"),
                        item.get("share_count"),
                        item.get("comment_count"),
                        item.get("play_count"),
                    ),
                )
                saved += 1
            conn.execute(
                "UPDATE accounts SET last_crawled_at=?, last_error=NULL WHERE id=?",
                (now, account_row_id),
            )
        return saved

    def export_rows(self, run_since: str | None = None) -> list[dict[str, Any]]:
        where = ""
        params: tuple[Any, ...] = ()
        if run_since:
            where = "WHERE datetime(i.updated_at) >= datetime(?)"
            params = (run_since,)
        sql = f"""
        WITH latest AS (
            SELECT s.*, ROW_NUMBER() OVER(PARTITION BY s.item_id ORDER BY datetime(s.captured_at) DESC) AS rn
            FROM item_snapshots s
        )
        SELECT a.platform, a.account_id, a.name AS account_name, a.url AS account_url, a.follower_count, a.avatar_url,
               i.platform_item_id, i.author_platform_id, i.title, i.item_url, i.cover_url, i.published_at,
               i.topics_json, l.captured_at, l.like_count, l.collect_count, l.share_count, l.comment_count, l.play_count
        FROM items i
        JOIN accounts a ON a.id=i.account_row_id
        JOIN latest l ON l.item_id=i.id AND l.rn=1
        {where}
        ORDER BY datetime(i.published_at) DESC, i.platform_item_id DESC
        """
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute(sql, params)]
        for row in rows:
            topics_json = row.pop("topics_json", None)
            try:
                row["topics"] = json.loads(topics_json) if topics_json else []
            except (TypeError, json.JSONDecodeError):
                row["topics"] = []
        return rows


def is_older_than_window(item: dict[str, Any], since: datetime) -> bool:
    published = parse_iso_datetime(item.get("published_at"))
    return bool(published and published < since)


def filter_recent(videos: list[dict[str, Any]], since: datetime, *, include_undated: bool) -> list[dict[str, Any]]:
    recent: list[dict[str, Any]] = []
    for item in videos:
        published = parse_iso_datetime(item.get("published_at"))
        if published is None:
            if include_undated:
                recent.append(item)
            continue
        if published >= since:
            recent.append(item)
    return recent


def crawl_douyin_account(
    account: Account,
    cookies: list[dict[str, Any]],
    *,
    since: datetime,
    headless: bool,
    browser_channel: str | None,
    browser_executable: Path | None,
    scrolls: int,
    wait_ms: int,
    include_undated: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from playwright.sync_api import sync_playwright

    captured_payloads: list[dict[str, Any]] = []
    post_payloads: list[dict[str, Any]] = []
    profile = {"name": None, "follower_count": None, "avatar_url": None}
    coverage = "limit"

    with sync_playwright() as playwright:
        launch_options: dict[str, Any] = {"headless": headless}
        if browser_channel:
            launch_options["channel"] = browser_channel
        if browser_executable:
            launch_options["executable_path"] = str(browser_executable)
        browser = playwright.chromium.launch(**launch_options)
        context = browser.new_context(locale="zh-CN")
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()

        def on_response(response):
            parsed = urlparse(response.url)
            if parsed.hostname != DOUYIN_HOST or parsed.path not in (DOUYIN_POST_ENDPOINT, DOUYIN_PROFILE_ENDPOINT):
                return
            query = parse_qs(parsed.query)
            if parsed.path == DOUYIN_POST_ENDPOINT and query.get("sec_user_id") != [account.account_id]:
                return
            if parsed.path == DOUYIN_PROFILE_ENDPOINT and query.get("sec_user_id") not in ([account.account_id], None, []):
                return
            try:
                payload = json.loads(response.body().decode("utf-8", errors="replace"))
            except Exception:
                return
            captured_payloads.append(payload)
            if parsed.path == DOUYIN_POST_ENDPOINT:
                post_payloads.append(payload)

        page.on("response", on_response)
        try:
            page.goto(account.url, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(max(wait_ms, 8_000))
            route_area = page.locator(".route-scroll-container").first
            bounds = route_area.bounding_box() if route_area.count() else None
            if bounds:
                page.mouse.move(
                    bounds["x"] + bounds["width"] * 0.65,
                    bounds["y"] + min(bounds["height"] * 0.7, bounds["height"] - 10),
                )
            else:
                page.mouse.move(900, 520)
            for _index in range(scrolls):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(750)
                if not post_payloads:
                    continue
                latest = post_payloads[-1]
                owned = owned_videos_from_payload(latest, account.account_id)
                if latest.get("has_more") in (False, 0):
                    coverage = "end"
                    break
                if owned and all(item.get("published_at") for item in owned) and all(is_older_than_window(item, since) for item in owned):
                    coverage = "window"
                    break
        finally:
            context.close()
            browser.close()

    all_videos: dict[str, dict[str, Any]] = {}
    for payload in captured_payloads:
        name, follower_count, avatar_url = parse_profile(payload, account.account_id)
        profile["name"] = name or profile["name"]
        profile["follower_count"] = follower_count if follower_count is not None else profile["follower_count"]
        profile["avatar_url"] = avatar_url or profile["avatar_url"]
        for item in owned_videos_from_payload(payload, account.account_id):
            all_videos[item["platform_item_id"]] = item

    if not all_videos:
        raise RuntimeError("未获取到可验证作者归属的作品；请检查登录态、账号URL或页面加载状态")
    recent = filter_recent(list(all_videos.values()), since, include_undated=include_undated)
    profile["coverage"] = coverage
    profile["videos_seen"] = len(all_videos)
    return recent, profile


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "platform",
        "account_id",
        "account_name",
        "account_url",
        "follower_count",
        "platform_item_id",
        "title",
        "item_url",
        "cover_url",
        "topics",
        "published_at",
        "captured_at",
        "like_count",
        "collect_count",
        "share_count",
        "comment_count",
        "play_count",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            current = dict(row)
            current["topics"] = " | ".join(current.get("topics") or [])
            writer.writerow(current)


def command_crawl(args: argparse.Namespace) -> int:
    configured_cookie = args.cookies or os.environ.get("DOUYIN_COOKIE_FILE") or DEFAULT_COOKIE_PATH
    cookie_path = Path(configured_cookie).expanduser().resolve()
    if not cookie_path.is_file():
        setup_guide = Path(__file__).resolve().parent.parent / "references" / "cookie-setup.md"
        raise FileNotFoundError(
            "No authenticated Douyin cookie file was found. Obtain the cookie from your own logged-in "
            "douyin.com browser session, then run scripts/configure_cookie.py interactively, pass --cookies, "
            f"or set DOUYIN_COOKIE_FILE. Default path: {DEFAULT_COOKIE_PATH}. Setup guide: {setup_guide}"
        )
    guard_restricted_cookie(cookie_path, args.allow_xiaoyu_cookie)
    accounts = load_accounts(args.accounts)
    if args.limit:
        accounts = accounts[: args.limit]
    db = Database(args.db)
    db.initialize()
    db.sync_accounts(accounts)
    cookies = parse_cookie_file(cookie_path, domain=".douyin.com")
    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    run_started_at = utc_now()
    run_id = db.start_run(len(accounts))

    success = 0
    error_count = 0
    item_count = 0
    messages: list[str] = []
    results: list[CrawlResult] = []

    for index, account in enumerate(accounts, start=1):
        print(f"[{index}/{len(accounts)}] {console_safe(account.name)} {account.account_id[:12]}...", flush=True)
        try:
            videos, profile = crawl_douyin_account(
                account,
                cookies,
                since=since,
                headless=not args.headed,
                browser_channel=args.browser_channel,
                browser_executable=args.browser_executable,
                scrolls=args.scrolls,
                wait_ms=args.wait_ms,
                include_undated=args.include_undated,
            )
            db.update_account_profile(
                account,
                name=profile.get("name"),
                follower_count=profile.get("follower_count"),
                avatar_url=profile.get("avatar_url"),
            )
            saved = db.save_videos(account, videos)
            success += 1
            item_count += saved
            results.append(
                CrawlResult(
                    account,
                    True,
                    videos_seen=int(profile.get("videos_seen") or 0),
                    recent_saved=saved,
                    coverage=str(profile.get("coverage") or "unknown"),
                    follower_count=profile.get("follower_count"),
                    avatar_url=profile.get("avatar_url"),
                )
            )
            print(f"  saved {saved} recent videos; seen {profile.get('videos_seen')}; coverage={profile.get('coverage')}", flush=True)
        except Exception as exc:
            error_count += 1
            message = f"{account.name}: {type(exc).__name__}: {exc}"
            messages.append(message)
            db.save_account_error(account, message)
            results.append(CrawlResult(account, False, error=message))
            print(f"  failed: {type(exc).__name__}: {console_safe(exc, stream=sys.stderr)}", file=sys.stderr, flush=True)
        if args.account_delay_sec and index < len(accounts):
            time.sleep(args.account_delay_sec)

    db.finish_run(run_id, success=success, items=item_count, errors=error_count, error_message="; ".join(messages) or None)
    rows = db.export_rows(run_since=run_started_at if args.export_current_run_only else None)
    if args.jsonl:
        write_jsonl(args.jsonl, rows)
    if args.csv:
        write_csv(args.csv, rows)
    if args.report:
        write_report(args.report, results, rows, since=since, run_id=run_id)

    print(f"crawl finished: run_id={run_id}, accounts={len(accounts)}, success={success}, errors={error_count}, videos={item_count}")
    if args.jsonl:
        print(f"jsonl: {args.jsonl}")
    if args.csv:
        print(f"csv: {args.csv}")
    if args.report:
        print(f"report: {args.report}")
    return 0 if error_count == 0 else 2


def write_report(path: Path, results: list[CrawlResult], rows: list[dict[str, Any]], *, since: datetime, run_id: int) -> None:
    payload = {
        "run_id": run_id,
        "window_start_utc": since.isoformat(timespec="seconds"),
        "generated_at": utc_now(),
        "account_count": len(results),
        "success_count": sum(1 for item in results if item.success),
        "error_count": sum(1 for item in results if not item.success),
        "video_count": len(rows),
        "accounts": [
            {
                "platform": item.account.platform,
                "account_id": item.account.account_id,
                "name": item.account.name,
                "url": item.account.url,
                "success": item.success,
                "videos_seen": item.videos_seen,
                "recent_saved": item.recent_saved,
                "coverage": item.coverage,
                "follower_count": item.follower_count,
                "avatar_url": item.avatar_url,
                "error": item.error,
            }
            for item in results
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="依据 Douyin 账号列表爬取最近一个月短视频互动数据，并写入 SQLite/JSONL/CSV。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    crawl = subparsers.add_parser("crawl", help="抓取账号列表最近 N 天视频互动数据")
    crawl.add_argument("--accounts", type=Path, required=True, help="账号列表：JSON/CSV/TXT，字段支持 url/sec_uid/account_id/name")
    crawl.add_argument(
        "--cookies",
        type=Path,
        default=None,
        help=(
            "授权 Cookie 文件；省略时先读 DOUYIN_COOKIE_FILE，再读本机默认路径 "
            f"{DEFAULT_COOKIE_PATH}。支持 Netscape 或 Cookie: header 格式"
        ),
    )
    crawl.add_argument("--db", type=Path, default=Path("data/douyin_recent_videos.sqlite3"), help="SQLite 输出路径")
    crawl.add_argument("--jsonl", type=Path, default=None, help="导出 JSONL 路径")
    crawl.add_argument("--csv", type=Path, default=None, help="导出 CSV 路径")
    crawl.add_argument("--report", type=Path, default=Path("data/douyin_recent_videos_report.json"), help="运行摘要 JSON")
    crawl.add_argument("--days", type=int, default=30, help="按发布时间保留最近多少天，默认 30")
    crawl.add_argument("--scrolls", type=int, default=45, help="每个账号最多滚动次数")
    crawl.add_argument("--wait-ms", type=int, default=2500, help="页面首次加载后的附加等待毫秒数")
    crawl.add_argument("--account-delay-sec", type=float, default=1.5, help="账号之间的等待秒数，避免过快请求")
    crawl.add_argument("--headed", action="store_true", help="显示浏览器窗口，用于登录态/页面加载排查")
    crawl.add_argument("--browser-channel", default=None, help="Playwright 浏览器频道，例如 chrome/msedge")
    crawl.add_argument("--browser-executable", type=Path, default=None, help="本机浏览器可执行文件路径，例如 Chrome.exe")
    crawl.add_argument("--include-undated", action="store_true", help="发布时间缺失的视频也保存")
    crawl.add_argument("--limit", type=int, default=0, help="只跑前 N 个账号，便于诊断")
    crawl.add_argument(
        "--export-current-run-only",
        action="store_true",
        help="JSONL/CSV 只导出本次运行更新的视频；默认导出库内所有最新快照",
    )
    crawl.add_argument(
        "--allow-xiaoyu-cookie",
        action="store_true",
        help="明确授权本次使用受限的小与AI cookie 时才打开；默认拒绝该 cookie 路径",
    )
    crawl.set_defaults(func=command_crawl)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
