"""
Multicast Monitoring Module
Broadcasts server statistics to multicast group for real-time monitoring.
Week 7: Multicast & Broadcast implementation.
"""
import socket
import json
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


class MulticastMonitor:
    """
    Multicast sender that broadcasts server stats periodically.
    
    Usage:
        monitor = MulticastMonitor(server_instance)
        monitor.start()  # Non-blocking, runs in background thread
        monitor.stop()   # Graceful shutdown
    """
    
    def __init__(
        self,
        server_instance,
        multicast_group: str = "239.0.0.1",
        multicast_port: int = 5555,
        interval_seconds: float = 3.0,
        ttl: int = 2
    ):
        """
        Args:
            server_instance: Reference to FileUploadServer instance
            multicast_group: Multicast IP (239.0.0.0 - 239.255.255.255)
            multicast_port: Port for multicast
            interval_seconds: How often to broadcast stats
            ttl: Time-to-live (1=same subnet, 2=same site, >2=wider)
        """
        self.server = server_instance
        self.multicast_group = multicast_group
        self.multicast_port = multicast_port
        self.interval = interval_seconds
        self.ttl = ttl
        
        self.socket: Optional[socket.socket] = None
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = time.time()
        
    def start(self):
        """Start broadcasting in background thread."""
        if self._thread and self._thread.is_alive():
            print("[Multicast] Already running")
            return
            
        try:
            # Create UDP socket for multicast
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, self.ttl)
            
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._broadcast_loop, daemon=True, name="MulticastMonitor")
            self._thread.start()
            
            print(f"[Multicast] Started broadcasting to {self.multicast_group}:{self.multicast_port} (TTL={self.ttl})")
            print(f"[Multicast] Interval: {self.interval}s")
        except Exception as e:
            print(f"[Multicast] Failed to start: {e}")
            
    def stop(self):
        """Stop broadcasting gracefully."""
        if not self._thread or not self._thread.is_alive():
            return
            
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        print("[Multicast] Stopped")
        
    def _broadcast_loop(self):
        """Main loop: collect stats and broadcast periodically."""
        while not self._stop_event.is_set():
            try:
                stats = self._collect_stats()
                message = json.dumps(stats, ensure_ascii=False)
                self.socket.sendto(
                    message.encode('utf-8'),
                    (self.multicast_group, self.multicast_port)
                )
                # Optionally log to console (comment out for production)
                # print(f"[Multicast] Sent: {stats['active_connections']} connections")
            except Exception as e:
                print(f"[Multicast] Broadcast error: {e}")
                
            # Sleep with early exit if stop requested
            self._stop_event.wait(self.interval)
            
    def _collect_stats(self) -> Dict[str, Any]:
        """Gather current server statistics."""
        uptime = time.time() - self._start_time
        
        # Get database stats if available
        db_files = 0
        db_bytes = 0
        if hasattr(self.server, 'enable_db') and self.server.enable_db and self.server.db:
            try:
                db_stats = self.server.db.get_stats()
                # Convert Decimal to int to avoid JSON serialization error
                db_files = int(db_stats.get('total_files', 0))
                db_bytes_raw = db_stats.get('total_bytes', 0)
                db_bytes = int(db_bytes_raw) if isinstance(db_bytes_raw, (Decimal, int, float)) else 0
            except Exception:
                pass
        
        stats = {
            "server_id": f"tcp-{self.server.port}",
            "host": self.server.host,
            "port": self.server.port,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(uptime),
            
            # Real-time metrics
            "active_connections": self.server.upload_stats.get('active_connections', 0),
            "total_files": self.server.upload_stats.get('total_files', 0),
            "total_bytes": self.server.upload_stats.get('total_bytes', 0),
            
            # Database metrics (if enabled)
            "db_enabled": hasattr(self.server, 'enable_db') and self.server.enable_db,
            "db_total_files": db_files,
            "db_total_bytes": db_bytes,
            
            # Status
            "status": "ready" if self.server.upload_stats.get('active_connections', 0) < 5 else "busy"
        }
        
        return stats


# Convenience functions for quick start
def start_multicast_monitoring(server_instance, **kwargs) -> MulticastMonitor:
    """Start multicast monitor and return instance for later control."""
    monitor = MulticastMonitor(server_instance, **kwargs)
    monitor.start()
    return monitor
