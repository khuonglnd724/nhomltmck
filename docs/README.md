# Dự Án Upload File - Kiến Trúc Hybrid

## Tổng Quan
Dự án minh họa cách kết hợp ba giao thức **TCP + UDP + HTTP/HTTPS** để tối ưu tốc độ, khả năng khám phá dịch vụ, và mở rộng về quản lý.

```
┌────────────────────────────────────────────────────┐
│      Server Kết Hợp (run_combined.py)              │
├────────────────────────────────────────────────────┤
│  TCP (9999):  Upload file chính (đáng tin cậy)     │
│  UDP (9998):  Discovery + Ping + Pre-check         │
│  HTTP (8000): REST API (health, auth, stats)       │
│  Multicast:  Giám sát realtime (239.0.0.1:5555)    │
└────────────────────────────────────────────────────┘
```

### Vai Trò Từng Giao Thức

**TCP (9999)**
- Truyền file kích thước lớn
- Đảm bảo thứ tự & toàn vẹn
- Length prefix 8 byte + thread mỗi connection
- Ghi file xuống `uploads/` + cập nhật DB (nếu bật)

**UDP (9998 / broadcast 8888)**
- Khám phá server (broadcast)
- Ping đo độ trễ (unicast)
- Pre-check nhanh metadata (unicast)
- Không handshake → tiết kiệm thời gian kết nối ban đầu

**HTTP/HTTPS (8000)**
- API chuẩn: đăng ký, đăng nhập, upload (phiên bản HTTP), thống kê, danh sách file
- Dễ tích hợp trình duyệt / mobile
- Có thể bật HTTPS (ENV: ENABLE_HTTPS)

**Multicast (239.0.0.1:5555)**
- Phát số liệu trạng thái định kỳ (active connections, tổng file, bytes, uptime)
- Nhiều dashboard nhận cùng lúc, không gây thêm tải đơn lẻ

---

## Khởi Chạy Server Kết Hợp

```powershell
pip install -r requirements.txt
$env:ENABLE_DB = "true"    # bật DB (tuỳ chọn)
$env:ENABLE_UDP = "true"   # bật UDP discovery
$env:ENABLE_MULTICAST = "true"  # bật multicast
python -m server.run_combined
```

Output:
```
======================================================================
Combined TCP + UDP + HTTP/HTTPS Server
======================================================================
[SERVER] Started on 127.0.0.1:9999
[UDP] Server started on port 9998
[UDP] Advertising: TCP=9999, HTTP=8000
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## UDP - Khám Phá & Tối Ưu

### 1. Service Discovery (Tìm server tự động qua broadcast)

**Command-line (Passive):**
```powershell
python -m client.udp_discovery
```
**Active discovery:**
```powershell
python -c "from client.udp_discovery import discover_servers_active; print(discover_servers_active())"
```
**Lợi ích:** Không cần nhập IP, hỗ trợ nhiều server, thời gian tìm < 1s.

### 2. UDP Pre-check (Xác thực sớm)

**Luồng Tối Ưu:**
```
1. Client --[UDP pre-check]--> Server (10ms)
   { "filename": "test.txt", "filesize": 1024000, "user_id": 1 }

2. Server validate:
   - File size trong giới hạn?
   - User có quota không?
   - Format hợp lệ?

3. Server --[UDP response]--> Client (10ms)
   { "status": "ACCEPT", "tcp_port": 9999 }

4. Client --[TCP upload]--> Server (chính thức upload)

Tiết kiệm: ~50-100ms (không cần TCP handshake để check)
```

**So sánh:**
```
Không có UDP pre-check:
  TCP connect → Send metadata → Server reject → Close
  Latency: ~150ms (waste)

Có UDP pre-check:
  UDP check → Server reject
  Latency: ~20ms (fast fail)
```

### 3. Ping (Heartbeat)

```powershell
python -c "from client.udp_discovery import ping_server; print(f'{ping_server(\"127.0.0.1\")}ms')"
```

Output: `12.5ms` (vs TCP ping ~50ms)

---

## HTTP/HTTPS API

- Install deps:

```powershell
pip install -r requirements.txt
```

- Run HTTP server:

```powershell
```powershell
# Chỉ HTTP (nếu muốn tách riêng)
python -m server.http_server

# Server kết hợp (TCP + UDP + Multicast + HTTP)
$env:ENABLE_DB="true"; python -m server.run_combined
```
Endpoints chính:
- `GET /api/health`
- `POST /api/register` {username, password}
- `POST /api/login` {username, password}
- `POST /api/upload` (multipart: file, user_id)
- `GET /api/files?user_id=`
- `GET /api/stats`

Ghi chú: Khi DB tắt (`ENABLE_DB=false`), upload HTTP vẫn hoạt động nhưng không ghi bản ghi vào DB.

## Demo Client HTTP (tuỳ chọn nếu có)

- Install deps:
```powershell
pip install -r requirements.txt
```

- Quick usage:
```powershell
# Health
python -m client.http_client health
python -m client.http_client register --username demo --password secret
python -m client.http_client login --username demo --password secret
python -m client.http_client upload --file README.md --user-id 1
python -m client.http_client files --user-id 1
python -m client.http_client stats
```