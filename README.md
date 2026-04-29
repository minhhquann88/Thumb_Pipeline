# Thumb Pipeline Desktop

Desktop app mẫu dùng Tauri cho shell desktop, HTML/CSS/JS cho giao diện, và Python FastAPI làm backend local.

## Cấu trúc

```text
.
├── backend/              # Python FastAPI backend
├── frontend/             # Frontend static HTML/CSS/JS bundled by Tauri
├── src/                  # Legacy copy of frontend CSS/JS
├── src-tauri/            # Tauri Rust shell
├── index.html            # Static frontend
├── package.json          # Tauri CLI scripts
└── thumb_pipeline_colab.py
```

## Cài đặt

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

Nếu muốn Tauri dùng đúng virtualenv khi chạy dev, mở terminal đã activate venv trước:

```powershell
.\.venv\Scripts\Activate.ps1
npm run dev
```

## Chạy backend riêng để test

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Kiểm tra API:

```powershell
Invoke-RestMethod http://127.0.0.1:8765/health
```

## Chạy desktop app

```powershell
npm run dev
```

Khi app mở, Tauri sẽ chạy lệnh sau để bật backend:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

## Chạy pipeline thật

Backend desktop không dùng được `google.colab.auth`, nên app dùng Google Service Account.

Chuẩn bị:

- Tạo Google Cloud service account và tải JSON key.
- Đặt file JSON ở project root với tên mặc định `service-account.json`, hoặc nhập path khác trong UI.
- Share Google Sheet cho email `client_email` trong JSON với quyền edit.
- Share các video Drive cho service account, hoặc để service account có quyền truy cập vào folder chứa video.
- Cài `ffmpeg` và đảm bảo `ffmpeg`/`ffprobe` có trong `PATH`.

Trong UI:

- `Spreadsheet ID`: ID của Google Sheet.
- `Sheet name`: tab sheet, mặc định `Sheet1`.
- `Video URL column`: index cột video URL, mặc định `3` nghĩa là cột D.
- `Thumbnail column`: index cột ghi link thumbnail, mặc định `14` nghĩa là cột O.
- `Timestamps`: danh sách giây cần chụp, ví dụ `3,8,13,18,23`.
- `Workers`: số video xử lý song song.

Pipeline sẽ đọc Sheet, bỏ qua dòng đã có thumbnail, tải video từ Drive, extract thumbnail bằng ffmpeg, upload ảnh lên Drive folder `thumbnails`, public ảnh và ghi link vào cột thumbnail.

## Build

```powershell
npm run build
```

File `.exe` sau build nằm tại:

```text
src-tauri\target\release\thumb-pipeline-desktop.exe
```

Installer MSI đang tắt trong `src-tauri/tauri.conf.json` bằng `bundle.active = false` vì project chưa có icon `.ico`. Khi cần đóng gói installer, thêm icon hợp lệ rồi bật lại `bundle.active`.

## API backend

- `GET /health`: kiểm tra backend.
- `POST /jobs`: tạo job pipeline chạy nền.
- `GET /jobs/{job_id}`: xem status, logs và kết quả job.
