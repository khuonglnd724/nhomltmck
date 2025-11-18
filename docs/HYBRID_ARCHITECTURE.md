# Kiến Trúc Hybrid: TCP + UDP + HTTP + Multicast

## Vì Sao Kết Hợp Nhiều Giao Thức?

### Nguyên tắc: "Dùng đúng công cụ cho đúng việc"

Mỗi giao thức có thế mạnh riêng:

| Protocol      | Điểm mạnh                        | Điểm yếu                   | Tình huống dùng            |
| ------------- | -------------------------------- | -------------------------- | -------------------------- |
| **TCP**       | Tin cậy tuyệt đối, có thứ tự     | Handshake ban đầu          | Upload file lớn            |
| **UDP**       | Độ trễ thấp, không handshake     | Không đảm bảo tin cậy      | Discovery, ping, pre-check |
| **HTTP**      | Chuẩn, dễ tích hợp, qua firewall | Overhead, stateless        | API quản lý, web/mobile    |
| **Multicast** | Phát 1 lần nhiều nơi nhận        | Không xác nhận từng client | Giám sát realtime          |

---

## Cách Áp Dụng Trong Dự Án

### 1. UDP Discovery → Chuẩn Bị TCP Upload

**Vấn đề:** Client phải nhập IP/port thủ công (dễ sai, tốn thời gian)

**Giải pháp (UDP broadcast):**

```
[Server] ------broadcast------> [LAN] (mỗi 5s)
   "FileServer @ 192.168.1.100:9999"

[Client GUI] "🔍 Tìm server"
   → Nhận broadcast
   → Auto-fill IP:port
   → Kết nối TCP
```

**So sánh:**

- Cấu hình tay: ~30s
- UDP discovery tự động: ~0.5s

---

### 2. UDP Pre-check → Giảm Lãng Phí Kết Nối TCP

**Vấn đề:** TCP handshake tốn thời gian; nếu file bị từ chối thì phí kết nối

**Giải pháp (UDP PRE_CHECK):**

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

### 3. UDP Ping → Kiểm Tra Sống (Health)

**Vấn đề:** Dùng TCP để kiểm tra độ trễ = tốn thêm handshake

**Giải pháp (UDP PING/PONG):**

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

### 4. HTTP API → Quản Lý & Tích Hợp Ngoài

**Vấn đề:** Desktop client thuần TCP khó tích hợp web/mobile

**Giải pháp (HTTP chuẩn REST):**

```javascript
// Web client
fetch("http://server.com/api/upload", {
  method: "POST",
  body: formData,
});

// Mobile (React Native, Flutter)
axios.post("/api/upload", data);
```

**Lợi ích:**

- Standard protocol
- Browser compatible
- Firewall-friendly (port 80/443)
- Swagger UI documentation

---

## So Sánh Hiệu Năng (Ví Dụ)

### Trường hợp: Upload file 10MB

| Kịch bản            | Chuẩn bị | Thời gian upload | Tốc độ |
| ------------------- | -------- | ---------------- | ------ |
| Manual + TCP        | ~30s     | ~2s              | 5 MB/s |
| UDP discovery + TCP | ~0.5s    | ~2s              | 5 MB/s |
| Tiết kiệm           | ~29.5s   | -                | -      |

### Trường hợp: File bị từ chối (quá lớn)

| Kịch bản         | Thời gian lãng phí |
| ---------------- | ------------------ |
| Chỉ TCP          | ~90ms              |
| Có UDP pre-check | ~20ms              |
| Tiết kiệm        | ~70ms / file       |

---

## Nên Dùng Giao Thức Nào Khi Nào?

### TCP

- Upload file lớn (>1MB)
- Cần độ tin cậy tuyệt đối
- Qua Internet (UDP dễ bị filter)
- Có yêu cầu tracking tiến độ

### UDP

- Tìm server tự động (broadcast)
- Ping nhanh độ trễ thấp
- Pre-check metadata trước TCP
- Mạng LAN ổn định
- Không dùng để truyền file lớn

### HTTP

- Tích hợp web/mobile
- REST chuẩn, dễ mở rộng
- Qua firewall dễ dàng
- Dùng cho xác thực / quản lý
- Không tối ưu truyền file lớn tùy chỉnh

### Multicast

- Giám sát trạng thái realtime nhiều dashboard
- Giảm tải so với mỗi dashboard phải tự hỏi (poll)

---

## Kịch Bản Thực Tế Tối Ưu

### Luồng Khởi Động Nhanh:

```
Người dùng mở ứng dụng
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

**Thời gian tổng:** ~11s (so với ~41s nếu không dùng UDP)

---

## Kết Luận

**Hybrid = Phối hợp điểm mạnh:**

- UDP: Tìm & xác thực nhanh
- TCP: Truyền tin cậy
- HTTP: Quản lý & tích hợp
- Multicast: Giám sát realtime hiệu quả

Không chỉ “so sánh” mà là “kết hợp để tối ưu toàn diện”.

---

## Cấu Hình Chung (Đồng Bộ)

Các thông số upload/streaming dùng chung cho Client và Server được đặt trong `config.py` ở thư mục gốc:

- `CONNECTION_TIMEOUT` = 60s
- `MAX_FILE_SIZE_MB` = 100MB
- `CHUNK_SIZE` = 8192 bytes (client gửi)
- `BUFFER_SIZE` = 4096 bytes (server nhận)

`server/server_config.py` import các giá trị này cho TCP/HTTP/UDP server. Hãy cập nhật ở `config.py` để tránh sai lệch giữa các thành phần.
