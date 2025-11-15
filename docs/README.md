# nhomltmck

## Kiến trúc Hybrid TCP + UDP + HTTP/HTTPS

Dự án tối ưu hiệu suất bằng cách kết hợp 3 protocols:

```
┌────────────────────────────────────────────────────┐
│         Combined Server (run_combined.py)          │
├────────────────────────────────────────────────────┤
│  TCP (9999):   File upload chính (reliable)       │
│  UDP (9998):   Discovery + Pre-check (fast)       │
│  HTTP (8000):  REST API + Management               │
└────────────────────────────────────────────────────┘
```

### Vai trò từng protocol:

**TCP (port 9999):**
- Upload file lớn, đáng tin cậy 100%
- Custom protocol với 8-byte length prefix
- Progress tracking với ACK
- Multi-threaded, connection-oriented

**UDP (port 9998):**
- Service Discovery: broadcast tìm server tự động
- Heartbeat/Ping: check server alive nhanh
- Pre-check: validate file trước khi upload TCP (tiết kiệm 50-100ms)
- Không cần handshake → latency thấp

**HTTP/HTTPS (port 8000):**
- REST API chuẩn cho web/mobile
- Authentication (login/register)
- File management (list, stats)
- Optional HTTPS với TLS

---

## Chạy server kết hợp

```powershell
pip install -r requirements.txt
$env:ENABLE_DB = "true"  # optional
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

## UDP Optimization - Cách sử dụng

### 1. Service Discovery (Tìm server tự động)

**Client GUI:**
- Click nút "🔍 Tìm server"
- UDP broadcast trong LAN
- Auto-fill IP:port khi tìm thấy

**Command-line:**
```powershell
python -m client.udp_discovery
```

**Lợi ích:**
- Không cần config IP thủ công
- Phát hiện nhiều servers
- Zero-configuration networking
- Latency < 100ms

### 2. UDP Pre-check (Fast validation)

**Flow tối ưu:**
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

### 3. Heartbeat/Ping

```powershell
python -c "from client.udp_discovery import ping_server; print(f'{ping_server(\"127.0.0.1\")}ms')"
```

Output: `12.5ms` (vs TCP ping ~50ms)

---

## HTTP/HTTPS Server

- Install deps:

```powershell
pip install -r requirements.txt
```

- Run HTTP server:

```powershell
python -m server.http_server
- Combined TCP + HTTP demo (single process):

```powershell
# Optional DB integration
$env:ENABLE_DB = "true"
python -m server.run_combined
```

Then test:
- TCP uploads via existing desktop client (port 9999)
- HTTP uploads via `POST /api/upload` (port 8000)
- Check unified status: `GET http://127.0.0.1:8000/api/health` (includes TCP stats)

```

- Configure HTTPS (optional):
	- Provide cert/key files and set env vars, then run:

```powershell
$env:ENABLE_HTTPS = "true"
$env:SSL_CERTFILE = "C:\path\to\cert.pem"
$env:SSL_KEYFILE = "C:\path\to\key.pem"
python -m server.http_server
```

- Endpoints:
	- `GET /api/health`
	- `POST /api/register` { username, password }
	- `POST /api/login` { username, password }
	- `POST /api/upload` multipart form: `file`, `user_id` (int, optional; default guest=0)
	- `GET /api/files?user_id=...`
	- `GET /api/stats`

Note: When DB is disabled (`ENABLE_DB=false`), uploads still stream and succeed but only as metadata-less operations (no DB records).

## HTTP Demo Client

- Install deps:
```powershell
pip install -r requirements.txt
```

- Quick usage:
```powershell
# Health
python -m client.http_client health

# Register & login
python -m client.http_client register --username demo --password secret
python -m client.http_client login --username demo --password secret

# Upload as guest
python -m client.http_client upload --file README.md --user-id 0

# List files & stats
python -m client.http_client files --user-id 0
python -m client.http_client stats

# Custom server URL
$env:HTTP_SERVER_URL = "http://127.0.0.1:8000"; python -m client.http_client health
```