---
name: skillto-int-qwen38-media-analysis
description: Use the LAN AMD-PAD Qwen3.8 service for multimodal image or video understanding, content classification, frame extraction, shot-by-shot breakdowns, OCR, and structured media analysis. Use when local media must be inspected or classified; do not use for downloading protected media or ordinary text-only questions.
---

# Skillto INT Qwen3.8 Media Analysis

Use the fixed internal AMD-PAD OpenAI-compatible Responses endpoint `http://192.168.3.188:8080/v1` with model `qwen3.8-35b-a3b-q6`. These non-secret deployment constants are intentionally embedded in the scripts because this skill is for the stable internal environment. Supply credentials through `QWEN38_API_KEY`, never in this skill or source files. Keep source media local unless the user explicitly requests another destination.

## Route The Task

- Single image, a small frame set, OCR, or classification: use `scripts/invoke-qwen38.ps1`.
- Video sampling: run `scripts/extract-frames.ps1`, then analyze the resulting manifest and frames with `scripts/invoke-qwen38.ps1`.
- Full shot breakdown: read `references/shot-analysis.md` before extracting frames.
- AMD-PAD CLI operations (`status`, `chat`, `json-chat`, `vision`, `ocr`): use `scripts/qwen38-remote-cli.ps1`. Its `native` mode is only for SSH maintenance, requires `sshpass`, and requires `QWEN38_NATIVE_WRAPPER` to point to an authorized local wrapper.
- Large batches: start with a coarse pass, then sample densely only around transitions or uncertain segments. Avoid sending near-duplicate frames.

## Required Behavior

1. Confirm the input paths and requested deliverable. Do not modify the source media.
2. For video, record duration and sampling policy. Prefer interval sampling for general understanding and scene sampling for editing analysis.
3. Ask Qwen for JSON when results will be merged, sorted, filtered, or exported. Treat model JSON as untrusted and validate it before downstream use.
4. Separate direct observations from interpretation. Preserve timestamps and frame filenames so every claim is traceable.
5. Report sampling gaps and uncertainty. Do not claim a full-video review when only sampled frames were inspected.
6. Do not bypass DRM, paywalls, authentication, or other access controls.

## Common Commands

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$skill = Join-Path $codexHome 'skills\skillto-int-qwen38-media-analysis'

& "$skill\scripts\invoke-qwen38.ps1" -ImagePath 'E:\media\frame.jpg' `
  -Prompt 'Describe the scene, visible text, people, actions, and safety risks.'

& "$skill\scripts\invoke-qwen38.ps1" -ImagePath 'E:\media\frame.jpg' `
  -Prompt 'Classify this frame. Return JSON with category, confidence, evidence, and alternatives.' -Json

& "$skill\scripts\extract-frames.ps1" -VideoPath 'E:\media\input.mp4' `
  -OutputDirectory 'E:\media\input-frames' -IntervalSeconds 5 -MaxFrames 120

& "$skill\scripts\qwen38-remote-cli.ps1" status
& "$skill\scripts\qwen38-remote-cli.ps1" json-chat 'Return a JSON taxonomy for these labels: tutorial, interview, ad.'
```

## Outputs

For a shot breakdown, default to a UTF-8 JSONL or Markdown table containing: time range, frame evidence, shot scale, camera movement, subject/action, setting, dialogue or visible text, audio notes when separately available, narrative function, content labels, confidence, and uncertainty.

The vision model receives images, not the audio track. Never invent speech, music, or sound effects from silent frames. Use a transcription/audio tool when audio analysis is requested, then align those results by timestamp.
