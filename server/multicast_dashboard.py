"""
Simple Multicast Monitoring Dashboard
Receives and displays server statistics broadcast via multicast.

Usage:
    python -m server.multicast_dashboard
    
Or standalone:
    cd d:\LTM\nhomltmck
    python server\multicast_dashboard.py
"""
import socket
import json
import struct
import sys
from datetime import datetime
from typing import Dict, Any


class MulticastDashboard:
    """Simple console dashboard that listens to multicast server stats."""
    
    def __init__(
        self,
        multicast_group: str = "239.0.0.1",
        multicast_port: int = 5555
    ):
        self.multicast_group = multicast_group
        self.multicast_port = multicast_port
        self.socket: socket.socket | None = None
        self.servers: Dict[str, Dict[str, Any]] = {}  # server_id -> latest stats
        
    def start(self):
        """Start listening to multicast broadcasts."""
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to multicast port (all interfaces)
            self.socket.bind(('', self.multicast_port))
            
            # Join multicast group
            mreq = struct.pack("4sl", socket.inet_aton(self.multicast_group), socket.INADDR_ANY)
            self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            print("=" * 70)
            print("📡 Multicast Monitoring Dashboard")
            print("=" * 70)
            print(f"Listening on: {self.multicast_group}:{self.multicast_port}")
            print("Waiting for server broadcasts...")
            print("-" * 70)
            print()
            
            self._listen_loop()
            
        except KeyboardInterrupt:
            print("\n\n[Dashboard] Stopped by user")
        except Exception as e:
            print(f"[Dashboard] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.socket:
                self.socket.close()
                
    def _listen_loop(self):
        """Main loop: receive and display stats."""
        while True:
            try:
                data, addr = self.socket.recvfrom(2048)
                stats = json.loads(data.decode('utf-8'))
                self._update_display(stats, addr)
            except json.JSONDecodeError as e:
                print(f"[Warning] Invalid JSON from {addr}: {e}")
            except Exception as e:
                print(f"[Error] {e}")
                
    def _update_display(self, stats: Dict[str, Any], addr: tuple):
        """Update and display server statistics."""
        server_id = stats.get('server_id', 'unknown')
        self.servers[server_id] = stats
        
        # Clear screen (optional, comment out if causes issues)
        # print("\033[2J\033[H", end="")
        
        # Print header
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\r[{now}] Received from {addr[0]}", end="", flush=True)
        print()
        
        # Display stats for all known servers
        print("\n" + "=" * 70)
        print("📊 Active Servers")
        print("=" * 70)
        
        for sid, s in self.servers.items():
            uptime_min = s.get('uptime_seconds', 0) // 60
            status_emoji = "🟢" if s.get('status') == 'ready' else "🔴"
            
            print(f"\n{status_emoji} Server: {s.get('host', '?')}:{s.get('port', '?')} ({sid})")
            print(f"   Status: {s.get('status', 'unknown').upper()}")
            print(f"   Uptime: {uptime_min} minutes")
            print(f"   Active Connections: {s.get('active_connections', 0)}")
            print(f"   Files Uploaded (session): {s.get('total_files', 0)}")
            print(f"   Bytes Uploaded (session): {self._format_bytes(s.get('total_bytes', 0))}")
            
            if s.get('db_enabled'):
                print(f"   📦 Database Stats:")
                print(f"      • Total Files (DB): {s.get('db_total_files', 0)}")
                print(f"      • Total Bytes (DB): {self._format_bytes(s.get('db_total_bytes', 0))}")
            
            print(f"   Last Update: {s.get('timestamp', 'N/A')}")
        
        print("\n" + "=" * 70)
        print("Press Ctrl+C to stop")
        print("-" * 70 + "\n")
        
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"


def main():
    """Entry point for dashboard."""
    # Allow custom group/port via command line
    if len(sys.argv) > 2:
        group = sys.argv[1]
        port = int(sys.argv[2])
        dashboard = MulticastDashboard(multicast_group=group, multicast_port=port)
    else:
        # Use defaults from config
        try:
            from server.server_config import MULTICAST_GROUP, MULTICAST_PORT
            dashboard = MulticastDashboard(
                multicast_group=MULTICAST_GROUP,
                multicast_port=MULTICAST_PORT
            )
        except Exception:
            # Fallback defaults
            dashboard = MulticastDashboard()
    
    dashboard.start()


if __name__ == "__main__":
    main()
