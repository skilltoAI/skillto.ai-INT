import argparse
import json
from pathlib import Path

import cv2


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract interval frames with OpenCV.")
    parser.add_argument("video")
    parser.add_argument("output_dir")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--max-frames", type=int, default=120)
    args = parser.parse_args()

    video = Path(args.video).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video}")

    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_total = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    duration = frame_total / fps if fps > 0 else None
    frames = []
    for index in range(args.max_frames):
        timestamp = index * args.interval
        if duration is not None and timestamp > duration:
            break
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = capture.read()
        if not ok:
            break
        path = output_dir / f"frame-{index + 1:06d}.jpg"
        if not cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92]):
            raise RuntimeError(f"Could not write frame: {path}")
        frames.append({"index": index + 1, "timestamp_s": round(timestamp, 3), "file": str(path)})
    capture.release()

    manifest = {
        "source": str(video),
        "duration_s": duration,
        "sampling": {"mode": "interval", "interval_s": args.interval, "max_frames": args.max_frames},
        "frame_count": len(frames),
        "extractor": "opencv",
        "frames": frames,
    }
    manifest_path = output_dir / "frames-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

