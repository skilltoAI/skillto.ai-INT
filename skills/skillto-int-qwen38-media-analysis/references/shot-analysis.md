# Shot Analysis

Use this guide when the user asks for 拉片, shot analysis, editing analysis, storyboard reconstruction, or a time-coded content audit.

## Sampling

- General understanding: sample every 5-10 seconds, capped to a reasonable batch.
- Short-form editing: start at 1-2 seconds; densify around cuts, overlays, and action changes.
- Long-form material: make a coarse pass first, divide the timeline into chapters, then resample selected chapters.
- Scene-cut sampling is useful for visual transitions but can miss long takes with important internal action. Combine it with interval samples when coverage matters.

## Analysis Schema

Use one record per inferred shot or stable segment:

```json
{
  "start_s": 0.0,
  "end_s": 3.2,
  "evidence_frames": ["frame-000001.jpg"],
  "shot_scale": "close-up",
  "camera": "static",
  "subject_action": "",
  "setting": "",
  "visible_text": [],
  "visual_style": [],
  "narrative_function": "hook",
  "content_labels": [],
  "confidence": 0.0,
  "uncertainty": ""
}
```

Merge adjacent samples only when subject, action, setting, and camera behavior remain consistent. Mark inferred cut boundaries as approximate unless exact frame-level detection was performed.

## Quality Checks

- Every segment must cite at least one frame.
- Timestamps must be monotonic and inside the media duration.
- Do not infer audio from images.
- Keep `confidence` calibrated; ambiguous frames should retain alternatives in `uncertainty`.
- Summaries must distinguish observed facts from creative or narrative interpretation.
