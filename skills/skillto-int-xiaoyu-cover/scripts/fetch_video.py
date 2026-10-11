"""Collect one explicitly requested Douyin video using the crawler's cookie rules."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


def load_crawler(root: Path):
    source = root / "scripts" / "crawl_recent_douyin_videos.py"
    spec = importlib.util.spec_from_file_location("xiaoyu_douyin_crawler", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Crawler helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def video_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = re.search(r"/(?:video|share/video)/(\d+)", parsed.path)
    if match:
        return match.group(1)
    query = parse_qs(parsed.query)
    return next((query[k][0] for k in ("modal_id", "aweme_id", "item_id") if query.get(k)), None)


def details(value):
    if isinstance(value, dict):
        if value.get("aweme_id") and isinstance(value.get("video"), dict):
            yield value
        for child in value.values():
            yield from details(child)
    elif isinstance(value, list):
        for child in value:
            yield from details(child)


def fetch(args) -> dict:
    from playwright.sync_api import sync_playwright

    source = args.url.strip()
    if not re.fullmatch(r"https?://(?:[\w-]+\.)?douyin\.com/[^\s]*", source):
        raise ValueError("This adapter accepts a single Douyin URL only")
    crawler = load_crawler(args.crawler_root)
    cookie_path = Path(args.cookies or os.environ.get("DOUYIN_COOKIE_FILE") or crawler.DEFAULT_COOKIE_PATH).expanduser().resolve()
    crawler.guard_restricted_cookie(cookie_path, args.allow_xiaoyu_cookie)
    if not cookie_path.is_file():
        raise FileNotFoundError("Authenticated default Douyin cookie is missing; follow the crawler cookie-setup guide")
    cookies = crawler.parse_cookie_file(cookie_path)
    if not any(c["name"] in {"sessionid", "sid_tt", "sessionid_ss"} for c in cookies):
        raise ValueError("The configured cookie does not contain an authenticated session")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    payloads = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.browser_channel, headless=True)
        context = browser.new_context(locale="zh-CN", viewport={"width": 1360, "height": 900})
        context.add_cookies(cookies)
        page = context.new_page()

        def capture(response):
            if urlparse(response.url).hostname not in {"www.douyin.com", "www.iesdouyin.com"}:
                return
            if not any(token in response.url for token in ("aweme/detail", "aweme/post", "aweme/v1/web")):
                return
            try:
                payloads.append(response.json())
            except Exception:
                pass

        page.on("response", capture)
        page.goto(source, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(args.wait_ms)
        canonical = page.url
        requested_id = video_id(canonical) or video_id(source)
        if not requested_id:
            # Some share pages keep the old URL while linking to the canonical player.
            links = page.locator('a[href*="/video/"], a[href*="modal_id="]').evaluate_all("nodes => nodes.map(n => n.href)")
            unique_ids = {video_id(link) for link in links if video_id(link)}
            if len(unique_ids) == 1:
                requested_id = unique_ids.pop()
        for selector in ('script#RENDER_DATA', 'script#__NEXT_DATA__'):
            for text in page.locator(selector).all_text_contents():
                try:
                    payloads.append(json.loads(unquote(text)))
                except (ValueError, TypeError):
                    pass
        matches = [item for payload in payloads for item in details(payload) if str(item["aweme_id"]) == requested_id]
        if not requested_id or not matches:
            raise RuntimeError("No JSON detail matching the requested video was captured; do not download recommendations or bypass login/CAPTCHA")
        item = matches[0]
        author = item.get("author") or {}
        author_id = author.get("sec_uid")
        if not author_id:
            raise RuntimeError("Video author identity is missing")
        if args.author_id and author_id != args.author_id:
            raise RuntimeError("Video author does not match the requested account")
        video = item["video"]
        addresses = []
        for key in ("play_addr", "play_addr_h264", "play_addr_265", "download_addr"):
            addresses.extend((video.get(key) or {}).get("url_list") or [])
        for rate in video.get("bit_rate") or []:
            addresses.extend((rate.get("play_addr") or {}).get("url_list") or [])
        addresses = list(dict.fromkeys(url for url in addresses if urlparse(url).scheme in {"http", "https"}))
        target = output / f"douyin_{requested_id}.mp4"
        if target.exists():
            raise FileExistsError("Video destination already exists; use its saved metadata or a new output directory")
        downloaded = False
        for address in addresses[:4]:
            try:
                response = context.request.get(address, headers={"Referer": canonical}, timeout=90000)
                if not response.ok:
                    continue
                body = response.body()
                if len(body) > 1024 and b"ftyp" in body[:64]:
                    target.write_bytes(body)
                    downloaded = True
                    break
            except Exception:
                continue
        if not downloaded:
            raise RuntimeError("The requested video's authorized media URLs did not return an MP4")
        metadata = {
            "source_url": source,
            "canonical_url": f"https://www.douyin.com/video/{requested_id}",
            "video_id": requested_id,
            "author_id": author_id,
            "author_name": author.get("nickname"),
            "title": item.get("desc", ""),
            "publish_time_unix": item.get("create_time"),
            "duration_hint_s": (video.get("duration") or item.get("duration") or 0) / 1000,
            "video_path": str(target),
            "fetcher": "playwright-rendered-json-with-crawler-cookie-parser",
            "identity_verified": True,
        }
        context.close()
        browser.close()
    (output / "source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("output", type=Path)
    parser.add_argument("--crawler-root", type=Path, default=Path(__file__).resolve().parents[2] / "skillto-int-douyin-xhs-crawler")
    parser.add_argument("--cookies")
    parser.add_argument("--author-id")
    parser.add_argument("--browser-channel", default="msedge")
    parser.add_argument("--wait-ms", type=int, default=12000)
    parser.add_argument("--allow-xiaoyu-cookie", action="store_true", help="Only after explicit per-task authorization to use 小与AI login")
    args = parser.parse_args()
    try:
        result = fetch(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        # Browser errors can embed request context; do not emit headers or raw responses.
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__, "reason": str(exc) if isinstance(exc, (ValueError, RuntimeError, FileNotFoundError, PermissionError, FileExistsError)) else "Browser/network failed; inspect login and runtime without exposing session secrets"}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
