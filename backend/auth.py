"""backend/auth.py — OAuth2 credentials + /auth router."""
from __future__ import annotations

import base64
import json
import os
import sys
import threading
from pathlib import Path

import httplib2
from fastapi import APIRouter, HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build

from backend.models import AuthStatus, LoginResult


# ─── Constants ───────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_app_data_dir() -> Path:
    r"""Thu muc ghi du lieu user: %APPDATA%\ThumbPipeline (Windows) hoac ~/.ThumbPipeline."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        d = Path(appdata) / "ThumbPipeline"
    else:
        d = Path.home() / ".ThumbPipeline"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_bundle_dir() -> Path:
    """Thư mục chứa file đóng gói: MEIPASS khi PyInstaller, project root khi dev."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent.parent


TOKEN_FILE = _get_app_data_dir() / "token.json"
CLIENT_SECRETS_FILE = _get_bundle_dir() / "client_secrets.json"


# ─── Credential helpers ──────────────────────────────────────────────────────

def load_oauth2_credentials(token_file: Path | None = None) -> Credentials | None:
    """Đọc token.json, tự refresh nếu hết hạn. Trả None nếu chưa đăng nhập."""
    path = token_file or TOKEN_FILE
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json(), encoding="utf-8")
    return creds if creds and creds.valid else None


def require_credentials() -> Credentials:
    """Trả credentials hoặc raise RuntimeError nếu chưa đăng nhập."""
    creds = load_oauth2_credentials(TOKEN_FILE)
    if creds:
        return creds
    raise RuntimeError(
        "❌ Chưa đăng nhập Google.\n"
        "Nhấn nút 'Đăng nhập tài khoản' trong app để xác thực."
    )


def build_service(credentials: Credentials, name: str, version: str):
    """Tạo Google API service với AuthorizedHttp và timeout."""
    http = AuthorizedHttp(credentials, http=httplib2.Http(timeout=60))
    return build(name, version, http=http, cache_discovery=False)


# ─── Router ──────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/auth", tags=["auth"])

_login_lock = threading.Lock()


@router.get("/status", response_model=AuthStatus)
def auth_status() -> AuthStatus:
    """Kiểm tra trạng thái đăng nhập, email và tên tài khoản."""
    creds = load_oauth2_credentials(TOKEN_FILE)
    if not (creds and creds.valid):
        return AuthStatus(logged_in=False, message="Chưa đăng nhập")

    email: str | None = None
    name:  str | None = None
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        id_token = data.get("id_token")
        if id_token:
            payload_b64 = id_token.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            email = payload.get("email")
            name  = payload.get("name") or payload.get("given_name")
    except Exception:
        pass

    return AuthStatus(logged_in=True, email=email, name=name, message="Đã đăng nhập")


@router.post("/login", response_model=LoginResult)
async def auth_login() -> LoginResult:
    """Mở trình duyệt để đăng nhập / đổi tài khoản mới.

    Chạy OAuth flow trong thread nội bộ — không cần subprocess Python riêng,
    tương thích với cả môi trường PyInstaller bundle lẫn dev.
    """
    if not CLIENT_SECRETS_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Không tìm thấy client_secrets.json (tìm tại: {CLIENT_SECRETS_FILE}).\n"
                "Liên hệ nhà phát triển để được cung cấp phiên bản app đúng."
            ),
        )

    def _run_flow() -> None:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRETS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except Exception as exc:
            # Lỗi ghi vào log nhưng không crash backend
            print(f"[auth] OAuth flow error: {exc}", flush=True)

    with _login_lock:
        # Hủy thread cũ nếu còn đang chạy (đặt flag daemon để tự kết thúc)
        t = threading.Thread(target=_run_flow, daemon=True, name="oauth-flow")
        t.start()

    return LoginResult(
        status="started",
        message="Đã mở trình duyệt. Đăng nhập tài khoản Google rồi quay lại app.",
    )


@router.delete("/token")
def auth_logout() -> dict[str, str]:
    """Xóa token.json — đăng xuất tài khoản hiện tại."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        return {"status": "ok", "message": "Đã xóa token. Tài khoản đã được đăng xuất."}
    return {"status": "ok", "message": "Không có token để xóa."}
