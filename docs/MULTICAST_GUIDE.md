# 📡 Multicast Monitoring - Hướng Dẫn

## 🎯 Mục Đích

**Multicast Monitoring** cho phép server tự động phát (broadcast) thông tin trạng thái đến tất cả các dashboard/monitor đang lắng nghe trong mạng LAN, mà không cần dashboard phải liên tục hỏi (poll) server.

### Lợi Ích
- ✅ **Real-time**: Dashboard nhận dữ liệu ngay lập tức khi có thay đổi
- ✅ **Hiệu quả**: Không tốn băng thông cho request/response
- ✅ **Scalable**: Thêm dashboard mới không tăng tải server
- ✅ **Đơn giản**: Server chỉ cần "phát", dashboard chỉ cần "nghe"

---

## ⚙️ Cấu Hình

### File: `server/server_config.py`

```python
# Multicast monitoring (Week 7)
ENABLE_MULTICAST = True              # Bật/tắt multicast
MULTICAST_GROUP = '239.0.0.1'        # IP multicast group
MULTICAST_PORT = 5555                # Cổng multicast
MULTICAST_INTERVAL = 3.0             # Giây giữa mỗi lần phát
MULTICAST_TTL = 2                    # Phạm vi: 1=subnet, 2=site, >2=rộng hơn
```

### Override bằng biến môi trường (PowerShell):

```powershell
$env:ENABLE_MULTICAST = "true"
$env:MULTICAST_GROUP = "239.0.0.1"
$env:MULTICAST_PORT = "5555"
$env:MULTICAST_INTERVAL = "3.0"
$env:MULTICAST_TTL = "2"
```

---

## 🚀 Cách Sử Dụng

### Bước 1: Cập Nhật Server (chỉ làm 1 lần)

Chạy script PowerShell để cập nhật các file server:

```powershell
cd d:\LTM\nhomltmck
.\update_multicast.ps1
```

Script sẽ:
- Backup các file cũ
- Cập nhật `server_config.py`, `run_combined.py`, `shared_state.py`
- Kiểm tra `multicast_monitor.py` đã có chưa

### Bước 2: Khởi Động Server

```powershell
cd d:\LTM\nhomltmck
$env:ENABLE_DB = "true"
python -m server.run_combined
```

Nếu multicast được bật, bạn sẽ thấy log:

```
[Multicast] Started broadcasting to 239.0.0.1:5555 (TTL=2)
[Multicast] Interval: 3.0s
```

### Bước 3: Khởi Động Dashboard

**Trong terminal khác** (để xem stats real-time):

```powershell
cd d:\LTM\nhomltmck
python -m server.multicast_dashboard
```

Hoặc:

```powershell
python server\multicast_dashboard.py
```

Dashboard sẽ hiển thị:

```
📡 Multicast Monitoring Dashboard
======================================================================
Listening on: 239.0.0.1:5555
Waiting for server broadcasts...
----------------------------------------------------------------------

======================================================================
📊 Active Servers
======================================================================

🟢 Server: 127.0.0.1:9999 (tcp-9999)
   Status: READY
   Uptime: 5 minutes
   Active Connections: 2
   Files Uploaded (session): 15
   Bytes Uploaded (session): 125.50 MB
   📦 Database Stats:
      • Total Files (DB): 127
      • Total Bytes (DB): 8.50 GB
   Last Update: 2025-11-15T20:30:00

======================================================================
Press Ctrl+C to stop
----------------------------------------------------------------------
```

---

## 📊 Dữ Liệu Multicast

Mỗi 3 giây (hoặc theo `MULTICAST_INTERVAL`), server sẽ gửi JSON như sau:

```json
{
  "server_id": "tcp-9999",
  "host": "127.0.0.1",
  "port": 9999,
  "timestamp": "2025-11-15T20:30:00",
  "uptime_seconds": 300,
  "active_connections": 2,
  "total_files": 15,
  "total_bytes": 131621888,
  "db_enabled": true,
  "db_total_files": 127,
  "db_total_bytes": 9126805504,
  "status": "ready"
}
```

---

## 🔧 Tùy Chỉnh

### Tắt Multicast

**Cách 1: Sửa file config**

```python
# server/server_config.py
ENABLE_MULTICAST = False
```

**Cách 2: Dùng biến môi trường**

```powershell
$env:ENABLE_MULTICAST = "false"
python -m server.run_combined
```

### Thay Đổi Multicast Group/Port

```python
# server/server_config.py
MULTICAST_GROUP = '239.1.2.3'  # IP khác trong dải 239.0.0.0/8
MULTICAST_PORT = 6666          # Cổng khác
```

Sau đó dashboard cũng phải dùng group/port tương ứng:

```powershell
python server\multicast_dashboard.py 239.1.2.3 6666
```

### Giảm Tần Suất Phát

```python
# server/server_config.py
MULTICAST_INTERVAL = 10.0  # Phát mỗi 10 giây thay vì 3 giây
```

---

## 🧪 Test Multicast

### Test 1: Một Server, Một Dashboard

1. Terminal 1:
   ```powershell
   cd d:\LTM\nhomltmck
   $env:ENABLE_DB = "true"
   python -m server.run_combined
   ```

2. Terminal 2:
   ```powershell
   cd d:\LTM\nhomltmck
   python -m server.multicast_dashboard
   ```

3. Terminal 3 (client):
   ```powershell
   cd d:\LTM\nhomltmck
   python -m client.gui.main_window
   ```

4. Upload vài file, xem dashboard tự động cập nhật số liệu.

### Test 2: Nhiều Dashboard

Mở nhiều terminal chạy dashboard:

```powershell
# Terminal 2
python -m server.multicast_dashboard

# Terminal 3
python -m server.multicast_dashboard

# Terminal 4
python -m server.multicast_dashboard
```

Tất cả dashboard sẽ nhận cùng dữ liệu từ server.

### Test 3: Nhiều Server (Advanced)

Nếu có nhiều máy trong LAN:

**Máy A:**
```powershell
python -m server.run_combined
```

**Máy B:**
```powershell
$env:TCP_PORT = "10000"
python -m server.run_combined
```

**Dashboard (Máy C hoặc bất kỳ):**
```powershell
python -m server.multicast_dashboard
```

Dashboard sẽ hiển thị cả 2 server.

---

## 📚 Liên Quan Đến Đề Cương

**Week 7: Multicast & Broadcast**

- ✅ **Broadcast**: Đã có UDP discovery (tìm server trong LAN)
- ✅ **Multicast**: Multicast monitoring (giám sát real-time)

**So sánh:**

| Tính năng | Broadcast (UDP Discovery) | Multicast (Monitoring) |
|-----------|---------------------------|------------------------|
| Mục đích | Tìm server trong LAN | Giám sát trạng thái real-time |
| Hướng | Client → All servers | Server → All dashboards |
| Tần suất | Khi cần (on-demand) | Liên tục (mỗi 3s) |
| Dữ liệu | Server IP/port | Stats đầy đủ |
| Ứng dụng | Auto-discovery | Admin dashboard, monitoring |

---

## 🐛 Troubleshooting

### Dashboard không nhận được dữ liệu

1. **Kiểm tra firewall**: Cho phép Python nhận UDP trên cổng 5555
2. **Kiểm tra multicast có bật không**: Xem log server khi start
3. **Thử chạy cả server và dashboard trên cùng máy**
4. **Kiểm tra group/port khớp nhau giữa server và dashboard**

### Server báo lỗi multicast

```
[Multicast] Failed to start: ...
```

- Kiểm tra `multicast_monitor.py` có tồn tại không
- Kiểm tra group IP đúng định dạng (239.0.0.0 - 239.255.255.255)
- Thử TTL = 1 thay vì 2

### Dashboard chỉ thấy một server dù có nhiều

- Các server phải dùng cùng `MULTICAST_GROUP` và `MULTICAST_PORT`
- Dashboard phải join đúng group đó

---

## 📖 Tài Liệu Tham Khảo

- [RFC 1112 - Host Extensions for IP Multicasting](https://datatracker.ietf.org/doc/html/rfc1112)
- [Python socket - Multicast](https://docs.python.org/3/library/socket.html)
- Multicast IP range: 224.0.0.0/4 (239.0.0.0/8 cho organization-local)

---

## ✅ Checklist Demo

Để demo multicast monitoring trong presentation:

- [ ] Server chạy với multicast enabled
- [ ] Dashboard hiển thị stats real-time
- [ ] Upload vài file, stats tự động cập nhật
- [ ] Giải thích tại sao dùng multicast (hiệu quả, scalable)
- [ ] So sánh với broadcast và unicast
- [ ] Show nhiều dashboard nhận cùng dữ liệu

---


