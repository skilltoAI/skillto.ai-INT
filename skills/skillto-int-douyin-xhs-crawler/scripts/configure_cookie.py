from __future__ import annotations

import argparse
import getpass
import os
import stat
import sys
from pathlib import Path


def default_cookie_path() -> Path:
    configured = os.environ.get("DOUYIN_DEFAULT_COOKIE_FILE")
    if configured:
        return Path(configured).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "skillto.ai" / "secrets" / "douyin-cookie.txt"
    return Path.home() / ".config" / "skillto.ai" / "secrets" / "douyin-cookie.txt"


def cookie_names(text: str) -> set[str]:
    value = text.strip()
    if value.lower().startswith("cookie:"):
        value = value.split(":", 1)[1].strip()
    names: set[str] = set()
    for pair in value.split(";"):
        if "=" not in pair:
            continue
        name, _ = pair.strip().split("=", 1)
        if name:
            names.add(name)
    return names


def validate_cookie(text: str) -> set[str]:
    names = cookie_names(text)
    if len(text.strip()) < 100 or not names:
        raise ValueError("The value does not look like a Douyin Cookie header.")
    if not ({"sessionid", "sessionid_ss", "sid_tt"} & names):
        raise ValueError("No authenticated-session field (sessionid/sessionid_ss/sid_tt) was found.")
    return names


def write_cookie(path: Path, text: str, *, replace: bool) -> None:
    if path.exists() and not replace:
        raise FileExistsError(f"Cookie file already exists: {path}. Use --replace to rotate it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure the default Douyin cookie without printing its value.")
    parser.add_argument("--path", type=Path, default=None, help="Override the destination secret file.")
    parser.add_argument("--stdin", action="store_true", help="Read the cookie from standard input instead of a hidden prompt.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing cookie file.")
    parser.add_argument("--check", action="store_true", help="Validate the configured file without showing its value.")
    args = parser.parse_args()

    path = (args.path or default_cookie_path()).expanduser().resolve()
    if args.check:
        if not path.is_file():
            print(f"Cookie is not configured. Expected file: {path}", file=sys.stderr)
            return 2
        names = validate_cookie(path.read_text(encoding="utf-8-sig", errors="replace"))
        print(f"Cookie file is configured: {path} ({len(names)} cookie names; value hidden)")
        return 0

    value = sys.stdin.read() if args.stdin else getpass.getpass("Paste Douyin Cookie value (input hidden): ")
    names = validate_cookie(value)
    write_cookie(path, value, replace=args.replace)
    print(f"Cookie configured: {path} ({len(names)} cookie names; value hidden)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"Cookie setup failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
