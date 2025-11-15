# Hướng Dẫn Sử Dụng Hệ Thống Upload Đa Giao Thức

> Phiên bản: Week 7 (TCP + UDP + HTTP/HTTPS + Multicast + Database)
> Ngôn ngữ triển khai: Python 3.11

## 1. Tổng Quan
Hệ thống hỗ trợ nhiều giao thức để truyền và giám sát upload file:
- TCP: Truyền file chính, ghi nhận metadata (không lưu nội dung file vào ổ đĩa nếu dùng chế độ metadata-only).
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
- Upload qua TCP (gửi metadata + nội dung tuỳ chế độ)
- Hiển thị progress bar
- Hiển thị trạng thái kết nối

## 6. REST API Endpoints (HTTP)
Ví dụ (giả định đã triển khai trong `http_app.py`):
- `POST /register` – Đăng ký user mới
- `POST /login` – Đăng nhập, trả về token (nếu có)
- `POST /upload` – Upload file đơn giản (metadata-only hoặc full)
- `GET /files` – Liệt kê file đã upload
- `GET /stats` – Thống kê tổng
- `GET /health` – Kiểm tra tình trạng

Test nhanh bằng `curl`:
```powershell
curl http://127.0.0.1:8000/health
```

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

## 9. Chế Độ Metadata-Only
Trong chế độ này, nội dung file không được ghi xuống thư mục `uploads/`, chỉ lưu metadata vào DB:
- Giảm IO
- Phục vụ demo logic truyền & xử lý

## 10. Quy Trình Upload (TCP)
1. Client chọn file -> đưa vào hàng đợi
2. Thread manager lấy file từ queue
3. Kết nối TCP tới server
4. Gửi header (user_id, filename, size, checksum nếu có)
5. Gửi nội dung (hoặc bỏ qua nếu metadata-only)
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
| Upload không ghi file | Đang ở chế độ metadata-only | Đổi config nếu cần lưu file |

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


