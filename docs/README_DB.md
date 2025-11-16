# Tích Hợp Cơ Sở Dữ Liệu (MySQL qua XAMPP)

## 1. Mục tiêu
- Lưu trữ người dùng, metadata file, phiên upload, thống kê theo ngày.
- Chuẩn bị nền tảng mở rộng sang HTTP/REST (FastAPI) hoặc các giao thức khác.

## 2. Yêu cầu
- Đã bật MySQL trong XAMPP (mặc định port 3306)
- Python 3.11+
- Cài đặt package:
```powershell
pip install -r requirements.txt
```

## 3. Khởi Tạo Database
Vào phpMyAdmin hoặc dùng terminal:
```sql
CREATE DATABASE fileupload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fileupload;
-- Import nội dung từ models.sql
```
Hoặc:
```powershell
mysql -u root -p < database/models.sql
```
(Mặc định root password trống trong XAMPP)

**Lưu ý:** Hệ thống chuẩn hóa Guest là `user_id=1` (trước đây 0, đã thống nhất lại). Nếu script cũ còn ghi 0 bạn có thể cập nhật thủ công:
```sql
UPDATE users SET user_id=1 WHERE username='Guest';
```

## 4. Cấu Hình
File: `database/config.py`
Có thể override bằng biến môi trường:
```powershell
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="3306"
$env:DB_USER="root"
$env:DB_PASSWORD=""
$env:DB_NAME="fileupload"
$env:ENABLE_DB="true"
```

## 5. Kiến Trúc Tầng
```
server/server.py ──(tùy chọn gọi DB)──▶ database/db_manager.py ──▶ MySQL
                                 ▲
                                 │
                         services/*.py (phục vụ HTTP/REST)
```

## 6. Các Bảng Chính
- `users`: thông tin người dùng / có thể thêm quota
- `files`: metadata file + trạng thái hiện tại
- `upload_sessions`: nhật ký từng phiên upload (bắt đầu/kết thúc)
- `statistics_daily`: tổng hợp theo ngày (số upload, bytes, active users)

## 7. Quy Trình Hoạt Động (TCP Upload)
1. Client gửi metadata → server tạo bản ghi file & session (nếu DB bật)
2. Server nhận từng chunk → ghi xuống thư mục `uploads/`
3. Hoàn tất → cập nhật `status=success`, finalize phiên, ghi thống kê ngày
4. Lỗi / gián đoạn → `status=error`, finalize kèm `error_message`

## 8. HTTP/REST (Đã Tích Hợp)
- `POST /api/register` – đăng ký user mới
- `POST /api/login` – xác thực, trả về `user_id`
- `POST /api/upload` – upload (HTTP, không ghi file xuống đĩa, chỉ thống kê)
- `GET /api/files?user_id=` – liệt kê file của user
- `GET /api/stats` – thống kê tổng
- `GET /api/health` – tình trạng hệ thống

## 9. Backup & Khôi Phục
- Backup: `mysqldump -u root fileupload > backup.sql`
- Khôi phục: `mysql -u root fileupload < backup.sql`

## 10. Bảo Mật (Định Hướng)
- Hash mật khẩu hiện dùng SHA-256 → nên nâng cấp bcrypt/argon2 để chống rainbow table.
- Thêm JWT cho phiên đăng nhập thay vì chỉ trả `user_id`.
- Có thể thêm refresh token nếu triển khai session dài.

## 11. Kiểm Thử Nhanh
```python
from database.db_manager import DB
uid = DB.register_user("demo","secret")
assert DB.authenticate("demo","secret") == uid
print(DB.get_stats())
```

## 12. Sự Cố Thường Gặp
| Vấn đề | Nguyên nhân | Khắc phục |
|--------|-------------|-----------|
| Cannot connect | MySQL chưa chạy | Bật MySQL trong XAMPP |
| Access denied | Sai user/password | Kiểm tra biến môi trường / `config.py` |
| Unknown database | Chưa tạo DB | Tạo bằng `CREATE DATABASE fileupload` |
| Table missing | Chưa import schema | Import `models.sql` |
| Guest id sai | Script cũ dùng 0 | Update thành 1 trong bảng `users` |

## 13. Mở Rộng Dự Kiến
- Thêm bảng `downloads` (log lượt tải – nếu cần sau này)
- Thêm bảng `api_tokens` (tạo khoá truy cập dịch vụ khác)
- Soft delete cho `files` (đánh dấu thay vì xoá vật lý)
- Quota per user (dung lượng tối đa / số file / tốc độ)

---
Trạng thái hiện tại: Guest chuẩn hóa `user_id=1`, hệ thống lưu đầy đủ metadata upload TCP và session. Nếu cần thêm tải xuống hoặc checksum toàn vẹn có thể bổ sung sau.


