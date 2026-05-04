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
    """Trả về (logged_in, email, name) từ token file của profile.

    Ưu tiên đọc email/name đã cache trong meta.json để tránh gọi Google API
    mỗi lần polling. Chỉ gọi userinfo endpoint khi chưa có cache.
    """
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

        # Đọc email/name đã cache trong meta.json trước (nhanh, không cần network)
        email, name = None, None
        with _meta_lock:
            cached_meta = load_all_profiles()
            for m in cached_meta:
                if m["id"] == profile_id:
                    email = m.get("email")
                    name  = m.get("name_google")  # tên GG riêng, khác 'name' (tên tự đặt)
                    break

        if email:
            return True, email, name

        # Thử đọc từ id_token
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            id_token_str = data.get("id_token")
            if id_token_str:
                payload_b64 = id_token_str.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                email = payload.get("email")
                name  = payload.get("name") or payload.get("given_name")
        except Exception:
            pass

        # Fallback: gọi Google userinfo endpoint (chỉ khi chưa có cache)
        if not email:
            try:
                import urllib.request
                req = urllib.request.Request(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {creds.token}"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    info = json.loads(resp.read().decode())
                    email = info.get("email")
                    name  = info.get("name") or info.get("given_name") or name
            except Exception:
                pass

        # Lưu vào meta.json để lần sau không cần gọi lại
        if email:
            with _meta_lock:
                fresh_meta = load_all_profiles()
                for m in fresh_meta:
                    if m["id"] == profile_id:
                        m["email"] = email
                        if name:
                            m["name_google"] = name
                        break
                save_profiles_meta(fresh_meta)

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
_login_lock = threading.Lock()   # bao ve viec launch OAuth thread
_meta_lock  = threading.Lock()   # bao ve read-modify-write cua meta.json


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
            google_name=name or m.get("name_google"),
            email=email or m.get("email"),
            logged_in=logged_in,
        ))
    return ProfileList(profiles=result)


@router.post("", response_model=ProfileInfo)
def create_profile(name: str = Body(..., embed=True)) -> ProfileInfo:
    """Tạo profile mới (chưa đăng nhập)."""
    with _meta_lock:
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
        google_name=name or m.get("name_google"),
        email=email or m.get("email"),
        logged_in=logged_in,
    )


@router.post("/{profile_id}/login", response_model=LoginResult)
async def login_profile(profile_id: str) -> LoginResult:
    """Mở OAuth flow cho profile cụ thể."""
    with _meta_lock:
        meta = load_all_profiles()
        m = next((x for x in meta if x["id"] == profile_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Profile not found")
    if not CLIENT_SECRETS_FILE.exists():
        raise HTTPException(status_code=400, detail="Khong tim thay client_secrets.json.")

    token_path = _profile_token_path(profile_id)

    from google_auth_oauthlib.flow import InstalledAppFlow
    import wsgiref.simple_server

    def _oauth_callback_app(environ, start_response):
        query = environ.get('QUERY_STRING', '')
        host = environ.get('HTTP_HOST', 'localhost')
        path = environ.get('PATH_INFO', '/')
        _oauth_callback_app.last_request_uri = f'http://{host}{path}?{query}'
        start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
        html_content = """
        <html>
            <head><meta charset="utf-8"></head>
            <body style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h1>Đăng nhập hoàn tất.</h1>
                <p style="color:#666;">Bạn có thể đóng tab này.</p>
            </body>
        </html>
        """
        return [html_content.encode('utf-8')]
    _oauth_callback_app.last_request_uri = None

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_FILE), SCOPES)
        server = wsgiref.simple_server.make_server('localhost', 0, _oauth_callback_app)
        flow.redirect_uri = "http://localhost:{}/".format(server.server_port)
        auth_url, _ = flow.authorization_url(prompt='consent')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi khoi tao OAuth: {str(e)}")

    def _run_flow() -> None:
        try:
            server.handle_request()
            if _oauth_callback_app.last_request_uri is not None:
                # OAuthlib yeu cau authorization_response bat dau bang https neu ko set flag insecure
                auth_resp = _oauth_callback_app.last_request_uri.replace('http://', 'https://')
                flow.fetch_token(authorization_response=auth_resp)
                creds = flow.credentials
                token_path.write_text(creds.to_json(), encoding="utf-8")
                # Doc lai meta TUOI (khong dung snapshot cu) de tranh ghi de profile khac
                _, email, _ = _read_token_info(profile_id)
                if email:
                    with _meta_lock:
                        fresh_meta = load_all_profiles()  # doc lai tu disk
                        for x in fresh_meta:
                            if x["id"] == profile_id:
                                x["email"] = email
                                break
                        save_profiles_meta(fresh_meta)
        except Exception as exc:
            print(f"[profiles] OAuth flow error for {profile_id}: {exc}", flush=True)

    with _login_lock:
        t = threading.Thread(target=_run_flow, daemon=True, name=f"oauth-{profile_id[:8]}")
        t.start()

    return LoginResult(
        status="started",
        auth_url=auth_url,
        message="Hãy copy URL và dán vào trình duyệt để đăng nhập",
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
    with _meta_lock:
        meta = load_all_profiles()
        new_meta = [x for x in meta if x["id"] != profile_id]
        if len(new_meta) == len(meta):
            raise HTTPException(status_code=404, detail="Profile not found")
        save_profiles_meta(new_meta)
    token_path = _profile_token_path(profile_id)
    if token_path.exists():
        token_path.unlink()
    return {"status": "ok", "deleted": profile_id}
