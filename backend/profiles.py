"""backend/profiles.py — Multi-account profile management + /profiles router."""
from __future__ import annotations

import base64
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from backend.auth import CLIENT_SECRETS_FILE, SCOPES, _get_app_data_dir
from backend.models import LoginResult, ProfileInfo, ProfileList


# ─── Storage paths ────────────────────────────────────────────────────────────

_profiles_dir        = _get_app_data_dir() / "profiles"
_profiles_meta_path  = _profiles_dir / "meta.json"

_profiles_dir.mkdir(parents=True, exist_ok=True)


def _profile_token_path(profile_id: str) -> Path:
    return _profiles_dir / f"{profile_id}.token.json"


# ─── Meta helpers ─────────────────────────────────────────────────────────────

def load_all_profiles() -> list[dict]:
    """Đọc metadata tất cả profiles từ meta.json."""
    if not _profiles_meta_path.exists():
        return []
    try:
        return json.loads(_profiles_meta_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_profiles_meta(profiles: list[dict]) -> None:
    _profiles_meta_path.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _read_token_info(profile_id: str) -> tuple[bool, str | None, str | None]:
    """Trả về (logged_in, email, name) từ token file của profile."""
    path = _profile_token_path(profile_id)
    if not path.exists():
        return False, None, None
    try:
        creds = Credentials.from_authorized_user_file(str(path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            path.write_text(creds.to_json(), encoding="utf-8")
        if not (creds and creds.valid):
            return False, None, None
        # Đọc email/name từ id_token
        data = json.loads(path.read_text(encoding="utf-8"))
        id_token = data.get("id_token")
        email, name = None, None
        if id_token:
            try:
                payload_b64 = id_token.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                email = payload.get("email")
                name  = payload.get("name") or payload.get("given_name")
            except Exception:
                pass
        return True, email, name
    except Exception:
        return False, None, None


def load_profile_credentials(profile_id: str) -> Credentials | None:
    """Load và refresh credentials cho profile. Trả None nếu chưa login."""
    path = _profile_token_path(profile_id)
    if not path.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            path.write_text(creds.to_json(), encoding="utf-8")
        return creds if (creds and creds.valid) else None
    except Exception:
        return None


def require_profile_credentials(profile_id: str) -> Credentials:
    """Trả credentials hoặc raise RuntimeError nếu chưa login."""
    creds = load_profile_credentials(profile_id)
    if creds:
        return creds
    raise RuntimeError(f"Profile '{profile_id}' chua dang nhap.")


# ─── Router ──────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/profiles", tags=["profiles"])
_login_lock = threading.Lock()


@router.get("", response_model=ProfileList)
def list_profiles() -> ProfileList:
    """Trả về tất cả profiles với trạng thái đăng nhập."""
    meta = load_all_profiles()
    result = []
    for m in meta:
        logged_in, email, name = _read_token_info(m["id"])
        result.append(ProfileInfo(
            id=m["id"],
            name=m.get("name", m["id"]),
            email=email or m.get("email"),
            logged_in=logged_in,
        ))
    return ProfileList(profiles=result)


@router.post("", response_model=ProfileInfo)
def create_profile(name: str = Body(..., embed=True)) -> ProfileInfo:
    """Tạo profile mới (chưa đăng nhập)."""
    meta = load_all_profiles()
    # Kiểm tra tên trùng
    if any(m.get("name") == name for m in meta):
        raise HTTPException(status_code=409, detail=f"Ten '{name}' da ton tai.")
    profile_id = uuid.uuid4().hex[:12]
    meta.append({"id": profile_id, "name": name, "created_at": datetime.now(timezone.utc).isoformat()})
    save_profiles_meta(meta)
    return ProfileInfo(id=profile_id, name=name, logged_in=False)


@router.get("/{profile_id}", response_model=ProfileInfo)
def get_profile(profile_id: str) -> ProfileInfo:
    """Lấy thông tin profile theo ID."""
    meta = load_all_profiles()
    m = next((x for x in meta if x["id"] == profile_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Profile not found")
    logged_in, email, name = _read_token_info(profile_id)
    return ProfileInfo(
        id=profile_id,
        name=m.get("name", profile_id),
        email=email or m.get("email"),
        logged_in=logged_in,
    )


@router.post("/{profile_id}/login", response_model=LoginResult)
async def login_profile(profile_id: str) -> LoginResult:
    """Mở OAuth flow cho profile cụ thể."""
    meta = load_all_profiles()
    m = next((x for x in meta if x["id"] == profile_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not CLIENT_SECRETS_FILE.exists():
        raise HTTPException(status_code=400, detail="Khong tim thay client_secrets.json.")

    token_path = _profile_token_path(profile_id)

    def _run_flow() -> None:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json(), encoding="utf-8")
            # Cập nhật email vào meta
            _, email, _ = _read_token_info(profile_id)
            if email:
                for x in meta:
                    if x["id"] == profile_id:
                        x["email"] = email
                        break
                save_profiles_meta(meta)
        except Exception as exc:
            print(f"[profiles] OAuth flow error for {profile_id}: {exc}", flush=True)

    with _login_lock:
        t = threading.Thread(target=_run_flow, daemon=True, name=f"oauth-{profile_id[:8]}")
        t.start()

    return LoginResult(
        status="started",
        message="Da mo trinh duyet. Dang nhap Google roi quay lai app.",
    )


@router.patch("/{profile_id}/logout", response_model=ProfileInfo)
def logout_profile(profile_id: str) -> ProfileInfo:
    """Xóa token của profile (đăng xuất)."""
    meta = load_all_profiles()
    m = next((x for x in meta if x["id"] == profile_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Profile not found")
    token_path = _profile_token_path(profile_id)
    if token_path.exists():
        token_path.unlink()
    return ProfileInfo(id=profile_id, name=m.get("name", profile_id), logged_in=False)


@router.delete("/{profile_id}")
def delete_profile(profile_id: str) -> dict:
    """Xóa hoàn toàn profile và token."""
    meta = load_all_profiles()
    new_meta = [x for x in meta if x["id"] != profile_id]
    if len(new_meta) == len(meta):
        raise HTTPException(status_code=404, detail="Profile not found")
    save_profiles_meta(new_meta)
    token_path = _profile_token_path(profile_id)
    if token_path.exists():
        token_path.unlink()
    return {"status": "ok", "deleted": profile_id}
