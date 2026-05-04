"""backend/jobs/routers.py — /jobs, /workflow, /utils FastAPI routers."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import (
    JobRequest, JobSnapshot,
    WorkflowRequest, WorkflowStartResult,
)
from backend.pipeline import PipelineConfig
from backend.auth import build_service
from backend.profiles import load_profile_credentials
from backend.jobs.runner import launch_job
from backend.jobs.store import get_all_jobs, get_job, is_sheet_running
from backend.pipeline.sheets import column_name


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
        snap = job.snapshot(include_logs=False)
        snap.result = None
        snap.error = None
        snapshots.append(snap)
    return snapshots


@router.post("", response_model=JobSnapshot)
async def create_job(payload: JobRequest) -> JobSnapshot:
    """Tao job cho 1 sheet — 1 job duy nhat per (spreadsheet_id, sheet_name)."""
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
        max_workers=payload.max_workers,
        upload_workers=payload.upload_workers,
        profile_id=payload.profile_id,
    )
    job = launch_job(payload.spreadsheet_id, payload.sheet_name, config, profile_id=payload.profile_id)
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
    """Khoi dong workflow: moi target la 1 job rieng biet."""
    started: list[JobSnapshot] = []
    skipped: list[str]         = []

    for target in payload.targets:
        key_str = f"{target.spreadsheet_id}::{target.sheet_name}"

        if is_sheet_running(target.spreadsheet_id, target.sheet_name):
            skipped.append(key_str)
            continue

        # Target-level profile_id; fallback ve workflow-level
        profile_id = target.profile_id or payload.profile_id

        config = PipelineConfig(
            spreadsheet_id=target.spreadsheet_id,
            sheet_name=target.sheet_name,
            drive_folder=payload.drive_folder,
            video_url_col=payload.video_url_col,
            thumb_col=payload.thumb_col,
            target_timestamps=payload.target_timestamps,
            thumb_quality=payload.thumb_quality,
            thumb_width=payload.thumb_width,
            max_workers=payload.max_workers,
            upload_workers=payload.upload_workers,
            profile_id=profile_id,
        )
        job = launch_job(target.spreadsheet_id, target.sheet_name, config, profile_id=profile_id)
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


@utils_router.get("/check-spreadsheet")
async def check_spreadsheet(spreadsheet_id: str, profile_id: str = "") -> dict:
    """Kiem tra Spreadsheet ID co ton tai khong.
    Tra ve: { ok, title, sheet_names, message }
    """
    if not spreadsheet_id.strip():
        raise HTTPException(status_code=400, detail="Spreadsheet ID khong duoc de trong")
    creds = load_profile_credentials(profile_id) if profile_id else None
    if creds is None:
        raise HTTPException(status_code=400, detail="Profile chua dang nhap")
    try:
        sheets_svc = build_service(creds, "sheets", "v4")
        meta = sheets_svc.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="properties.title,sheets.properties.title",
        ).execute()
        titles = [s.get("properties", {}).get("title", "") for s in meta.get("sheets", [])]
        title  = meta.get("properties", {}).get("title", "")
        return {
            "ok": True,
            "title": title,
            "sheet_names": titles,
            "message": f"Tìm thấy: \"{title}\" ({len(titles)} sheet)",
        }
    except Exception as e:
        err = str(e)
        if "404" in err or "not found" in err.lower():
            return {"ok": False, "title": None, "sheet_names": [], "message": "Không tìm thấy Spreadsheet ID này"}
        raise HTTPException(status_code=502, detail=f"Lỗi Google API: {err}")


@utils_router.get("/check-sheet")
async def check_sheet(
    spreadsheet_id: str,
    sheet_name: str = "Sheet1",
    profile_id: str = "",
) -> dict:
    """Kiem tra Sheet name co ton tai va co dang bi chay khong.
    Tra ve: { ok, exists, running, message }
    """
    if not spreadsheet_id.strip():
        raise HTTPException(status_code=400, detail="Spreadsheet ID khong duoc de trong")
    creds = load_profile_credentials(profile_id) if profile_id else None
    if creds is None:
        raise HTTPException(status_code=400, detail="Profile chua dang nhap")
    try:
        sheets_svc = build_service(creds, "sheets", "v4")
        meta = sheets_svc.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties.title",
        ).execute()
        titles = [s.get("properties", {}).get("title", "") for s in meta.get("sheets", [])]
        exists  = sheet_name in titles
        running = is_sheet_running(spreadsheet_id, sheet_name)

        if not exists:
            return {
                "ok": False, "exists": False, "running": False,
                "message": f"Sheet '{sheet_name}' không tồn tại. Các sheet hiện có: {', '.join(titles) or '(trống)'}",
            }
        if running:
            return {
                "ok": False, "exists": True, "running": True,
                "message": f"Sheet '{sheet_name}' đang được xử lý bởi một job khác",
            }
        return {
            "ok": True, "exists": True, "running": False,
            "message": f"Sheet '{sheet_name}' sẵn sàng",
        }
    except Exception as e:
        err = str(e)
        if "404" in err or "not found" in err.lower():
            return {"ok": False, "exists": False, "running": False, "message": "Không tìm thấy Spreadsheet ID này"}
        raise HTTPException(status_code=502, detail=f"Lỗi Google API: {err}")


# Giu lai endpoint cu de backward-compat (frontend cu van chay duoc)
@utils_router.get("/sheet-validate")
async def sheet_validate(spreadsheet_id: str, sheet_name: str = "Sheet1", profile_id: str = "") -> dict:
    if not spreadsheet_id.strip():
        raise HTTPException(status_code=400, detail="Spreadsheet ID is required")
    creds = load_profile_credentials(profile_id) if profile_id else None
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


@utils_router.post("/clear-thumb-col")
async def clear_thumb_col(payload: dict) -> dict:
    """Xóa toàn bộ dữ liệu cột thumbnail (trừ dòng tiêu đề - row 1).

    Body: { spreadsheet_id, sheet_name, thumb_col, profile_id }
    Trả về: { ok, cleared_rows, message }
    """
    spreadsheet_id = payload.get("spreadsheet_id", "").strip()
    sheet_name     = payload.get("sheet_name", "Sheet1").strip()
    thumb_col      = int(payload.get("thumb_col", 14))
    profile_id     = payload.get("profile_id", "")

    if not spreadsheet_id:
        raise HTTPException(status_code=400, detail="Thiếu spreadsheet_id")

    creds = load_profile_credentials(profile_id) if profile_id else None
    if creds is None:
        raise HTTPException(status_code=400, detail="Profile chưa đăng nhập")

    try:
        sheets_svc = build_service(creds, "sheets", "v4")

        # Lấy số dòng hiện có của sheet
        meta = sheets_svc.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets.properties",
        ).execute()
        sheet_info = next(
            (s["properties"] for s in meta.get("sheets", [])
             if s["properties"]["title"] == sheet_name),
            None,
        )
        if sheet_info is None:
            raise HTTPException(status_code=404, detail=f"Sheet '{sheet_name}' không tồn tại")

        row_count = sheet_info.get("gridProperties", {}).get("rowCount", 1000)
        if row_count <= 1:
            return {"ok": True, "cleared_rows": 0, "message": f"Sheet '{sheet_name}' chỉ có dòng tiêu đề, không có dữ liệu để xóa"}

        col = column_name(thumb_col)
        # Range tu row 2 (bo tieu de) den het
        range_notation = f"{sheet_name}!{col}2:{col}{row_count}"

        sheets_svc.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
        ).execute()

        cleared = row_count - 1
        return {
            "ok": True,
            "cleared_rows": cleared,
            "message": f"Đã xóa dữ liệu cũ cột thumbnail của '{sheet_name}'. Sẵn sàng tạo mới!",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lỗi Google API: {str(e)}")
