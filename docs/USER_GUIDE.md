# Hướng Dẫn Sử Dụng Hệ Thống Upload Đa Giao Thức

> Phiên bản: Week 7 (TCP + UDP + HTTP/HTTPS + Multicast + Database)
> Ngôn ngữ triển khai: Python 3.11

## 1. Tổng Quan
 Hệ thống hỗ trợ nhiều giao thức để truyền và giám sát upload file:
- TCP: Truyền file chính và ghi file thực tế xuống thư mục `uploads/` (đồng thời ghi metadata vào DB nếu bật DB).
- HTTP/HTTPS (FastAPI): REST API cho đăng ký, đăng nhập, upload đơn giản, thống kê.
- UDP: Khám phá server (discovery), heartbeat, quảng bá cổng dịch vụ.
- Multicast: Giám sát real-time trạng thái server (tuân thủ syllabus tuần 7).
- MySQL Database: Lưu metadata file, user, thống kê.

## 2. Cấu Trúc Thư Mục
```
server/
  run_combined.py        # Runner tích hợp
  server_config.py       # Config trung tâm
  shared_state.py        # State chia sẻ
  server.py              # TCP server
  udp_server.py          # UDP server
  http_server.py         # FastAPI HTTP server
  http_app.py            # Ứng dụng FastAPI
  multicast_monitor.py   # Broadcast multicast stats
  multicast_dashboard.py # Dashboard nhận stats
 client/
  main.py                # GUI client (Tkinter)
  uploader/              # logic upload TCP
  async_controller/      # quản lý luồng
  file_manager/          # hàng đợi & xử lý file
  gui/                   # giao diện chính & progress bar
```

## 3. Chuẩn Bị Môi Trường
### 3.1. Cài đặt package
```powershell
pip install -r requirements.txt
```
### 3.2. MySQL (XAMPP)
- Bật MySQL trong XAMPP.
- Tạo database: `fileupload`
- Bảng sẽ được tạo tự động nếu logic đã triển khai (users, files).
- Tài khoản mặc định: user=`root`, password trống.

### 3.3. Config qua biến môi trường (tùy chọn)
```powershell
$env:ENABLE_DB="true"
$env:ENABLE_UDP="true"
$env:ENABLE_MULTICAST="true"
```
Hoặc chỉnh trực tiếp trong `server/server_config.py`.

## 4. Khởi Chạy Hệ Thống Tích Hợp
Chạy tất cả dịch vụ trong một tiến trình:
```powershell
$env:ENABLE_DB="true"; $env:ENABLE_UDP="true"; $env:ENABLE_MULTICAST="true"; python -m server.run_combined
```
Dịch vụ sẽ khởi chạy:
- TCP: `127.0.0.1:9999`
- HTTP API: `http://127.0.0.1:8000`
- UDP: Port `9998`
- Multicast: Group `239.0.0.1:5555`

## 5. Sử Dụng Client GUI
Chạy client:
```powershell
python -m client.main
```
 Chức năng:
 - Chọn file -> đẩy vào hàng đợi
 - Upload qua TCP (gửi metadata + nội dung)
 - Hiển thị progress bar
 - Hiển thị trạng thái kết nối

## 6. REST API Endpoints (HTTP)
Ví dụ (đã triển khai trong `http_app.py`):
- `POST /register` – Đăng ký user mới
- `POST /login` – Đăng nhập, trả về token (nếu có)
- `POST /upload` – Upload file đơn giản (ghi nội dung xuống `uploads/`)
- `GET /files` – Liệt kê file đã upload
- `GET /stats` – Thống kê tổng
- `GET /health` – Kiểm tra tình trạng

Test nhanh bằng `curl`:
```powershell
curl http://127.0.0.1:8000/health
```

### 6.1. Test nhanh bằng curl
```powershell
# Health
curl http://127.0.0.1:8000/api/health

# Upload file (DB tắt: chỉ đo và trả metadata; DB bật: ghi metadata vào DB)
curl -F "file=@path\to\file.txt" -F "user_id=1" http://127.0.0.1:8000/api/upload

# Danh sách file (cần DB bật)
curl "http://127.0.0.1:8000/api/files?user_id=1"

# Thống kê (DB tắt sẽ trả 0/0)
curl http://127.0.0.1:8000/api/stats
```

### 6.2. Chạy test HTTP tự động
Đã thêm test tự động sử dụng FastAPI TestClient.

```powershell
$env:PYTHONPATH="."; python -m unittest -v tests.test_http_api
```
Test bao gồm:
- `/api/health` trả `status=ok`
- `/api/upload` nhận file thành công khi DB tắt
- `/api/files` trả `503` khi DB tắt
- `/api/stats` trả `0/0` khi DB tắt

## 7. UDP Discovery & Heartbeat
Nếu `ENABLE_UDP=true`:
- Server gửi gói UDP quảng bá thông tin cổng dịch vụ.
- Client (nếu có logic lắng nghe) có thể tự động tìm server mà không cần nhập tay.

## 8. Multicast Monitoring
Dashboard real-time:
```powershell
python -m server.multicast_dashboard
```
Hiển thị:
- Số kết nối đang active
- Tổng số file session
- Tổng số bytes session
- Thống kê database (tổng file, tổng dung lượng)
- Uptime server
- Trạng thái (READY/BUSY)

## 9. Lưu File Thực Tế
Mặc định, server ghi toàn bộ nội dung file xuống thư mục `uploads/` ở thư mục gốc dự án:
- Đường dẫn: `d:\\LTM\\nhomltmck\\uploads` (Windows) hoặc `./uploads/`
- Metadata file (tên, kích thước, mime, trạng thái, user, session) vẫn được lưu vào DB nếu bật `ENABLE_DB`.

Lưu ý: Nếu bạn chạy server từ thư mục khác, hãy kiểm tra current working directory để đảm bảo đường dẫn `uploads/` đúng vị trí mong muốn.

## 10. Quy Trình Upload (TCP)
1. Client chọn file -> đưa vào hàng đợi
2. Thread manager lấy file từ queue
3. Kết nối TCP tới server
4. Gửi header (user_id, filename, size, checksum nếu có)
5. Gửi nội dung
6. Server cập nhật `upload_stats` + ghi vào DB nếu bật

## 11. Bật/Tắt Tính Năng Nhanh
```powershell
# Tắt multicast
$env:ENABLE_MULTICAST="false"; python -m server.run_combined
# Tắt UDP
$env:ENABLE_UDP="false"; python -m server.run_combined
# Chỉ chạy TCP + HTTP
$env:ENABLE_DB="true"; python -m server.run_combined
```

## 12. Xử Lý Lỗi Phổ Biến
| Lỗi | Nguyên nhân | Khắc phục |
|-----|-------------|-----------|
| Cannot connect TCP | Server chưa chạy | Chạy `run_combined` trước |
| JSON Decimal error | Kiểu Decimal từ DB | Đã fix trong `multicast_monitor.py` |
| MySQL access denied | Sai user/password | Kiểm tra cấu hình XAMPP |
| Dashboard không nhận multicast | TTL hoặc group sai | Dùng group `239.0.0.1`, TTL >=2 |
| Không thấy file trong uploads | Chạy sai thư mục hoặc quyền ghi | Kiểm tra working dir và quyền ghi vào `uploads/` |

## 13. Demo Nhanh (Gợi Ý)
1. Mở 2 terminal: Server + Multicast Dashboard.
2. Mở client GUI, upload vài file nhỏ.
3. Quan sát dashboard tăng số file và dung lượng.
4. Gọi API `/stats` để đối chiếu.

## 14. Mở Rộng Tương Lai
- Thêm xác thực JWT chuẩn cho HTTP.
- Lưu nội dung file lên object storage (MinIO/S3).
- Thêm gRPC làm kênh streaming song song.
- Phân cụm (cluster) nhiều server multicast.

## 15. Thông Tin Khác
- Guest user có `user_id=1`.
- Thư mục `backup_YYYYMMDD_*` chứa version cũ (có thể xóa nếu gọn nhẹ).
- Tất cả cấu hình quan trọng trong `server_config.py`.


