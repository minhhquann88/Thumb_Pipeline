"""
backend_server_entry.py
───────────────────────
Entry point cho PyInstaller bundle.
PyInstaller sẽ đóng gói file này thành backend_server.exe.

Tauri gọi: <app_dir>/_internal/backend_server.exe
→ Khởi động uvicorn FastAPI backend trên 127.0.0.1:8765
"""
import multiprocessing
import sys

import uvicorn


def main() -> None:
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8765,
        log_level="warning",   # tắt bớt noise
        access_log=False,
    )


if __name__ == "__main__":
    # Bắt buộc trên Windows với PyInstaller để tránh lỗi spawn
    multiprocessing.freeze_support()
    main()
