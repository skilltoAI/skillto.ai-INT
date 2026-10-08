# skillto.ai INT skills

This repository distributes two Codex-compatible skills:

- `douyin-xhs-crawler`: authorized Douyin/Xiaohongshu account and video collection with ownership verification and local analysis exports.
- `skillto-table`: local or authenticated remote multimedia report tables with semantic MCP CRUD.

## Install

Clone the repository, then run one installer from the repository root:

```powershell
git clone https://github.com/skilltoAI/skillto.ai-INT.git
cd skillto.ai-INT
.\install.ps1
```

```sh
git clone https://github.com/skilltoAI/skillto.ai-INT.git
cd skillto.ai-INT
./install.sh
```

The default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise `~/.codex/skills`. Install one skill with `-Skill douyin-xhs-crawler` / `-Skill skillto-table` on PowerShell, or pass the skill name to `install.sh`.

Installers refuse to overwrite an existing skill directory. Move or back up an old installation before upgrading, then restart the agent/client so it rediscovers the skills.

## Agent installation

A coding agent can install directly from this repository by copying either folder under `skills/` into its user skill directory without flattening the folder:

```text
skills/douyin-xhs-crawler/ -> <agent-skill-root>/douyin-xhs-crawler/
skills/skillto-table/      -> <agent-skill-root>/skillto-table/
```

Each destination must contain `SKILL.md` at its root. Preserve the bundled `scripts/`, `references/`, `assets/`, and `agents/` directories. Do not copy cookies, API keys, local report data, or runtime files into the installation.

## Requirements

- Python 3.10 or newer.
- `douyin-xhs-crawler`: Playwright plus an installed Chromium/Chrome/Edge browser. Supply an authorized cookie file through `--cookies`, `DOUYIN_COOKIE_FILE`, or the documented OS-specific secret path. Never commit cookies.
- `skillto-table`: no third-party dependency for the local stdio MCP server. Remote mode needs an authenticated report-table endpoint and a protected API-key file as described in its references.

## Validate

Use Codex's `skill-creator/scripts/quick_validate.py` against each skill directory. Basic bundled checks:

```powershell
python -m py_compile skills/douyin-xhs-crawler/scripts/crawl_recent_douyin_videos.py
python skills/skillto-table/scripts/test_server.py
node skills/skillto-table/assets/test-schema-controls.cjs
```

Review each `SKILL.md` before use. External access, authenticated crawling, and remote report mutations remain subject to user authorization and the target platform's rules.
