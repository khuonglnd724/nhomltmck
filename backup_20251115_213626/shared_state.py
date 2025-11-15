"""Shared state module to allow HTTP layer to report TCP server status.

The combined runner will set `tcp_server` to the active instance of
`FileUploadServer`. The FastAPI app can then read lightweight stats
without tight coupling.
"""
from __future__ import annotations
from typing import Optional

try:
    from server.server import FileUploadServer  # when imported as package
except Exception:  # pragma: no cover
    try:
        from server import FileUploadServer  # fallback
    except Exception:
        FileUploadServer = None  # type: ignore

tcp_server: Optional[FileUploadServer] = None
