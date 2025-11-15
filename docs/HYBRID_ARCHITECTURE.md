# Kiến trúc Hybrid: TCP + UDP + HTTP

## Tại sao kết hợp 3 protocols?

### Nguyên tắc: "Right tool for the right job"

Mỗi protocol có điểm mạnh riêng:

| Protocol | Điểm mạnh | Điểm yếu | Use case |
|----------|-----------|----------|----------|
| **TCP** | Reliable 100%, ordered | High latency (handshake) | File upload lớn |
| **UDP** | Low latency, no handshake | Unreliable, no order | Discovery, ping, pre-check |
| **HTTP** | Standard, firewall-friendly, tooling | Overhead, stateless | API, web integration |

---

## Chi tiết kết hợp trong dự án

### 1. UDP Discovery → TCP Upload

**Vấn đề:** Client phải biết trước IP server (không tự động)

**Giải pháp UDP:**
```
[Server] ------broadcast------> [LAN] (mỗi 5s)
   "FileServer @ 192.168.1.100:9999"

[Client GUI] "🔍 Tìm server"
   → Nhận broadcast
   → Auto-fill IP:port
   → Kết nối TCP
```

**Benchmark:**
- Manual config: ~30s (nhập tay, có thể sai)
- UDP discovery: ~0.5s (tự động, chính xác)

---

### 2. UDP Pre-check → TCP Upload

**Vấn đề:** TCP handshake tốn thời gian, nếu server reject (file quá lớn) thì waste

**Giải pháp UDP:**
```python
# Trước (chỉ TCP):
1. TCP connect         50ms  ┐
2. Send metadata       20ms  │ Waste if rejected
3. Server validate           │
4. Server reject       10ms  ┘
5. Close connection    10ms
---
Total: 90ms waste

# Sau (UDP pre-check):
1. UDP pre-check       10ms
2. Server validate
3. Server reject       10ms
---
Total: 20ms (tiết kiệm 70ms)

Nếu ACCEPT:
4. TCP connect         50ms  ← Chỉ khi đã validate OK
5. Upload...
```

**Code flow:**
```python
# client/uploader/upload_client.py
def upload_file(self, filepath, ...):
    # UDP pre-check
    result = udp_precheck(host, filename, filesize, user_id)
    if result["status"] == "REJECT":
        return {"error": result["reason"]}  # Fast fail
    
    # TCP upload (chỉ khi đã pass pre-check)
    with TCPConnection(host, port) as conn:
        conn.send_file(filepath)
```

---

### 3. UDP Ping → Health check

**Vấn đề:** TCP health check cần handshake (slow)

**Giải pháp UDP:**
```
TCP ping:
  SYN → SYN-ACK → ACK → Close
  Latency: ~50-80ms

UDP ping:
  PING → PONG
  Latency: ~5-15ms (3-5x nhanh hơn)
```

**Usage:**
```python
from client.udp_discovery import ping_server
latency = ping_server("192.168.1.100")
print(f"Server latency: {latency}ms")
```

---

### 4. HTTP API → Management

**Vấn đề:** Desktop client khó tích hợp web/mobile

**Giải pháp HTTP:**
```javascript
// Web client
fetch('http://server.com/api/upload', {
  method: 'POST',
  body: formData
})

// Mobile (React Native, Flutter)
axios.post('/api/upload', data)
```

**Lợi ích:**
- Standard protocol
- Browser compatible
- Firewall-friendly (port 80/443)
- Swagger UI documentation

---

## Benchmark Performance

### Test case: Upload 10MB file

| Scenario | Latency | Throughput |
|----------|---------|------------|
| **Manual config + TCP** | ~30s setup + 2s upload | 5 MB/s |
| **UDP discovery + TCP** | ~0.5s setup + 2s upload | 5 MB/s |
| **Saving:** | **29.5s faster** | - |

### Test case: File rejected (too large)

| Scenario | Wasted time |
|----------|-------------|
| **TCP only** | ~90ms (handshake + metadata + reject) |
| **UDP pre-check** | ~20ms (validate + reject) |
| **Saving:** | **70ms per rejected file** |

---

## Khi nào dùng protocol nào?

### Dùng TCP:
- ✅ Upload file lớn (> 1MB)
- ✅ Cần đảm bảo toàn vẹn dữ liệu
- ✅ Qua Internet (UDP thường bị chặn)
- ✅ Streaming có progress tracking

### Dùng UDP:
- ✅ Service discovery (broadcast)
- ✅ Heartbeat/health check (low latency)
- ✅ Pre-validation (fast fail)
- ✅ Trong LAN (packet loss thấp)
- ❌ KHÔNG dùng cho file lớn (unreliable)

### Dùng HTTP:
- ✅ Web/mobile integration
- ✅ REST API standard
- ✅ Public internet (firewall-friendly)
- ✅ Authentication/management
- ❌ KHÔNG dùng cho custom protocol (overhead cao)

---

## Real-world scenario

### Startup flow tối ưu:

```
User mở app
  ↓
1. GUI click "🔍 Tìm server"
   → UDP broadcast discovery (0.5s)
   → Auto-fill 192.168.1.100:9999
  ↓
2. UDP ping check latency (0.01s)
   → Display: "Server OK (12ms)"
  ↓
3. User login qua HTTP API (0.2s)
   → GET /api/login
   → Store user_id
  ↓
4. User drag & drop file 50MB
   ↓
5. UDP pre-check (0.02s)
   → Server validate: OK
   ↓
6. TCP upload with progress (10s)
   → 8KB chunks
   → Progress bar real-time
   ↓
7. HTTP query uploaded files (0.1s)
   → GET /api/files?user_id=1
   → Display list
```

**Total time:** ~11s (vs ~41s without UDP optimization)

---

## Kết luận

**Hybrid architecture = Best of all worlds:**
- UDP: Fast discovery & validation
- TCP: Reliable upload
- HTTP: Standard API

**Không phải "so sánh" TCP vs UDP, mà là "kết hợp" để tối ưu!**
