"""UDP Discovery Client - Tự động tìm file upload servers trong mạng LAN.

Lợi ích so với manual config:
- Không cần biết trước IP server
- Tự động phát hiện nhiều servers
- Zero-configuration networking
- Nhanh (UDP broadcast < 100ms)

Usage:
    from client.udp_discovery import discover_servers
    servers = discover_servers(timeout=2.0)
    for srv in servers:
        print(f"Found: {srv['ip']}:{srv['tcp_port']}")
"""
from __future__ import annotations
import socket
import json
import time
from typing import List, Dict, Optional


def discover_servers(timeout: float = 2.0, broadcast_port: int = 8888) -> List[Dict[str, any]]:
    """Broadcast tìm kiếm servers trong LAN.
    
    Args:
        timeout: Thời gian chờ responses (seconds)
        broadcast_port: Port để nhận server announcements
        
    Returns:
        List của server info dicts với keys: ip, tcp_port, http_port, udp_port
    """
    servers = []
    seen_ips = set()
    
    try:
        # Tạo UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        # Bind để nhận announcements
        sock.bind(("", broadcast_port))
        
        print(f"[UDP Discovery] Listening on broadcast port {broadcast_port}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                
                # Tránh duplicate
                if ip in seen_ips:
                    continue
                
                try:
                    msg = json.loads(data.decode())
                    if msg.get("type") == "SERVER_ANNOUNCEMENT":
                        server_info = {
                            "ip": ip,
                            "tcp_port": msg.get("tcp_port", 9999),
                            "http_port": msg.get("http_port", 8000),
                            "udp_port": msg.get("udp_port", 9998),
                            "timestamp": msg.get("timestamp", time.time())
                        }
                        servers.append(server_info)
                        seen_ips.add(ip)
                        print(f"[UDP Discovery] Found server: {ip}:{server_info['tcp_port']}")
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[UDP Discovery] Invalid announcement from {ip}: {e}")
            except socket.timeout:
                # Timeout bình thường khi hết thời gian chờ
                break
            except Exception as e:
                print(f"[UDP Discovery] Receive error: {e}")
                break
        
        sock.close()
    except Exception as e:
        print(f"[UDP Discovery] Failed: {e}")
    
    return servers


def discover_servers_active(timeout: float = 1.0, udp_port: int = 9998) -> List[Dict[str, any]]:
    """Gửi DISCOVERY request chủ động thay vì chờ broadcast (nhanh hơn).
    
    Args:
        timeout: Thời gian chờ responses
        udp_port: Port UDP server
        
    Returns:
        List servers found
    """
    servers = []
    seen_ips = set()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)
        
        # Gửi DISCOVERY request broadcast
        request = json.dumps({"type": "DISCOVERY"})
        sock.sendto(request.encode(), ("<broadcast>", udp_port))
        print(f"[UDP Discovery] Sent DISCOVERY broadcast to port {udp_port}...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                
                if ip in seen_ips:
                    continue
                
                msg = json.loads(data.decode())
                if msg.get("type") == "DISCOVERY_RESPONSE":
                    server_info = {
                        "ip": ip,
                        "tcp_port": msg.get("tcp_port", 9999),
                        "http_port": msg.get("http_port", 8000),
                        "udp_port": msg.get("udp_port", 9998),
                        "status": msg.get("status", "unknown")
                    }
                    servers.append(server_info)
                    seen_ips.add(ip)
                    print(f"[UDP Discovery] Found server: {ip}:{server_info['tcp_port']} (status: {server_info['status']})")
            except socket.timeout:
                break
            except Exception as e:
                print(f"[UDP Discovery] Error: {e}")
                break
        
        sock.close()
    except Exception as e:
        print(f"[UDP Discovery] Failed: {e}")
    
    return servers


def ping_server(host: str, udp_port: int = 9998, timeout: float = 1.0) -> Optional[float]:
    """Ping server qua UDP để check latency (nhanh hơn TCP).
    
    Returns:
        Round-trip time in milliseconds, or None if failed
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        request = json.dumps({"type": "PING"})
        t0 = time.perf_counter()
        sock.sendto(request.encode(), (host, udp_port))
        
        data, _ = sock.recvfrom(1024)
        t1 = time.perf_counter()
        
        msg = json.loads(data.decode())
        if msg.get("type") == "PONG":
            rtt_ms = (t1 - t0) * 1000
            return rtt_ms
        
        sock.close()
    except Exception as e:
        print(f"[UDP Ping] Failed: {e}")
    
    return None


def pre_check_upload(host: str, filename: str, filesize: int, user_id: int = 0,
                     udp_port: int = 9998, timeout: float = 2.0) -> Dict[str, any]:
    """Gửi metadata qua UDP trước khi upload TCP để validate nhanh.
    
    Lợi ích:
    - Không cần TCP handshake (tiết kiệm ~50-100ms)
    - Server reject ngay nếu file quá lớn
    - Client biết TCP port & session_id trước
    
    Returns:
        {"status": "ACCEPT"/"REJECT", "reason": ..., "tcp_port": ..., "session_id": ...}
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        request = json.dumps({
            "type": "PRE_CHECK",
            "filename": filename,
            "filesize": filesize,
            "user_id": user_id
        })
        sock.sendto(request.encode(), (host, udp_port))
        
        data, _ = sock.recvfrom(4096)
        response = json.loads(data.decode())
        
        sock.close()
        return response
    except socket.timeout:
        return {"status": "ERROR", "reason": "Server không phản hồi (timeout)"}
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}


if __name__ == "__main__":
    print("=== UDP Discovery Demo ===\n")
    
    # Method 1: Passive listen (chờ server broadcast)
    print("1. Passive discovery (listening for announcements)...")
    servers = discover_servers(timeout=3.0)
    print(f"   Found {len(servers)} server(s)\n")
    
    # Method 2: Active broadcast (nhanh hơn)
    print("2. Active discovery (sending DISCOVERY request)...")
    servers = discover_servers_active(timeout=1.0)
    print(f"   Found {len(servers)} server(s)\n")
    
    if servers:
        srv = servers[0]
        print(f"3. Testing server {srv['ip']}:")
        
        # Ping test
        rtt = ping_server(srv['ip'], srv['udp_port'])
        if rtt:
            print(f"   UDP Ping: {rtt:.2f}ms")
        
        # Pre-check test
        result = pre_check_upload(srv['ip'], "test.txt", 1024, user_id=0, udp_port=srv['udp_port'])
        print(f"   Pre-check: {result['status']} - {result.get('reason', 'OK')}")
