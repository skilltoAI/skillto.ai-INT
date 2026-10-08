"""Stdio MCP client bridge to the project's authenticated HTTP MCP server."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def forward(url: str, key: str, message: dict):
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json',
               'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-03-26'}
    request = Request(url.rstrip('/'), data=json.dumps(message).encode('utf-8'), headers=headers, method='POST')
    try:
        with urlopen(request, timeout=60) as response:
            if response.status == 202:
                return None
            return json.loads(response.read())
    except HTTPError as exc:
        raise RuntimeError(f'Report MCP HTTP {exc.code}; check endpoint, key, scopes and expiry') from exc
    except URLError as exc:
        raise RuntimeError('Report MCP is unreachable; no local fallback was performed') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.getenv('SKILLTO_TABLE_API_URL'))
    parser.add_argument('--key-file', default=os.getenv('SKILLTO_TABLE_API_KEY_FILE'))
    args = parser.parse_args()
    url = args.url
    if not url or urlparse(url).scheme not in {'https', 'http'} or not urlparse(url).netloc:
        parser.error('Set SKILLTO_TABLE_API_URL to the complete /api/report-tables/mcp endpoint')
    key = Path(args.key_file).read_text(encoding='utf-8').strip() if args.key_file else os.getenv('SKILLTO_TABLE_API_KEY', '')
    if not key:
        parser.error('Set SKILLTO_TABLE_API_KEY_FILE or SKILLTO_TABLE_API_KEY')
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        message = None
        try:
            message = json.loads(line)
            response = forward(url, key, message)
        except Exception as exc:
            if not isinstance(message, dict) or 'id' not in message:
                print(str(exc), file=sys.stderr)
                continue
            response = {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32603, 'message': str(exc)}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
