from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "http://192.168.3.188:8080/v1"
MODEL = "qwen3.8-35b-a3b-q6"


def api_key() -> str:
    return os.environ.get("QWEN38_API_KEY") or "sk-local"


def image_part(path: Path) -> dict[str, str]:
    resolved = path.expanduser().resolve(strict=True)
    mime = mimetypes.guess_type(resolved.name)[0] or "image/jpeg"
    encoded = base64.b64encode(resolved.read_bytes()).decode("ascii")
    return {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}"}


def extract_text(response: dict[str, Any]) -> str:
    if response.get("output_text"):
        return str(response["output_text"]).strip()
    texts: list[str] = []
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) and part.get("text"):
                texts.append(str(part["text"]))
    return "\n".join(texts).strip() or json.dumps(response, ensure_ascii=False, indent=2)


def invoke(prompt: str, images: list[Path], *, json_mode: bool = False, max_output_tokens: int = 2048) -> str:
    content: list[dict[str, str]] = [{"type": "input_text", "text": prompt}]
    content.extend(image_part(path) for path in images)
    payload: dict[str, Any] = {
        "model": MODEL,
        "input": [{"role": "user", "content": content}],
        "max_output_tokens": max_output_tokens,
    }
    if json_mode:
        payload["text"] = {"format": {"type": "json_object"}}
    request = urllib.request.Request(
        f"{BASE_URL}/responses",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Qwen request failed with HTTP {exc.code}: {detail[:500]}") from exc
    return extract_text(body)


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the fixed internal Qwen3.8 Responses endpoint.")
    parser.add_argument("prompt")
    parser.add_argument("--image", action="append", type=Path, default=[])
    parser.add_argument("--json", action="store_true", dest="json_mode")
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = invoke(args.prompt, args.image, json_mode=args.json_mode, max_output_tokens=args.max_output_tokens)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
