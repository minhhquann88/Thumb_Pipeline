"""backend/main.py — FastAPI app setup, CORS, router registration."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import auth, jobs, profiles


app = FastAPI(title="Thumb Pipeline Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"],
    allow_origin_regex=r"(tauri://localhost|https?://(localhost|127\.0\.0\.1|tauri\.localhost)(:\d+)?)",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký routers
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(jobs.router)
app.include_router(jobs.workflow_router)
app.include_router(jobs.utils_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Kiểm tra backend có đang chạy không."""
    return {
        "status": "ok",
        "service": "python-backend",
        "time": datetime.now(timezone.utc).isoformat(),
    }
