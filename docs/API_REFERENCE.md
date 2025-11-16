# 📘 Tài Liệu API HTTP Upload

Phiên bản: 1.0.0  
Server: FastAPI  
Phạm vi: Chỉ cung cấp chức năng upload và thống kê (không có tải xuống).  

## 🔑 Tổng Quan
- Cơ chế xác thực đơn giản (register/login) qua DB; khi DB tắt dùng Guest user (user_id=1).
- Upload qua HTTP KHÔNG ghi file ra đĩa (metadata-only). Việc ghi file thực tế hiện được thực hiện ở giao thức TCP.
- Khi `ENABLE_DB=false` các endpoint phụ thuộc DB trả mã lỗi 503 hoặc trả về dữ liệu mặc định.

## 🌐 Base URL
Ví dụ chạy cục bộ: `http://127.0.0.1:8000` (tùy cấu hình uvicorn nếu có). Trong project này dùng module trực tiếp nên mặc định host/port của FastAPI runner.

Tất cả endpoint dưới đây đều tiền tố `/api`.

## 🧪 Trạng Thái & Hệ Thống
### GET `/api/health`
Mô tả: Kiểm tra tình trạng API, trạng thái DB, và (nếu có) thông tin TCP server tích hợp.

Phản hồi 200:
```json
{
  "status": "ok",
  "db_enabled": false,
  "tcp": {
    "host": "127.0.0.1",
    "port": 9999,
    "active_connections": 2,
    "total_files": 15,
    "total_bytes": 131621888
  }
}
```

Trường `tcp` có thể là `null` hoặc `{ "error": "unavailable" }` nếu TCP server chưa sẵn sàng.

## 👤 Người Dùng
### POST `/api/register`
Mô tả: Tạo tài khoản mới (chỉ hoạt động khi DB bật).  
Body JSON:
```json
{ "username": "alice", "password": "secret123" }
```
Phản hồi 200:
```json
{ "user_id": 5, "username": "alice" }
```
Lỗi:
- 400: Trùng tên hoặc sai định dạng.
- 503: DB tắt.

### POST `/api/login`
Mô tả: Đăng nhập lấy `user_id`. Khi DB tắt trả về Guest (`user_id=1`).  
Body JSON:
```json
{ "username": "alice", "password": "secret123" }
```
Phản hồi 200 (DB bật):
```json
{ "user_id": 5, "username": "alice" }
```
Phản hồi 200 (DB tắt):
```json
{ "user_id": 1, "username": "Guest" }
```
Lỗi:
- 401: Sai thông tin đăng nhập.
- 500: Lỗi hệ thống.

## 📤 Upload
### POST `/api/upload`
Mô tả: Upload 1 file dạng multipart/form-data. Chỉ ghi nhận kích thước, không lưu file vào đĩa ở giao thức HTTP.  
Form fields:
- `user_id`: số (mặc định 0 nếu không gửi; nên gửi 1 khi dùng Guest).
- `file`: tệp tin cần upload.

Ví dụ curl:
```bash
curl -X POST http://127.0.0.1:8000/api/upload \
  -F "user_id=1" \
  -F "file=@d:/LTM/nhomltmck/sample.txt"
```

Phản hồi (DB tắt):
```json
{
  "status": "success",
  "filename": "sample.txt",
  "bytes": 10240,
  "seconds": 0.0123,
  "mbps": 0.81,
  "stored": false
}
```

Phản hồi (DB bật):
```json
{
  "status": "success",
  "file_id": 42,
  "session_id": 77,
  "filename": "sample.txt",
  "bytes": 10240,
  "seconds": 0.0123,
  "mbps": 0.81,
  "stored": false
}
```
Lỗi:
- 500: Lỗi ghi nhận metadata hoặc DB.

## 📂 Danh Sách File
### GET `/api/files`
Tham số query: `user_id`  
Mô tả: Trả danh sách file thuộc user (chỉ khi DB bật).  
Ví dụ: `GET /api/files?user_id=5`

Phản hồi 200:
```json
{ "user_id": 5, "files": [ {"file_id": 42, "filename": "sample.txt", "size": 10240} ] }
```
Lỗi:
- 503: DB tắt.
- 500: Lỗi hệ thống.

## 📈 Thống Kê
### GET `/api/stats`
Mô tả: Trả về tổng số file và tổng số bytes (aggregate).  
Phản hồi (DB bật):
```json
{ "total_files": 150, "total_bytes": 9126805504 }
```
Phản hồi (DB tắt):
```json
{ "total_files": 0, "total_bytes": 0 }
```
Lỗi:
- 500: Lỗi hệ thống.

## 🛡️ Mã Trạng Thái Tổng Hợp
| Mã | Ý nghĩa |
|----|---------|
| 200 | Thành công |
| 400 | Dữ liệu không hợp lệ (ví dụ đăng ký trùng) |
| 401 | Sai thông tin đăng nhập |
| 500 | Lỗi hệ thống nội bộ |
| 503 | Dịch vụ tạm thời không khả dụng (DB tắt) |

## 🔐 Ghi Chú Bảo Mật
- Hiện tại mật khẩu được băm (SHA-256) ở tầng dịch vụ, chưa có JWT.
- Nên thêm HTTPS reverse proxy nếu triển khai thực tế.
- User Guest dùng id=1 khi DB tắt (không cần đăng ký/login).

## 🔄 Khác Biệt So Với TCP
| Tiêu chí | HTTP Upload | TCP Upload |
|----------|-------------|------------|
| Lưu file vật lý | Không | Có (ghi vào thư mục uploads/) |
| Dùng session DB | Có (khi DB bật) | Có (khi DB bật) |
| Đo tốc độ | Có (dựa vào thời gian đọc stream) | Có (dựa vào vòng lặp nhận) |
| Giao thức | Multipart HTTP | Socket thuần length-prefix |

## ✅ Checklist Kiểm Tra Nhanh
- [ ] `GET /api/health` hoạt động
- [ ] Upload nhỏ thành công (DB tắt) trả `stored=false`
- [ ] Upload khi DB bật trả `file_id`, `session_id`
- [ ] `GET /api/files` trả 503 nếu DB tắt
- [ ] `GET /api/stats` trả số liệu đúng
- [ ] Guest login (DB tắt) trả `user_id=1`

## 📦 Biến Môi Trường Liên Quan
| Tên | Vai trò | Giá trị ví dụ |
|-----|---------|---------------|
| ENABLE_DB | Bật/tắt thao tác DB | `true` / `false` |
| TCP_PORT | Cổng TCP server (health hiển thị) | `9999` |

## 📝 Lưu Ý Cuối
- API này không hỗ trợ tải xuống file.
- Mọi số liệu tốc độ (`mbps`) mang tính tương đối để demo.
- Khi cần ghi file qua HTTP có thể mở rộng bằng cách lưu chunk vào đĩa (chưa triển khai theo phạm vi đề tài).
