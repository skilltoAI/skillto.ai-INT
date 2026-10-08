# Douyin cookie setup

Use only a Douyin account and browser session that the user is authorized to use. A cookie grants session access: never paste it into chat, issue trackers, source files, command arguments, screenshots, or shared logs. Do not use browser extensions or third-party “cookie export” websites.

## Obtain the cookie from a logged-in browser

Chrome or Edge:

1. Sign in at `https://www.douyin.com/` and confirm that the site shows the expected account.
2. Open Developer Tools (`F12` or `Ctrl+Shift+I`) and select **Network**.
3. Reload the Douyin page, then select a request whose host is `www.douyin.com`.
4. In **Headers > Request Headers**, find `cookie` and copy only its value. If the value is collapsed, use the header's copy-value action. Do not copy or run a whole “Copy as cURL” command.

Firefox follows the same flow under **Network > request > Headers > Request headers**.

The copied value should be a long list of `name=value` pairs separated by semicolons. `sessionid` or `sid_tt` is normally present in an authenticated session. If neither is present, confirm that login succeeded and repeat the capture on a new same-site request. Never bypass a CAPTCHA or browser security warning.

## Configure securely

From the installed skill directory, run:

```powershell
python .\scripts\configure_cookie.py
```

```sh
python3 ./scripts/configure_cookie.py
```

Paste the cookie only into the hidden interactive prompt. The helper validates recognizable authenticated-session fields, writes the OS-specific default secret file, and prints only the path and cookie-name count—not the cookie value.

Fixed default locations:

- Windows: `E:\wwai\media-download\runtime\douyin_auth\default-cookie.txt`
- Linux/macOS: `~/.config/skillto.ai/secrets/douyin-cookie.txt`

To use a different protected file for a crawl, use `--cookies` or set `DOUYIN_COOKIE_FILE`. The interactive helper always writes the fixed platform default so every local session resolves the same file.

Check configuration without revealing the secret:

```powershell
python .\scripts\configure_cookie.py --check
```

```sh
python3 ./scripts/configure_cookie.py --check
```

If the cookie expires or crawling returns a login page, obtain a fresh value from the logged-in browser and run the helper again with `--replace`. Rotate or revoke a cookie immediately if it was pasted into chat, committed, or otherwise exposed.
