"""backend/jobs/runner.py — Job execution: run_job & launch_job."""
from __future__ import annotations

import threading
import uuid

from backend.jobs.state import JobState
from backend.jobs.store import register_job, unregister_sheet
from backend.pipeline import PipelineConfig, run_pipeline


def _run_job(job: JobState, config: PipelineConfig) -> None:
    if job.is_cancelled:
        job.add_log("Job da duoc yeu cau dung truoc khi bat dau.")
        job.update(status="cancelled")
        unregister_sheet(job.spreadsheet_id, job.sheet_name, job.id)
        return

    job.update(status="running")
    if job.is_cancelled:
        job.add_log("Job da duoc yeu cau dung truoc khi pipeline bat dau.")
        job.update(status="cancelled")
        unregister_sheet(job.spreadsheet_id, job.sheet_name, job.id)
        return

    job.add_log(f"[{job.sheet_name}] Job started")
    try:
        result = run_pipeline(config, log=job.add_log, cancel_event=job._cancel_event)
        if job.is_cancelled:
            job.add_log("⏹ Pipeline đã dừng — các row chưa xử lý được bỏ qua.")
            job.update(status="cancelled")
        else:
            job.update(status="succeeded", result=result.__dict__)
    except Exception as error:
        if job.is_cancelled:
            job.add_log("⏹ Pipeline đã dừng — các row chưa xử lý được bỏ qua.")
            job.update(status="cancelled")
        else:
            job.add_log(f"Job failed: {error}")
            job.update(status="failed", error=str(error))
    finally:
        unregister_sheet(job.spreadsheet_id, job.sheet_name, job.id)


def launch_job(
    spreadsheet_id: str,
    sheet_name: str,
    config: PipelineConfig,
) -> JobState:
    """Tạo JobState, đăng ký và khởi động thread."""
    job = JobState(uuid.uuid4().hex, spreadsheet_id=spreadsheet_id, sheet_name=sheet_name)
    register_job(job)
    threading.Thread(
        target=_run_job,
        args=(job, config),
        daemon=True,
        name=f"job-{job.id[:8]}-{sheet_name}",
    ).start()
    return job
