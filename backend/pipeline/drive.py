"""backend/pipeline/drive.py — Google Drive helpers (download, upload, folder)."""
from __future__ import annotations

import re
import threading
from pathlib import Path

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from backend.pipeline.config import LogFn


def extract_drive_file_id(url: str) -> str | None:
    """Parse Google Drive file ID tu URL."""
    for pattern in [r"/file/d/([a-zA-Z0-9_-]+)", r"id=([a-zA-Z0-9_-]+)"]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def get_or_create_folder(drive_svc, name: str, log: LogFn) -> str:
    """Tim hoac tao folder tren Drive."""
    escaped = name.replace("'", "\\'")
    query = f"name='{escaped}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    files = drive_svc.files().list(q=query, fields="files(id,name)").execute().get("files", [])
    if files:
        fid = files[0]["id"]
        log(f'[+] Dung folder "{name}" (id={fid})')
        return fid
    folder = drive_svc.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    fid = folder["id"]
    log(f'[+] Tao folder "{name}" (id={fid})')
    return fid


def download_video(
    drive_svc,
    file_id: str,
    dest: Path,
    cancel_event: threading.Event | None = None,
) -> None:
    """Download file tu Drive ve local."""
    request = drive_svc.files().get_media(fileId=file_id)
    try:
        with dest.open("wb") as fh:
            dl = MediaIoBaseDownload(fh, request, chunksize=8 * 1024 * 1024)
            done = False
            while not done:
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Download cancelled")
                _, done = dl.next_chunk()
                if cancel_event and cancel_event.is_set() and not done:
                    raise RuntimeError("Download cancelled")
    except RuntimeError as exc:
        if "cancel" in str(exc).lower():
            dest.unlink(missing_ok=True)
        raise


def upload_thumb(drive_svc, local: Path, folder_id: str) -> str:
    """Upload thumbnail len Drive va set public. Tra ve direct link."""
    media = MediaFileUpload(str(local), mimetype="image/jpeg")
    file = drive_svc.files().create(
        body={"name": local.name, "parents": [folder_id]},
        media_body=media,
        fields="id",
    ).execute()
    fid = file["id"]
    drive_svc.permissions().create(fileId=fid, body={"role": "reader", "type": "anyone"}).execute()
    return f"https://drive.google.com/uc?id={fid}"
