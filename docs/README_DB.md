# Database Integration (MySQL via XAMPP)

## 1. Mục tiêu
- Lưu trữ người dùng, file metadata, phiên upload, thống kê hàng ngày.
- Sẵn sàng mở rộng sang HTTP/REST (FastAPI) hoặc WebSocket.

## 2. Yêu cầu
- XAMPP MySQL đang chạy (port mặc định 3306)
- Python 3.11+
- Cài đặt package:
```bash
pip install -r requirements.txt
```

## 3. Tạo Database
Vào phpMyAdmin hoặc dùng terminal:
```sql
CREATE DATABASE fileupload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fileupload;
-- Import models.sql nội dung
```
Hoặc từ terminal:
```bash
mysql -u root -p < database/models.sql
```
(Mặc định XAMPP root password rỗng)

**Lưu ý:** Script `models.sql` tự động tạo Guest user (user_id=0) để hỗ trợ anonymous uploads.

## 4. Cấu hình
File: `database/config.py`
- Sử dụng biến môi trường để override:
```bash
set DB_HOST=127.0.0.1
set DB_PORT=3306
set DB_USER=root
set DB_PASSWORD=
set DB_NAME=fileupload
set ENABLE_DB=true
```

## 5. Kiến trúc Layer
```
server/server.py ──(optional DB calls)──▶ database/db_manager.py ──▶ MySQL
                                 ▲
                                 │
                         services/*.py (dùng cho HTTP/REST về sau)
```

## 6. Các bảng chính
- users: thông tin người dùng / quota
- files: metadata file + trạng thái
- upload_sessions: log quá trình upload
- statistics_daily: thống kê ngày

## 7. Các bước hoạt động (server)
1. Client gửi metadata → server tạo record (files + session)
2. Server nhận chunk → cập nhật tiến độ nội bộ
3. Hoàn tất → cập nhật status=success, finalize session
4. Lỗi hoặc gián đoạn → status=error, finalize với error_message

## 8. Mở rộng HTTP/REST sau này
- Endpoint: POST /login → xác thực (services.user_service.authenticate_user)
- Endpoint: POST /upload (multipart) → lưu file; ghi file record & session
- Endpoint: GET /files → list files theo user
- Endpoint: GET /stats → thống kê tổng quát

## 9. Backup & Migration
- Dump dữ liệu: `mysqldump -u root fileupload > backup.sql`
- Phục hồi: `mysql -u root fileupload < backup.sql`

## 10. Bảo mật (tương lai)
- Hash mật khẩu: SHA-256 hiện tại; nên nâng cấp bcrypt/argon2
- Thêm JWT tokens (bước HTTP layer)
- Thêm column refresh_token nếu cần session dài

## 11. Kiểm thử nhanh
```python
from database.db_manager import DB
uid = DB.register_user("demo","secret")
assert DB.authenticate("demo","secret") == uid
print(DB.get_stats())
```

## 12. Troubleshooting
| Issue | Nguyên nhân | Giải pháp |
|-------|-------------|-----------|
| Cannot connect | MySQL chưa chạy | Khởi động XAMPP MySQL |
| Access denied | Sai user/pass | Kiểm tra config.py / env |
| Unknown database | Chưa tạo DB | Chạy câu lệnh CREATE DATABASE |
| Table missing | Chưa import schema | Import models.sql |

## 13. Kế hoạch mở rộng
- Thêm bảng downloads (log mỗi lượt tải)
- Thêm bảng api_tokens (token truy cập dịch vụ ngoài)
- Thêm cơ chế soft delete cho files

---
**Version:** 1.0  
**Date:** 2025-11-15  
**Author:** GitHub Copilot
