"""Extract FFmpeg cut candidates and within-shot frame evidence without altering media."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


def ffmpeg_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    installed = shutil.which("ffmpeg")
    if installed:
        return installed
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def extract(args) -> dict:
    video = args.video.resolve(strict=True)
    output = args.output.resolve()
    if (output / "scenes.json").exists():
        raise FileExistsError("Scene manifest already exists; use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not capture.isOpened() or fps <= 0 or count <= 0:
        raise RuntimeError("Cannot decode media metadata")
    duration = count / fps
    detector = subprocess.run(
        [ffmpeg_path(args.ffmpeg), "-hide_banner", "-i", str(video), "-an", "-vf",
         f"select=gt(scene\\,{args.threshold}),showinfo", "-vsync", "vfr", "-f", "null", "-"],
        capture_output=True, text=True, errors="replace", timeout=max(90, duration * 2), check=True,
    )
    detected = sorted(set(float(value) for value in re.findall(r"pts_time:([\d.]+)", detector.stderr)))
    cuts = [0.0]
    for value in detected:
        if value - cuts[-1] >= args.min_shot and duration - value >= args.min_shot:
            cuts.append(value)
    cuts.append(duration)
    scenes = []
    for index, (start, end) in enumerate(zip(cuts, cuts[1:]), 1):
        span = end - start
        timestamps = {start + span * fraction for fraction in (0.15, 0.5, 0.85)}
        if span > 6:
            timestamps.update(start + value for value in range(2, math.ceil(span), 2) if value < span)
        ordered = sorted(timestamps)
        if len(ordered) > args.max_per_shot:
            positions = {round(i * (len(ordered) - 1) / (args.max_per_shot - 1)) for i in range(args.max_per_shot)}
            ordered = [ordered[i] for i in sorted(positions)]
        frames = []
        for sample, timestamp in enumerate(ordered, 1):
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            actual = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = float(gray.mean())
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            file = output / f"shot-{index:03d}-{sample:02d}-{timestamp:.3f}s.jpg"
            # imencode + Path handles Unicode workspace names on Windows.
            success, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            if not success:
                raise RuntimeError("Frame encoding failed")
            file.write_bytes(encoded.tobytes())
            frames.append({"file": str(file), "requested_s": round(timestamp, 3), "timestamp_s": round(actual, 3),
                           "brightness": round(brightness, 2), "sharpness": round(sharpness, 2)})
        if not frames:
            raise RuntimeError(f"No evidence frame for shot {index}")
        usable = [frame for frame in frames if 10 <= frame["brightness"] <= 245] or frames
        representative = max(usable, key=lambda item: item["sharpness"])
        scenes.append({"shot_id": f"S{index:03d}", "start_s": round(start, 3), "end_s": round(end, 3),
                       "boundary_kind": "ffmpeg_scene_score_candidate", "frames": frames,
                       "representative": representative["file"], "semantic_review": "pending"})
    capture.release()
    sheets = []
    flattened = [(scene["shot_id"], frame) for scene in scenes for frame in scene["frames"]]
    for page, offset in enumerate(range(0, len(flattened), 20), 1):
        batch = flattened[offset:offset + 20]
        cell_w, cell_h = 240, 320
        sheet = Image.new("RGB", (cell_w * 5, cell_h * math.ceil(len(batch) / 5)), "#202020")
        draw = ImageDraw.Draw(sheet)
        for i, (shot_id, frame) in enumerate(batch):
            with Image.open(frame["file"]) as source:
                thumb = source.copy()
            thumb.thumbnail((cell_w - 12, cell_h - 35))
            x = (i % 5) * cell_w
            y = (i // 5) * cell_h
            sheet.paste(thumb, (x + (cell_w - thumb.width) // 2, y + 4))
            draw.text((x + 6, y + cell_h - 24), f"{shot_id}  {frame['timestamp_s']:.3f}s", fill="white")
        destination = output / f"contact-sheet-{page:02d}.jpg"
        sheet.save(destination, quality=93)
        sheets.append(str(destination))
    manifest = {"source": str(video), "duration_s": duration, "fps": fps, "width": width, "height": height,
                "sampling": {"cut_detector": "FFmpeg scene score", "threshold": args.threshold,
                             "minimum_shot_s": args.min_shot, "within_shot": "15%, 50%, 85%; every 2s for shots over 6s",
                             "max_frames_per_shot": args.max_per_shot, "note": "Cut candidates require semantic review; short cuts can be merged by minimum-shot filter"},
                "scene_count": len(scenes), "frame_count": len(flattened), "contact_sheets": sheets, "scenes": scenes}
    (output / "scenes.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {key: manifest[key] for key in ("duration_s", "fps", "width", "height", "scene_count", "frame_count", "contact_sheets")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--threshold", type=float, default=0.30)
    parser.add_argument("--min-shot", type=float, default=0.6)
    parser.add_argument("--max-per-shot", type=int, default=9)
    args = parser.parse_args()
    if not 0 < args.threshold < 1 or args.min_shot <= 0 or args.max_per_shot < 3:
        parser.error("threshold must be between 0 and 1, min-shot positive, max-per-shot >= 3")
    print(json.dumps(extract(args), ensure_ascii=False))


if __name__ == "__main__":
    main()
