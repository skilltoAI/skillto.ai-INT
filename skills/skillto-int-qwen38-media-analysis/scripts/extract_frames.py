from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def ffprobe_duration(video: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return float(result.stdout.strip()) if result.returncode == 0 else None
    except ValueError:
        return None


def extract_with_ffmpeg(video: Path, output: Path, interval: float, max_frames: int, quality: int) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("ffmpeg was not found")
    pattern = output / "frame-%06d.jpg"
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", f"fps=1/{interval}",
         "-frames:v", str(max_frames), "-q:v", str(quality), "-y", str(pattern)],
        check=True,
    )
    frames = sorted(output.glob("frame-*.jpg"))
    manifest = {
        "source": str(video),
        "duration_s": ffprobe_duration(video),
        "sampling": {"mode": "interval", "interval_s": interval, "max_frames": max_frames},
        "frame_count": len(frames),
        "extractor": "ffmpeg",
        "frames": [
            {"index": index, "timestamp_s": round((index - 1) * interval, 3), "file": str(path)}
            for index, path in enumerate(frames, start=1)
        ],
    }
    manifest_path = output / "frames-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract interval frames on Windows, macOS, or Linux.")
    parser.add_argument("video", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--jpeg-quality", type=int, default=3)
    args = parser.parse_args()
    if args.interval <= 0 or args.max_frames <= 0:
        parser.error("--interval and --max-frames must be positive")
    video = args.video.expanduser().resolve(strict=True)
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg"):
        manifest = extract_with_ffmpeg(video, output, args.interval, args.max_frames, args.jpeg_quality)
    else:
        fallback = Path(__file__).with_name("extract_frames_cv.py")
        subprocess.run(
            [sys.executable, str(fallback), str(video), str(output), "--interval", str(args.interval),
             "--max-frames", str(args.max_frames)],
            check=True,
        )
        manifest = output / "frames-manifest.json"
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
