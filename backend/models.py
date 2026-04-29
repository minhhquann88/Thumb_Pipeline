"""backend/models.py — Tất cả Pydantic models của hệ thống."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ─── Auth ────────────────────────────────────────────────────────────────────

class AuthStatus(BaseModel):
    logged_in: bool
    email: str | None = None
    name: str | None = None
    message: str


class LoginResult(BaseModel):
    status: str  # "started" | "already_running"
    message: str


# ─── Jobs ────────────────────────────────────────────────────────────────────

JobStatus = Literal["queued", "running", "cancelling", "succeeded", "failed", "cancelled"]


class JobRequest(BaseModel):
    spreadsheet_id: str = Field(min_length=1, description="Google Spreadsheet ID")
    sheet_name: str = Field(default="Sheet1", min_length=1)
    video_url_col: int = Field(default=3, ge=0)
    thumb_col: int = Field(default=14, ge=0)
    drive_folder: str = Field(default="thumbnails", min_length=1)
    target_timestamps: list[int] = Field(default_factory=lambda: [3, 8, 13, 18, 23])
    thumb_quality: int = Field(default=2, ge=1, le=31)
    thumb_width: int = Field(default=1280, ge=64)
    max_workers: int = Field(default=3, ge=1, le=16)
    upload_workers: int = Field(default=3, ge=1, le=16)
    profile_ids: list[str] = Field(default_factory=list)


class JobSnapshot(BaseModel):
    id: str
    status: JobStatus
    spreadsheet_id: str = ""   # populated from JobState
    sheet_name: str = ""       # populated from JobState
    created_at: str
    updated_at: str
    logs: list[str]
    result: dict | None = None
    error: str | None = None


# ─── Workflow ─────────────────────────────────────────────────────────────────

class WorkflowTarget(BaseModel):
    spreadsheet_id: str = Field(min_length=1)
    sheet_name: str = Field(default="Sheet1", min_length=1)
    profile_ids: list[str] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    targets: list[WorkflowTarget]
    drive_folder: str = Field(default="thumbnails", min_length=1)
    video_url_col: int = Field(default=3, ge=0)
    thumb_col: int = Field(default=14, ge=0)
    target_timestamps: list[int] = Field(default_factory=lambda: [3, 8, 13, 18, 23])
    thumb_quality: int = Field(default=2, ge=1, le=31)
    thumb_width: int = Field(default=1280, ge=64)
    max_workers: int = Field(default=3, ge=1, le=16)
    upload_workers: int = Field(default=3, ge=1, le=16)
    profile_ids: list[str] = Field(default_factory=list)


class WorkflowStartResult(BaseModel):
    started: list[JobSnapshot]
    skipped: list[str]


# ─── Profiles ────────────────────────────────────────────────────────────────

class ProfileInfo(BaseModel):
    id: str
    name: str
    email: str | None = None
    logged_in: bool = False


class ProfileList(BaseModel):
    profiles: list[ProfileInfo]
