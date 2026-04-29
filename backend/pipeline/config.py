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
    # Danh sach profile_id dung cho workflow da tai khoan
    # Neu rong -> dung tai khoan mac dinh (auth/token.json)
    profile_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PipelineResult:
    total_rows: int
    queued: int
    succeeded: int
    failed: int
    elapsed_seconds: float
    rows: dict[int, list[str] | None]
