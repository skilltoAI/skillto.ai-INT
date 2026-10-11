# skillto.ai INT skills

This repository distributes one parent skill and four namespaced child skills:

- `skillto-int`: routes end-to-end Skillto INT requests.
- `skillto-int-douyin-xhs-crawler`: authorized Douyin/Xiaohongshu collection, ownership verification, and recent-content analysis.
- `skillto-int-table`: local or authenticated remote multimedia report tables with semantic MCP CRUD.
- `skillto-int-qwen38-media-analysis`: configurable Qwen3.8 multimodal image/video understanding, classification, OCR, frame extraction, and shot analysis.
- `skillto-int-xiaoyu-cover` (小与封面图): Xiaoyu branded video/course/AI-tutorial covers, bundled IP/style assets, scene and ASR evidence, and independently composed 3:4 and 4:3 PNGs. Integrated from `xiaoyu-cover` under the project's child-skill namespace.

The five skills are installed as sibling directories because Codex-compatible agents discover skills at the skill-root level. The parent routes work to the four child skills; this preserves parent-child behavior without hiding the children from discovery.

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
.\install.ps1 -Skill skillto-int-qwen38-media-analysis
.\install.ps1 -Skill skillto-int-xiaoyu-cover
```

```sh
./install.sh skillto-int-douyin-xhs-crawler
./install.sh skillto-int-table
./install.sh skillto-int-qwen38-media-analysis
./install.sh skillto-int-xiaoyu-cover
```

Install `skillto-int` together with all four children for automatic parent routing. Installing an individual child is supported when only that capability is needed. The cover child's video adapter expects the crawler as a sibling directory (or an explicit `--crawler-root`); theme-only covers do not need crawling or ASR.

## Vibe coding agent installation

An agent that can clone Git repositories and write to its skill root should:

1. Clone `https://github.com/skilltoAI/skillto.ai-INT.git`.
2. Determine its skill root (`$CODEX_HOME/skills`, `~/.codex/skills`, or the product-specific equivalent).
3. Run the provided installer, or copy these directories without flattening them:

```text
skills/skillto-int/                    -> <agent-skill-root>/skillto-int/
skills/skillto-int-douyin-xhs-crawler/ -> <agent-skill-root>/skillto-int-douyin-xhs-crawler/
skills/skillto-int-table/              -> <agent-skill-root>/skillto-int-table/
skills/skillto-int-qwen38-media-analysis/ -> <agent-skill-root>/skillto-int-qwen38-media-analysis/
skills/skillto-int-xiaoyu-cover/       -> <agent-skill-root>/skillto-int-xiaoyu-cover/
```

4. Verify that each destination has `SKILL.md` at its root and preserve all bundled `scripts/`, `references/`, `assets/`, and `agents/` directories.
5. Restart or reload skill discovery. Do not copy cookies, API keys, report data, or runtime files into the skill installation.

## Requirements

- Python 3.10 or newer.
- `skillto-int-douyin-xhs-crawler`: Playwright plus an installed Chromium/Chrome/Edge browser. The fixed Windows Cookie path is `E:\wwai\media-download\runtime\douyin_auth\default-cookie.txt`; macOS/Linux uses `~/.config/skillto.ai/secrets/douyin-cookie.txt`. On first use, follow its [cookie setup guide](skills/skillto-int-douyin-xhs-crawler/references/cookie-setup.md); never commit or paste cookies into chat.
- `skillto-int-table`: no third-party dependency for the local stdio MCP server. Remote mode needs an authenticated report-table endpoint and a protected API-key file as described in its references.
- `skillto-int-qwen38-media-analysis`: cross-platform Python 3 client for the fixed internal AMD-PAD Qwen endpoint; Windows PowerShell wrappers are also included. Frame extraction prefers FFmpeg (`brew install ffmpeg` on macOS) and falls back to Python/OpenCV. The LAN base URL and model are embedded deployment constants; provide only `QWEN38_API_KEY` when the service does not accept the built-in local placeholder.
- `skillto-int-xiaoyu-cover`: an available `imagegen` skill and built-in `image_gen` tool for cover generation. Video mode additionally uses the crawler with Playwright and an installed Edge/Chrome, FFmpeg (or `imageio-ffmpeg`), `opencv-python`, Pillow, and an available ASR tool when speech is present. The default browser channel is Edge; pass `--browser-channel chrome` for Chrome. Both brand reference PNGs are bundled; generation outputs and downloaded media belong in the task workspace.

## Validate

Use Codex's `skill-creator/scripts/quick_validate.py` against all five directories. Basic bundled checks:

```powershell
python -m py_compile skills/skillto-int-douyin-xhs-crawler/scripts/crawl_recent_douyin_videos.py
python skills/skillto-int-table/scripts/test_server.py
node skills/skillto-int-table/assets/test-schema-controls.cjs
python -m py_compile skills/skillto-int-qwen38-media-analysis/scripts/*.py
python -m py_compile skills/skillto-int-xiaoyu-cover/scripts/*.py
```

Review each `SKILL.md` before use. External access, authenticated crawling, and remote report mutations remain subject to user authorization and target-platform rules.
