"""Normalize one FireRed/FunASR JSONL transcript and associate real times with shots."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def normalize(raw: dict, duration: float) -> dict:
    sentences = raw.get("sentences") or []
    if not isinstance(sentences, list):
        raise ValueError("ASR sentences must be an array")
    segments = []
    for sentence in sentences:
        if not isinstance(sentence, dict) or not str(sentence.get("text", "")).strip():
            continue
        if not {"start_ms", "end_ms"}.issubset(sentence):
            continue
        start = float(sentence["start_ms"]) / 1000
        end = float(sentence["end_ms"]) / 1000
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start <= end <= duration + 0.25):
            raise ValueError("ASR timestamps fall outside the source duration")
        if segments and start < segments[-1]["start_s"]:
            raise ValueError("ASR sentences are not time ordered")
        segments.append({"segment_id": len(segments) + 1, "start_s": start, "end_s": end, "text": str(sentence["text"])})
    text = str(raw.get("text") or raw.get("text_tn") or "").strip()
    if not text:
        text = "".join(str(sentence.get("text", "")) for sentence in sentences if isinstance(sentence, dict))
    if not text:
        raise ValueError("No recognized speech text in the ASR result")
    return {"status": "success", "alignment": "sentence-timed" if segments else "untimed", "text": text, "segments": segments}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asr_jsonl", type=Path)
    parser.add_argument("scenes_json", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--engine", required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.asr_jsonl.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ValueError("Expected one JSONL result for one source video")
    manifest = json.loads(args.scenes_json.read_text(encoding="utf-8-sig"))
    transcript = normalize(rows[0], float(manifest["duration_s"]))
    transcript.update({"engine": args.engine, "source_result": str(args.asr_jsonl.resolve()),
                       "source_video": manifest["source"], "media_duration_s": manifest["duration_s"]})
    aligned = []
    for scene in manifest["scenes"]:
        ids = [segment["segment_id"] for segment in transcript["segments"]
               if segment["start_s"] < scene["end_s"] and segment["end_s"] > scene["start_s"]]
        aligned.append({"shot_id": scene["shot_id"], "start_s": scene["start_s"], "end_s": scene["end_s"],
                        "asr_segment_ids": ids, "alignment": transcript["alignment"]})
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, data in (("transcript.json", transcript), ("shot-asr-alignment.json", aligned)):
        target = output / name
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite {name}")
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "transcript.txt").write_text(transcript["text"], encoding="utf-8")
    print(json.dumps({"status": transcript["status"], "alignment": transcript["alignment"],
                      "segment_count": len(transcript["segments"]), "character_count": len(transcript["text"]),
                      "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
