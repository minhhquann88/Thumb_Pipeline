# Thumb Pipeline Desktop

Thumb Pipeline Desktop là một ứng dụng máy tính đa nền tảng (sử dụng Tauri cho giao diện và Python FastAPI cho xử lý logic). Ứng dụng này giúp tự động hóa quy trình lấy video từ Google Drive, trích xuất hình ảnh thu nhỏ (thumbnail) bằng FFmpeg, sau đó tải ảnh lên lại Google Drive và cập nhật đường dẫn (URL) vào Google Sheet.

## 🌟 Tính năng chính

- **Giao diện trực quan**: Frontend được thiết kế hiện đại bằng HTML/CSS/JS, build và đóng gói siêu nhẹ nhờ Tauri.
- **Xử lý ngầm mạnh mẽ**: Backend Python FastAPI chịu trách nhiệm giao tiếp với Google APIs, chạy đa luồng (workers) để tăng tốc độ.
- **Tự động hóa Google Sheet & Drive**: Đọc danh sách video từ Sheet, tự động upload ảnh thumbnail lên thư mục trên Drive và ghi link trở lại Sheet một cách chính xác.
- **Xử lý FFmpeg linh hoạt**: Hỗ trợ chụp nhiều khung hình (timestamps) từ video.
- **Bảo mật**: Xác thực với Google thông qua quy trình OAuth2 thủ công an toàn (`client_secrets.json`).

## 📂 Cấu trúc thư mục

```text
.
├── backend/                # Source code Python FastAPI backend
├── frontend/               # Mã nguồn giao diện tĩnh (HTML/CSS/JS)
├── src-tauri/              # Source code Tauri (Rust) để build desktop shell
├── tools/                  # Chứa các file thực thi nhị phân ngoài (ví dụ: ffmpeg.exe)
├── build_release.bat       # Script tự động build đóng gói ứng dụng (cho Windows)
├── backend_server.spec     # File cấu hình PyInstaller để đóng gói backend
└── package.json            # Quản lý dependencies cho Node.js và script chạy Tauri
```

## 💻 Yêu cầu hệ thống

Trước khi bắt đầu, đảm bảo máy tính của bạn đã cài đặt các công cụ sau:
- **Node.js**: (Khuyến nghị bản LTS) để chạy các script của Tauri và quản lý frontend.
- **Python**: Phiên bản 3.10 trở lên.
- **Rust**: Để build Tauri app (Cài đặt thông qua rustup).
- **FFmpeg**: Công cụ xử lý video.

## 🚀 Hướng dẫn cài đặt môi trường

### 1. Cài đặt các thư viện Node.js và Python

Mở terminal/PowerShell tại thư mục gốc của dự án và chạy lần lượt các lệnh sau:

```powershell
# Cài đặt dependencies cho Tauri/Frontend
npm install

# Tạo môi trường ảo Python (Virtual Environment)
python -m venv .venv

# Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1   # (Hoặc .\.venv\Scripts\activate.bat trên CMD)

# Cài đặt dependencies cho Backend
pip install -r backend\requirements.txt
```

### 2. Cài đặt FFmpeg

1. Tải FFmpeg bản build cho Windows tại [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (Khuyên dùng bản `ffmpeg-release-essentials.zip`).
2. Giải nén và copy 2 file `ffmpeg.exe` và `ffprobe.exe` (nằm trong thư mục `bin`) vào thư mục `tools/` của dự án (Tạo thư mục `tools` nếu chưa có).

*Lưu ý: Các file `.exe` trong thư mục `tools/` đã được thiết lập để bỏ qua (ignore) khi push lên Git, tránh làm nặng repository.*

### 3. Thiết lập Google API Credentials

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Tạo một Project mới hoặc chọn Project hiện có.
3. Bật (Enable) 2 APIs: **Google Sheets API** và **Google Drive API**.
4. Vào mục **APIs & Services > Credentials**:
   - Nhấn **Create Credentials** > **OAuth client ID**.
   - Chọn Application type là **Desktop app**.
   - Tải file JSON về và đổi tên thành `client_secrets.json`.
   - Đặt file `client_secrets.json` vào thư mục gốc của dự án. (File này cũng đã được bỏ qua trong `.gitignore`).

## 🛠 Hướng dẫn chạy Development (Chế độ phát triển)

### Chạy Backend độc lập (để test API)
Kích hoạt môi trường ảo và khởi chạy Uvicorn:
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765
```
Kiểm tra API có hoạt động không bằng cách truy cập: `http://127.0.0.1:8765/health`

### Chạy Giao diện Desktop (Tauri)
Đảm bảo bạn đang ở môi trường ảo (để Tauri có thể gọi đúng phiên bản Python), sau đó chạy:
```powershell
npm run dev
```
Khi ứng dụng mở lên, Tauri sẽ tự động khởi chạy backend Python ngầm.

## 📦 Hướng dẫn Build Release (Đóng gói ứng dụng)

Dự án có cung cấp sẵn script `build_release.bat` để tự động hóa hoàn toàn quá trình đóng gói cho Windows.

```powershell
.\build_release.bat
```

Script này sẽ tự động thực hiện các bước:
1. Kiểm tra sự hiện diện của `ffmpeg.exe` và `ffprobe.exe` trong `tools/`.
2. Đóng gói Backend Python thành file thực thi duy nhất bằng **PyInstaller** (`backend_server.exe`).
3. Build ứng dụng Desktop bằng **Tauri** (`npm run build`).
4. Gom tất cả các file cần thiết (Tauri exe, Python backend exe, FFmpeg, client_secrets.json) vào chung một thư mục.

Sau khi quá trình hoàn tất, thư mục phân phối cuối cùng sẽ nằm tại:
```text
src-tauri\target\release\
```

Bạn chỉ cần nén (zip) nội dung bên trong thư mục này và chia sẻ cho người dùng. Họ có thể chạy ứng dụng trực tiếp bằng file `.exe` mà không cần cài đặt Python hay Node.js.

## 📖 Hướng dẫn sử dụng trên UI

1. **Xác thực Google**: 
   - Ứng dụng hiện tại sử dụng cơ chế đăng nhập thủ công an toàn. Bạn cần chuẩn bị sẵn file `client_secrets.json` của Google Cloud Console đặt cùng thư mục với file `.exe` (hoặc ở root project).
   - Trên UI, bấm vào nút lấy URL đăng nhập, trình duyệt sẽ mở. Đăng nhập và lấy Localhost URL hoặc Authorization Code rồi dán vào ô xác nhận để kết nối.
2. **Cấu hình Pipeline**:
   - `Spreadsheet ID`: ID của Google Sheet (nằm giữa `.../d/` và `/edit` trên thanh địa chỉ trình duyệt). Ứng dụng sẽ tự động validate ID này.
   - `Sheet name`: Tên tab chứa dữ liệu.
   - `Video URL Column` / `Thumbnail Column`: Index của cột chứa link Drive video đầu vào và cột xuất link ảnh. (A=1, B=2, C=3, D=4...)
   - `Timestamps (s)`: Danh sách các giây trong video cần cắt ảnh, cách nhau bằng dấu phẩy (VD: `5, 10, 15`).
   - `Max Workers`: Số lượng tác vụ lấy thumbnail xử lý đồng thời.
3. Nhấn **Chạy Pipeline** để hệ thống tự động xử lý. Bạn có thể theo dõi tiến độ qua thanh trạng thái. Bạn cũng có thể dọn dẹp các đường link cũ bằng công cụ **Clear Thumbnail Column**.
