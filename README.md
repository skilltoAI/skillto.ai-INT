# skillto.ai INT skills

This repository distributes one parent skill and two namespaced child skills:

- `skillto-int`: routes end-to-end Skillto INT requests.
- `skillto-int-douyin-xhs-crawler`: authorized Douyin/Xiaohongshu collection, ownership verification, and recent-content analysis.
- `skillto-int-table`: local or authenticated remote multimedia report tables with semantic MCP CRUD.

The three skills are installed as sibling directories because Codex-compatible agents discover skills at the skill-root level. The parent routes work to the two child skills; this preserves parent-child behavior without hiding the children from discovery.

## Install all skills

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

The default destination is `$CODEX_HOME/skills` when `CODEX_HOME` is set, otherwise `~/.codex/skills`. Restart the agent/client after installation so it rediscovers the skills. Installers refuse to overwrite existing skill directories; back up or remove an old installation before upgrading.

## Install one child

```powershell
.\install.ps1 -Skill skillto-int-douyin-xhs-crawler
.\install.ps1 -Skill skillto-int-table
```

```sh
./install.sh skillto-int-douyin-xhs-crawler
./install.sh skillto-int-table
```

Install `skillto-int` together with both children for automatic parent routing. Installing an individual child is supported when only that capability is needed.

## Vibe coding agent installation

An agent that can clone Git repositories and write to its skill root should:

1. Clone `https://github.com/skilltoAI/skillto.ai-INT.git`.
2. Determine its skill root (`$CODEX_HOME/skills`, `~/.codex/skills`, or the product-specific equivalent).
3. Run the provided installer, or copy these directories without flattening them:

```text
skills/skillto-int/                    -> <agent-skill-root>/skillto-int/
skills/skillto-int-douyin-xhs-crawler/ -> <agent-skill-root>/skillto-int-douyin-xhs-crawler/
skills/skillto-int-table/              -> <agent-skill-root>/skillto-int-table/
```

4. Verify that each destination has `SKILL.md` at its root and preserve all bundled `scripts/`, `references/`, `assets/`, and `agents/` directories.
5. Restart or reload skill discovery. Do not copy cookies, API keys, report data, or runtime files into the skill installation.

## Requirements

- Python 3.10 or newer.
- `skillto-int-douyin-xhs-crawler`: Playwright plus an installed Chromium/Chrome/Edge browser. On first use, follow its [cookie setup guide](skills/skillto-int-douyin-xhs-crawler/references/cookie-setup.md) and use the bundled interactive helper; never commit or paste cookies into chat.
- `skillto-int-table`: no third-party dependency for the local stdio MCP server. Remote mode needs an authenticated report-table endpoint and a protected API-key file as described in its references.

## Validate

Use Codex's `skill-creator/scripts/quick_validate.py` against all three directories. Basic bundled checks:

```powershell
python -m py_compile skills/skillto-int-douyin-xhs-crawler/scripts/crawl_recent_douyin_videos.py
python skills/skillto-int-table/scripts/test_server.py
node skills/skillto-int-table/assets/test-schema-controls.cjs
```

Review each `SKILL.md` before use. External access, authenticated crawling, and remote report mutations remain subject to user authorization and target-platform rules.
