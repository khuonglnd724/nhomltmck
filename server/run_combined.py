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


def start_tcp():
    tcp = FileUploadServer()
    shared_state.tcp_server = tcp
    tcp.start()  # blocking loop until shutdown


def start_http():
    host = os.getenv("HTTP_HOST", "127.0.0.1")
    port = int(os.getenv("HTTP_PORT", "8000"))
    enable_https = os.getenv("ENABLE_HTTPS", "false").lower() in ("1", "true", "yes")
    certfile = os.getenv("SSL_CERTFILE")
    keyfile = os.getenv("SSL_KEYFILE")
    ssl_kw = {}
    if enable_https and certfile and keyfile:
        ssl_kw = {"ssl_keyfile": keyfile, "ssl_certfile": certfile}
    uvicorn.run("server.http_app:app", host=host, port=port, reload=False, **ssl_kw)


def main():
    print("=" * 70)
    print("Combined TCP + HTTP/HTTPS Server")
    print("=" * 70)
    # Start TCP server in background daemon thread
    t = threading.Thread(target=start_tcp, name="TCPServerThread", daemon=True)
    t.start()
    # Start HTTP server (blocking)
    start_http()


if __name__ == "__main__":
    main()
