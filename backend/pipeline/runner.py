"""backend/pipeline/runner.py — Main pipeline runner & per-row worker."""
from __future__ import annotations

import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from backend.auth import build_service
from backend.pipeline.config import LogFn, PipelineConfig, PipelineResult
from backend.pipeline.drive import (
    download_video,
    extract_drive_file_id,
    get_or_create_folder,
    upload_thumb,
)
from backend.pipeline.ffmpeg import extract_thumbnails
from backend.pipeline.sheets import read_sheet, write_thumb_links


# --- Worker ------------------------------------------------------------------

def _process_row(
    task: dict,
    config: PipelineConfig,
    credentials,
    log: LogFn,
    cancel_event: "threading.Event | None" = None,
) -> tuple[int, list[str] | None]:
    row_index = task["row_index"]
    row       = task["row"]
    folder_id = task["folder_id"]
    tmp_dir   = Path(task["tmp_dir"])

    prefix = f"[Row {row_index}]"

    try:
        # Checkpoint truoc khi bat dau
        if cancel_event and cancel_event.is_set():
            log(f"{prefix} Dung trong hang doi")
            return row_index, None

        video_url = row[config.video_url_col] if len(row) > config.video_url_col else ""
        file_id   = extract_drive_file_id(video_url)
        product   = row[1][:50] if len(row) > 1 else f"row_{row_index}"
        drive_svc = build_service(credentials, "drive", "v3")

        # Checkpoint 1: truoc download
        if cancel_event and cancel_event.is_set():
            log(f"{prefix} Dung truoc download")
            return row_index, None

        # Download
        video_path = tmp_dir / f"{file_id}_{row_index}.mp4"
        try:
            log(f"{prefix} Downloading... ({product})")
            download_video(drive_svc, file_id or "", video_path, cancel_event)
        except Exception as e:
            if cancel_event and cancel_event.is_set():
                log(f"{prefix} Dung trong download")
            else:
                log(f"{prefix} Download loi: {e}")
            return row_index, None

        # Checkpoint 2
        if cancel_event and cancel_event.is_set():
            video_path.unlink(missing_ok=True)
            log(f"{prefix} Dung sau download")
            return row_index, None

        # Extract thumbnails
        thumb_paths: list[Path] = []
        try:
            base = re.sub(r"[^\w]", "_", f"r{row_index}_{product[:20]}")
            thumb_paths = extract_thumbnails(config, video_path, tmp_dir, base)
            log(f"{prefix} {len(thumb_paths)} thumbnails extracted")
        except Exception as e:
            log(f"{prefix} ffmpeg loi: {e}")
            video_path.unlink(missing_ok=True)
            return row_index, None

        # Checkpoint 3
        if cancel_event and cancel_event.is_set():
            video_path.unlink(missing_ok=True)
            for tp in thumb_paths:
                tp.unlink(missing_ok=True)
            log(f"{prefix} Dung sau extract (khong upload)")
            return row_index, None

        def upload_one(path: Path) -> str:
            # Google API (httplib2) is NOT thread-safe. Build a new service for each thread.
            svc = build_service(credentials, "drive", "v3")
            return upload_thumb(svc, path, folder_id)

        links: list[str] = []
        with ThreadPoolExecutor(max_workers=config.upload_workers) as pool:
            futures = [pool.submit(upload_one, tp) for tp in thumb_paths]
            for future in futures:
                try:
                    if cancel_event and cancel_event.is_set():
                        raise RuntimeError("Upload cancelled")
                    links.append(future.result())
                except Exception as e:
                    log(f"{prefix} Upload loi: {e}")

        # Cleanup
        video_path.unlink(missing_ok=True)
        for tp in thumb_paths:
            tp.unlink(missing_ok=True)

        if cancel_event and cancel_event.is_set():
            log(f"{prefix} Dung sau upload (khong ghi sheet)")
            return row_index, None

        if links:
            log(f"{prefix} Uploaded {len(links)} thumbs")
        return row_index, links or None
    except Exception as e:
        log(f"{prefix} Lỗi không mong muốn trong quá trình xử lý: {e}")
        return row_index, None


# --- Main pipeline -----------------------------------------------------------

def run_pipeline(
    config: PipelineConfig,
    log: LogFn | None = None,
    cancel_event: threading.Event | None = None,
) -> PipelineResult:
    """Chay pipeline voi 1 tai khoan (profile_id dau tien trong config)."""
    log = log or (lambda m: None)
    t0  = time.time()

    # Load credentials — chi dung 1 tai khoan
    from backend.pipeline.credentials import load_single_credentials
    creds = load_single_credentials(config, log)

    sheets_svc = build_service(creds, "sheets", "v4")
    drive_svc  = build_service(creds, "drive",  "v3")

    log("[*] Doc sheet...")
    folder_id = get_or_create_folder(drive_svc, config.drive_folder, log)
    rows      = read_sheet(sheets_svc, config)
    data_rows = rows[1:]
    tasks: list[dict] = []

    for i, row in enumerate(data_rows, start=2):
        video_url = row[config.video_url_col] if len(row) > config.video_url_col else ""
        existing  = row[config.thumb_col]     if len(row) > config.thumb_col     else ""

        if not video_url or not video_url.startswith("http"):
            log(f"[Row {i}] Khong co video_url, bo qua")
        elif existing.strip():
            log(f"[Row {i}] Da co thumbnail, bo qua")
        elif not extract_drive_file_id(video_url):
            log(f"[Row {i}] Khong parse duoc file_id, bo qua")
        else:
            tasks.append({"row_index": i, "row": row, "folder_id": folder_id})

    log(f"\n[*] Xu ly {len(tasks)} videos / {config.max_workers} luong...\n")
    results: dict[int, list[str] | None] = {}

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        for task in tasks:
            task["tmp_dir"] = tmp_dir

        with ThreadPoolExecutor(max_workers=config.max_workers) as pool:
            futures = []
            for task in tasks:
                if cancel_event and cancel_event.is_set():
                    log(f"[Row {task['row_index']}] Bo qua - da dung")
                    results[task["row_index"]] = None
                    continue
                futures.append(
                    pool.submit(_process_row, task, config, creds, log, cancel_event)
                )

            for future in as_completed(futures):
                if cancel_event and cancel_event.is_set():
                    for f in futures:
                        f.cancel()
                row_index, links = future.result()
                if cancel_event and cancel_event.is_set():
                    results[row_index] = None
                    continue
                if links:
                    write_thumb_links(sheets_svc, config, row_index, links)
                    log(f"[Row {row_index}] Ghi {len(links)} links -> sheet")
                results[row_index] = links

    succeeded = sum(1 for v in results.values() if v)
    failed    = sum(1 for v in results.values() if not v)
    elapsed   = time.time() - t0
    log(f"\n[OK] Hoan tat trong {elapsed:.1f}s")
    log(f"   Thanh cong: {succeeded} videos")
    log(f"   Loi:        {failed} videos")

    return PipelineResult(
        total_rows=len(data_rows),
        queued=len(tasks),
        succeeded=succeeded,
        failed=failed,
        elapsed_seconds=elapsed,
        rows=results,
    )
