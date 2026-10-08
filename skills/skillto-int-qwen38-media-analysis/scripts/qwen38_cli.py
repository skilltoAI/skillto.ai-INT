from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from invoke_qwen38 import BASE_URL, MODEL, invoke


def status() -> None:
    root = BASE_URL.split("/v1", 1)[0] + "/"
    with urllib.request.urlopen(root, timeout=10) as response:
        print(json.dumps({"status": response.status, "api": BASE_URL, "model": MODEL}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-platform CLI for the internal Qwen3.8 service.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    for command in ("chat", "json-chat"):
        item = subparsers.add_parser(command)
        item.add_argument("prompt")
    vision = subparsers.add_parser("vision")
    vision.add_argument("image", type=Path)
    vision.add_argument("prompt")
    ocr = subparsers.add_parser("ocr")
    ocr.add_argument("image", type=Path)
    args = parser.parse_args()

    if args.command == "status":
        status()
    elif args.command == "chat":
        print(invoke(args.prompt, []))
    elif args.command == "json-chat":
        print(invoke(args.prompt, [], json_mode=True))
    elif args.command == "vision":
        print(invoke(args.prompt, [args.image]))
    elif args.command == "ocr":
        print(invoke(
            "Extract all visible text. Preserve reading order and line breaks. Mark uncertain characters.",
            [args.image],
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
