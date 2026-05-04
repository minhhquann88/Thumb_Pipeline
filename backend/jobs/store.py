"""backend/jobs/store.py — In-memory job storage & dedup tracker."""
from __future__ import annotations

import threading

from backend.jobs.state import JobState


_jobs: dict[str, JobState]         = {}
_jobs_lock                          = threading.Lock()
# Dedup tracker: (spreadsheet_id, sheet_name) → job_id đang chạy
_running_sheets: dict[tuple, str]   = {}


def _sheet_key(spreadsheet_id: str, sheet_name: str) -> tuple[str, str]:
    return (spreadsheet_id.strip(), sheet_name.strip())


def get_job(job_id: str) -> JobState | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def get_all_jobs() -> list[JobState]:
    with _jobs_lock:
        return list(_jobs.values())


def register_job(job: JobState) -> None:
    key = _sheet_key(job.spreadsheet_id, job.sheet_name)
    with _jobs_lock:
        _jobs[job.id] = job
        _running_sheets[key] = job.id


def is_sheet_running(spreadsheet_id: str, sheet_name: str) -> bool:
    key = _sheet_key(spreadsheet_id, sheet_name)
    with _jobs_lock:
        job_id = _running_sheets.get(key)
        if not job_id:
            return False
        job = _jobs.get(job_id)
        return job is not None and job.status in ("queued", "running", "cancelling")


def unregister_sheet(spreadsheet_id: str, sheet_name: str, job_id: str) -> None:
    """Xóa khỏi running_sheets khi job hoàn tất."""
    key = _sheet_key(spreadsheet_id, sheet_name)
    with _jobs_lock:
        if _running_sheets.get(key) == job_id:
            del _running_sheets[key]

