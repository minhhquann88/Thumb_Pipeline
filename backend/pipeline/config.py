"""backend/pipeline/config.py — PipelineConfig & PipelineResult dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

LogFn = Callable[[str], None]


@dataclass(frozen=True)
class PipelineConfig:
    spreadsheet_id: str
    sheet_name: str = "Sheet1"
    video_url_col: int = 3
    thumb_col: int = 14
    drive_folder: str = "thumbnails"
    target_timestamps: list[int] = field(default_factory=lambda: [3, 8, 13, 18, 23])
    thumb_quality: int = 2
    thumb_width: int = 1280
    max_workers: int = 3
    upload_workers: int = 3
    # Profile ID cua tai khoan Google se dung (rong = dung tai khoan mac dinh)
    profile_id: str = ""


@dataclass(frozen=True)
class PipelineResult:
    total_rows: int
    queued: int
    succeeded: int
    failed: int
    elapsed_seconds: float
    rows: dict[int, list[str] | None]
