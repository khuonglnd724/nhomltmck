"""Run both the TCP socket server and the FastAPI HTTP/HTTPS API together.

Usage (PowerShell):
  pip install -r requirements.txt
  $env:ENABLE_DB = "true"  # optional
  python -m server.run_combined

Set HTTPS environment variables for TLS:
  $env:ENABLE_HTTPS = "true"
  $env:SSL_CERTFILE = "C:\path\cert.pem"
  $env:SSL_KEYFILE = "C:\path\key.pem"

Press CTRL+C to stop. Uvicorn handles the signal; TCP server thread will exit when process ends.
"""
from __future__ import annotations
import os
import threading
import uvicorn

from server.server import FileUploadServer
from server import shared_state

# Optional UDP import; only used when ENABLE_UDP
try:
    from server.udp_server import UDPServer
except Exception:
    UDPServer = None  # type: ignore

# Load config with fallbacks
try:
    from server.server_config import (
        SERVER_PORT as CFG_TCP_PORT,
        HTTP_HOST as CFG_HTTP_HOST,
        HTTP_PORT as CFG_HTTP_PORT,
        ENABLE_UDP as CFG_ENABLE_UDP,
        UDP_PORT as CFG_UDP_PORT,
    )
except Exception:
    CFG_TCP_PORT = 9999
    CFG_HTTP_HOST = "127.0.0.1"
    CFG_HTTP_PORT = 8000
    CFG_ENABLE_UDP = True
    CFG_UDP_PORT = 9998


def start_tcp():
    tcp = FileUploadServer()
    shared_state.tcp_server = tcp
    tcp.start()  # blocking loop until shutdown


def start_udp():
    # Determine ports from config, allow env overrides if present
    tcp_port = int(os.getenv("TCP_PORT", str(CFG_TCP_PORT)))
    http_port = int(os.getenv("HTTP_PORT", str(CFG_HTTP_PORT)))
    udp_port = int(os.getenv("UDP_PORT", str(CFG_UDP_PORT)))
    if UDPServer is None:
        print("[UDP] UDPServer module not available; skipping UDP")
        return
    udp = UDPServer(udp_port=udp_port, tcp_port=tcp_port, http_port=http_port)
    udp.start()  # blocking loop


def start_http():
    host = os.getenv("HTTP_HOST", str(CFG_HTTP_HOST))
    port = int(os.getenv("HTTP_PORT", str(CFG_HTTP_PORT)))
    enable_https = os.getenv("ENABLE_HTTPS", "false").lower() in ("1", "true", "yes")
    certfile = os.getenv("SSL_CERTFILE")
    keyfile = os.getenv("SSL_KEYFILE")
    ssl_kw = {}
    if enable_https and certfile and keyfile:
        ssl_kw = {"ssl_keyfile": keyfile, "ssl_certfile": certfile}
    uvicorn.run("server.http_app:app", host=host, port=port, reload=False, **ssl_kw)


def main():
    print("=" * 70)
    print("Combined TCP + UDP + HTTP/HTTPS Server")
    print("=" * 70)
    # Start TCP server in background daemon thread
    t_tcp = threading.Thread(target=start_tcp, name="TCPServerThread", daemon=True)
    t_tcp.start()
    # Start UDP server based on config/env flag
    enable_udp_env = os.getenv("ENABLE_UDP")
    if enable_udp_env is not None:
        enable_udp = enable_udp_env.lower() in ("1", "true", "yes")
    else:
        enable_udp = bool(CFG_ENABLE_UDP)

    if enable_udp:
        t_udp = threading.Thread(target=start_udp, name="UDPServerThread", daemon=True)
        t_udp.start()
    else:
        print("[UDP] Disabled by configuration (ENABLE_UDP=false)")
    # Start HTTP server (blocking)
    start_http()


if __name__ == "__main__":
    main()
