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

    if getattr(sys, "frozen", False):
        candidate = Path(sys.executable).parent / exe
    else:
        candidate = Path(__file__).parent.parent.parent / "tools" / exe

    if candidate.is_file():
        return str(candidate)

    raise RuntimeError(
        f"{name} not found.\n"
        f"  Path checked: {candidate}\n"
        "Dam bao ffmpeg.exe va ffprobe.exe nam trong thu muc tools/."
    )


# Cache tai module load — chi resolve path 1 lan duy nhat
_FFMPEG_PATH:  str | None = None
_FFPROBE_PATH: str | None = None


def _get_ffmpeg() -> str:
    global _FFMPEG_PATH
    if _FFMPEG_PATH is None:
        _FFMPEG_PATH = _find_tool("ffmpeg")
    return _FFMPEG_PATH


def _get_ffprobe() -> str:
    global _FFPROBE_PATH
    if _FFPROBE_PATH is None:
        _FFPROBE_PATH = _find_tool("ffprobe")
    return _FFPROBE_PATH


def extract_thumbnails(config: PipelineConfig, video: Path, out_dir: Path, base: str) -> list[Path]:
    """Extract thumbnail images from a video at configured timestamps."""
    ffmpeg  = _get_ffmpeg()
    ffprobe = _get_ffprobe()

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
