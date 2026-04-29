"""backend/pipeline/credentials.py — Load credentials cho pipeline."""
from __future__ import annotations

from backend.auth import require_credentials
from backend.pipeline.config import LogFn, PipelineConfig


def load_credentials_list(config: PipelineConfig, log: LogFn):
    """Tra ve danh sach credentials de dung cho pipeline.

    - Neu config.profile_ids rong: dung 1 credentials mac dinh.
    - Neu co profile_ids: load tung profile, bo qua profile chua login.
    """
    from backend.profiles import load_profile_credentials

    if not config.profile_ids:
        creds = require_credentials()
        log("[*] Dung tai khoan mac dinh")
        return [creds]

    creds_list = []
    for pid in config.profile_ids:
        c = load_profile_credentials(pid)
        if c:
            creds_list.append(c)
            log(f"[*] Profile '{pid}' san sang")
        else:
            log(f"[!] Profile '{pid}' chua dang nhap, bo qua")

    if not creds_list:
        raise RuntimeError(
            "Khong co profile nao hop le. Hay dang nhap it nhat 1 tai khoan."
        )
    return creds_list
