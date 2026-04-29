"""backend/jobs/routers.py — /jobs, /workflow, /utils FastAPI routers."""
from __future__ import annotations

import webbrowser

from fastapi import APIRouter, HTTPException

from backend.models import (
    JobRequest, JobSnapshot,
    WorkflowRequest, WorkflowStartResult,
)
from backend.pipeline import PipelineConfig
from backend.auth import build_service
from backend.profiles import require_profile_credentials
from backend.jobs.runner import launch_job
from backend.jobs.store import get_all_jobs, get_job, is_sheet_running


# ─── /jobs router ────────────────────────────────────────────────────────────

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobSnapshot])
async def list_jobs() -> list[JobSnapshot]:
    """Trả về tất cả jobs (đang chạy + đã xong)."""
    jobs = get_all_jobs()
    # Sắp xếp mới nhất lên đầu
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    snapshots = []
    for job in jobs[:50]:
        snap = job.snapshot()
        snap.logs = []
        snap.result = None
        snap.error = None
        snapshots.append(snap)
    return snapshots


@router.post("", response_model=JobSnapshot)
async def create_job(payload: JobRequest) -> JobSnapshot:
    """Tạo single-sheet job (backward compat)."""
    if is_sheet_running(payload.spreadsheet_id, payload.sheet_name):
        raise HTTPException(
            status_code=409,
            detail=f"Sheet '{payload.sheet_name}' trong spreadsheet '{payload.spreadsheet_id[:20]}...' dang chay.",
        )
    config = PipelineConfig(
        spreadsheet_id=payload.spreadsheet_id,
        sheet_name=payload.sheet_name,
        video_url_col=payload.video_url_col,
        thumb_col=payload.thumb_col,
        drive_folder=payload.drive_folder,
        target_timestamps=payload.target_timestamps,
        thumb_quality=payload.thumb_quality,
        thumb_width=payload.thumb_width,
        max_workers=3,
        upload_workers=payload.upload_workers,
        profile_ids=payload.profile_ids,
    )
    job = launch_job(payload.spreadsheet_id, payload.sheet_name, config)
    return job.snapshot()


@router.get("/{job_id}", response_model=JobSnapshot)
async def get_job_status(job_id: str) -> JobSnapshot:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.snapshot()


@router.delete("/{job_id}", response_model=JobSnapshot)
async def cancel_job(job_id: str) -> JobSnapshot:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    status = job.snapshot().status
    if status in ("cancelling", "succeeded", "failed", "cancelled"):
        return job.snapshot()
    if status not in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Job khong the huy — trang thai hien tai: {job.status}",
        )
    job.cancel()
    job.add_log("⏹ Đã nhận lệnh dừng — sẽ hoàn thành row hiện tại rồi dừng.")
    return job.snapshot()


# ─── /workflow router ────────────────────────────────────────────────────────

workflow_router = APIRouter(prefix="/workflow", tags=["workflow"])


@workflow_router.post("", response_model=WorkflowStartResult)
async def start_workflow(payload: WorkflowRequest) -> WorkflowStartResult:
    """Khởi động workflow: chạy nhiều sheet targets song song.

    - Mỗi target là 1 job chạy trong thread riêng.
    - Nếu (spreadsheet_id + sheet_name) đang chạy → bỏ qua (dedup).
    """
    started: list[JobSnapshot] = []
    skipped: list[str]         = []

    for target in payload.targets:
        key_str = f"{target.spreadsheet_id}::{target.sheet_name}"

        if is_sheet_running(target.spreadsheet_id, target.sheet_name):
            skipped.append(key_str)
            continue

        # Target-level profile_ids; fallback về workflow-level
        profile_ids = target.profile_ids or payload.profile_ids

        config = PipelineConfig(
            spreadsheet_id=target.spreadsheet_id,
            sheet_name=target.sheet_name,
            drive_folder=payload.drive_folder,
            video_url_col=payload.video_url_col,
            thumb_col=payload.thumb_col,
            target_timestamps=payload.target_timestamps,
            thumb_quality=payload.thumb_quality,
            thumb_width=payload.thumb_width,
            max_workers=3,
            upload_workers=payload.upload_workers,
            profile_ids=profile_ids,
        )
        job = launch_job(target.spreadsheet_id, target.sheet_name, config)
        started.append(job.snapshot())

    return WorkflowStartResult(started=started, skipped=skipped)


@workflow_router.delete("", response_model=list[JobSnapshot])
async def stop_all_workflow() -> list[JobSnapshot]:
    """Dừng tất cả jobs đang chạy."""
    cancelled = []
    for job in get_all_jobs():
        status = job.snapshot().status
        if status == "cancelling":
            cancelled.append(job.snapshot())
        elif status in ("queued", "running"):
            job.cancel()
            job.add_log("Yeu cau dung duoc gui boi Stop All.")
            cancelled.append(job.snapshot())
    return cancelled


# ─── /utils router ───────────────────────────────────────────────────────────

utils_router = APIRouter(prefix="/utils", tags=["utils"])


@utils_router.post("/open-url")
async def open_url(payload: dict) -> dict:
    url: str = payload.get("url", "")
    if not url.startswith(("https://", "http://")):
        raise HTTPException(status_code=400, detail="URL khong hop le")
    webbrowser.open(url)
    return {"status": "ok"}


@utils_router.get("/sheet-validate")
async def sheet_validate(spreadsheet_id: str, sheet_name: str = "Sheet1", profile_id: str = "") -> dict:
    if not spreadsheet_id.strip():
        raise HTTPException(status_code=400, detail="Spreadsheet ID is required")
    creds = require_profile_credentials(profile_id) if profile_id else None
    if creds is None:
        raise HTTPException(status_code=400, detail="Profile chua dang nhap")
    sheets_svc = build_service(creds, "sheets", "v4")
    meta = sheets_svc.spreadsheets().get(spreadsheetId=spreadsheet_id, fields="properties.title,sheets.properties.title").execute()
    titles = [s.get("properties", {}).get("title", "") for s in meta.get("sheets", [])]
    return {
        "ok": sheet_name in titles,
        "spreadsheet_title": meta.get("properties", {}).get("title"),
        "sheet_names": titles,
        "message": "OK" if sheet_name in titles else f"Khong tim thay sheet '{sheet_name}'",
    }
