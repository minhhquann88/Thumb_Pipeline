# backend_server.spec
# ───────────────────
# Cấu hình PyInstaller để đóng gói Python backend thành backend_server.exe
#
# Chạy: pyinstaller backend_server.spec
# Output: dist/backend_server/ (thư mục chứa .exe + thư viện)

from pathlib import Path

ROOT = Path(SPECPATH)  # thư mục chứa file .spec này (= project root)

# ── Các module uvicorn/fastapi bị PyInstaller bỏ sót ──────────────────────────
hidden_imports = [
    # uvicorn internals
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # fastapi + middleware (hay bị miss nhất)
    "fastapi",
    "fastapi.middleware",
    "fastapi.middleware.cors",
    "fastapi.responses",
    "fastapi.routing",
    "fastapi.encoders",
    "fastapi.exception_handlers",
    "fastapi.exceptions",
    # starlette (fastapi dùng bên dưới)
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.middleware.base",
    "starlette.routing",
    "starlette.responses",
    "starlette.requests",
    "starlette.background",
    "starlette.concurrency",
    "starlette.datastructures",
    "starlette.exceptions",
    "starlette.formparsers",
    "starlette.status",
    "starlette.types",
    "starlette.websockets",
    "starlette.testclient",
    # anyio backends
    "anyio",
    "anyio._backends._asyncio",
    "anyio._backends._trio",
    "anyio.streams.memory",
    "anyio.to_thread",
    # google api (dung dong nen PyInstaller khong detect duoc)
    "googleapiclient",
    "googleapiclient.discovery",
    "googleapiclient.http",
    "googleapiclient.errors",
    "googleapiclient.model",
    "googleapiclient.schema",
    "googleapiclient.channel",
    "googleapiclient.iam",
    "googleapiclient._helpers",
    "googleapiclient.discovery_cache",
    "googleapiclient.discovery_cache.base",
    "googleapiclient.discovery_cache.file_cache",
    "google.auth",
    "google.auth.transport",
    "google.auth.transport.requests",
    "google.auth.transport.urllib3",
    "google.oauth2",
    "google.oauth2.credentials",
    "google.oauth2.service_account",
    "google_auth_httplib2",
    "google_auth_oauthlib",
    "google_auth_oauthlib.flow",
    "httplib2",
    # email parser (dùng bởi httplib2)
    "email.mime.multipart",
    "email.mime.text",
    "email.mime.base",
    # pydantic
    "pydantic",
    "pydantic.v1",
    "pydantic_core",
    # h11
    "h11",
    "h11._connection",
    "h11._events",
    "h11._readers",
    "h11._state",
    "h11._writers",
]

# ── Dữ liệu đóng gói vào bundle ───────────────────────────────────────────────
datas = [
    # client_secrets.json — file định danh app OAuth2
    (str(ROOT / "client_secrets.json"), "."),
    # backend package (source code Python)
    (str(ROOT / "backend"), "backend"),
    # ffmpeg + ffprobe executables
    (str(ROOT / "tools" / "ffmpeg.exe"), "."),
    (str(ROOT / "tools" / "ffprobe.exe"), "."),
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "backend_server_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Loại bỏ những thứ không cần để giảm size
        "tkinter",
        "matplotlib",
        "numpy",
        "PIL",
        "scipy",
        "pandas",
        "IPython",
        "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="backend_server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,            # nén để giảm size (cần cài UPX hoặc bỏ dòng này)
    console=True,        # True để xem log lỗi khi debug; đổi False khi release
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="backend_server",
)
