"""backend/jobs/state.py — Thread-safe JobState class."""
from __future__ import annotations

import threading
from datetime import datetime, timezone

from backend.models import JobSnapshot, JobStatus


class JobState:
    def __init__(self, job_id: str, spreadsheet_id: str = "", sheet_name: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.id             = job_id
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name     = sheet_name
        self.status: JobStatus = "queued"
        self.created_at     = now
        self.updated_at     = now
        self.logs: list[str] = []
        self.result: dict | None = None
        self.error: str | None  = None
        self._lock          = threading.Lock()
        self._cancel_event  = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()
        with self._lock:
            if self.status in ("queued", "running"):
                self.status = "cancelling"
            self.updated_at = datetime.now(timezone.utc).isoformat()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def add_log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with self._lock:
            self.logs.append(f"[{ts}] {message}")
            self.logs = self.logs[-500:]
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def update(self, *, status: JobStatus | None = None,
               result: dict | None = None, error: str | None = None) -> None:
        with self._lock:
            if status:
                self.status = status
            if result is not None:
                self.result = result
            if error is not None:
                self.error = error
            self.updated_at = datetime.now(timezone.utc).isoformat()

    def snapshot(self) -> JobSnapshot:
        with self._lock:
            return JobSnapshot(
                id=self.id,
                status=self.status,
                spreadsheet_id=self.spreadsheet_id,
                sheet_name=self.sheet_name,
                created_at=self.created_at,
                updated_at=self.updated_at,
                logs=list(self.logs),
                result=self.result,
                error=self.error,
            )
