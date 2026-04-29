"""backend/pipeline/ffmpeg.py — FFmpeg/FFprobe resolver & thumbnail extraction."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from backend.pipeline.config import PipelineConfig


def _find_tool(name: str) -> str:
    """Tim ffmpeg/ffprobe tu bundle dir (exe) hoac tools/ (dev). Khong dung PATH.

    - Exe mode (PyInstaller): ffmpeg.exe nam cung thu muc backend_server.exe (_MEIPASS)
    - Dev mode             : ffmpeg.exe nam trong <project_root>/tools/
    """
    exe = name + (".exe" if sys.platform == "win32" else "")

    if hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / exe  # type: ignore[attr-defined]
    else:
        candidate = Path(__file__).parent.parent.parent / "tools" / exe

    if candidate.is_file():
        return str(candidate)

    raise RuntimeError(
        f"{name} not found.\n"
        f"  Path checked: {candidate}\n"
        "Dam bao ffmpeg.exe va ffprobe.exe nam trong thu muc tools/."
    )


def extract_thumbnails(config: PipelineConfig, video: Path, out_dir: Path, base: str) -> list[Path]:
    """Extract thumbnail images from a video at configured timestamps."""
    ffmpeg  = _find_tool("ffmpeg")
    ffprobe = _find_tool("ffprobe")

    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    timestamps = [ts for ts in config.target_timestamps if ts < duration]

    saved: list[Path] = []
    for i, ts in enumerate(timestamps, 1):
        out = out_dir / f"{base}_thumb_{i:02d}_{ts}s.jpg"
        subprocess.run(
            [ffmpeg, "-y", "-ss", str(ts), "-i", str(video),
             "-frames:v", "1", "-q:v", str(config.thumb_quality),
             "-vf", f"scale={config.thumb_width}:-1", str(out)],
            check=True, capture_output=True,
        )
        saved.append(out)
    return saved
