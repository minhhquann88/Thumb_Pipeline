"""backend/pipeline/credentials.py — Load credentials cho pipeline (1 tai khoan)."""
from __future__ import annotations

from backend.pipeline.config import LogFn, PipelineConfig


def load_single_credentials(config: PipelineConfig, log: LogFn):
    """Tra ve credentials duy nhat cho pipeline.

    - Neu config.profile_ids co phan tu -> dung profile dau tien.
    - Neu rong -> dung tai khoan mac dinh (auth/token.json).
    """
    from backend.profiles import load_profile_credentials
    from backend.auth import require_credentials

    if config.profile_id:
        pid = config.profile_id
        creds = load_profile_credentials(pid)
        if creds:
            log(f"[*] Dung profile: {pid[:12]}...")
            return creds
        raise RuntimeError(
            f"Profile '{pid}' chua dang nhap hoac token het han. "
            "Vui long dang nhap lai trong app."
        )

    # Fallback: tai khoan mac dinh (legacy token.json)
    creds = require_credentials()
    log("[*] Dung tai khoan mac dinh")
    return creds


# Giu tuong thich nguoc cho code cu con goi load_credentials_list
def load_credentials_list(config: PipelineConfig, log: LogFn):
    return [load_single_credentials(config, log)]
