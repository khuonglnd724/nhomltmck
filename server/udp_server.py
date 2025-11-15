"""UDP Server cho Service Discovery và Fast Metadata Exchange.

Chức năng:
1. Service Discovery: broadcast thông tin TCP/HTTP server cho clients tự động tìm.
2. Heartbeat/Ping: UDP ping/pong nhanh để check server alive (không cần TCP handshake).
3. Pre-check Metadata: client gửi file info qua UDP, server validate nhanh trước khi bắt đầu TCP upload.

Port mặc định: 9998 (UDP)
"""
from __future__ import annotations
import socket
import json
import threading
import time
import os
from typing import Optional

# Optional database for validation
try:
    from database.db_manager import DB
except Exception:
    DB = None


class UDPServer:
    def __init__(self, udp_port: int = 9998, tcp_port: int = 9999, http_port: int = 8000):
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.http_port = http_port
        self.sock: Optional[socket.socket] = None
        self.running = False
        self.stats = {
            "discovery_requests": 0,
            "heartbeat_pings": 0,
            "metadata_checks": 0,
        }

    def start(self):
        """Khởi động UDP server."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", self.udp_port))
            self.running = True
            print(f"[UDP] Server started on port {self.udp_port}")
            print(f"[UDP] Advertising: TCP={self.tcp_port}, HTTP={self.http_port}")
            
            # Start broadcast thread
            broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
            broadcast_thread.start()
            
            # Main receive loop
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    threading.Thread(target=self._handle_message, args=(data, addr), daemon=True).start()
                except Exception as e:
                    if self.running:
                        print(f"[UDP] Receive error: {e}")
        except Exception as e:
            print(f"[UDP] Failed to start: {e}")
        finally:
            self.stop()

    def _broadcast_loop(self):
        """Broadcast thông tin server mỗi 5 giây (service discovery)."""
        broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                message = json.dumps({
                    "type": "SERVER_ANNOUNCEMENT",
                    "tcp_port": self.tcp_port,
                    "http_port": self.http_port,
                    "udp_port": self.udp_port,
                    "timestamp": time.time()
                })
                broadcast_sock.sendto(message.encode(), ("<broadcast>", 8888))
            except Exception as e:
                print(f"[UDP] Broadcast error: {e}")
            time.sleep(5)
        broadcast_sock.close()

    def _handle_message(self, data: bytes, addr):
        """Xử lý các loại message UDP."""
        try:
            msg = json.loads(data.decode())
            msg_type = msg.get("type")
            
            if msg_type == "DISCOVERY":
                self._handle_discovery(addr)
            elif msg_type == "PING":
                self._handle_ping(addr)
            elif msg_type == "PRE_CHECK":
                self._handle_precheck(msg, addr)
            else:
                print(f"[UDP] Unknown message type: {msg_type} from {addr}")
        except json.JSONDecodeError:
            print(f"[UDP] Invalid JSON from {addr}")
        except Exception as e:
            print(f"[UDP] Handle error from {addr}: {e}")

    def _handle_discovery(self, addr):
        """Trả lời yêu cầu discovery với thông tin server."""
        self.stats["discovery_requests"] += 1
        response = json.dumps({
            "type": "DISCOVERY_RESPONSE",
            "tcp_port": self.tcp_port,
            "http_port": self.http_port,
            "udp_port": self.udp_port,
            "status": "ready"
        })
        self.sock.sendto(response.encode(), addr)
        print(f"[UDP] Discovery response sent to {addr}")

    def _handle_ping(self, addr):
        """Trả lời heartbeat ping."""
        self.stats["heartbeat_pings"] += 1
        response = json.dumps({
            "type": "PONG",
            "timestamp": time.time()
        })
        self.sock.sendto(response.encode(), addr)

    def _handle_precheck(self, msg: dict, addr):
        """Validate metadata trước khi client bắt đầu TCP upload.
        
        Lợi ích UDP:
        - Không cần TCP handshake (tiết kiệm 1.5 RTT)
        - Nhanh hơn 3-5x so với HTTP request
        - Client biết ngay nếu file quá lớn/không hợp lệ
        """
        self.stats["metadata_checks"] += 1
        
        filename = msg.get("filename", "unknown")
        filesize = msg.get("filesize", 0)
        user_id = msg.get("user_id", 0)
        
        # Validate
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024
        
        if filesize > max_size:
            response = {
                "type": "PRE_CHECK_RESPONSE",
                "status": "REJECT",
                "reason": f"File quá lớn (max {max_size//1024//1024} MB)"
            }
        elif filesize <= 0:
            response = {
                "type": "PRE_CHECK_RESPONSE",
                "status": "REJECT",
                "reason": "File size không hợp lệ"
            }
        else:
            # Optional: check quota nếu DB enabled
            if DB and user_id > 0:
                try:
                    # Có thể thêm logic check quota user tại đây
                    pass
                except Exception:
                    pass
            
            response = {
                "type": "PRE_CHECK_RESPONSE",
                "status": "ACCEPT",
                "tcp_port": self.tcp_port,
                "session_id": f"{addr[0]}_{int(time.time())}"
            }
        
        self.sock.sendto(json.dumps(response).encode(), addr)
        print(f"[UDP] Pre-check {response['status']}: {filename} ({filesize} bytes) from {addr}")

    def stop(self):
        """Dừng UDP server."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        print(f"[UDP] Server stopped")
        print(f"[UDP] Stats: discovery={self.stats['discovery_requests']}, "
              f"pings={self.stats['heartbeat_pings']}, "
              f"pre-checks={self.stats['metadata_checks']}")


if __name__ == "__main__":
    server = UDPServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[UDP] Shutting down...")
        server.stop()
