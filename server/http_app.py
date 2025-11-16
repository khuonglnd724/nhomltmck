from __future__ import annotations
import os
import time
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from pydantic import BaseModel, Field

from database.config import CONFIG
try:
    from server import shared_state  # package import
except Exception:
    try:
        import shared_state  # local import fallback
    except Exception:  # pragma: no cover
        shared_state = None  # type: ignore
from services import user_service, file_service
from database.db_manager import DB


app = FastAPI(title="File Upload HTTP API", version="1.0.0")


class AuthRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=3, max_length=128)


@app.get("/api/health")
def health():
    tcp_info = None
    if shared_state and getattr(shared_state, "tcp_server", None):
        s = shared_state.tcp_server
        try:
            tcp_info = {
                "host": s.host,
                "port": s.port,
                "active_connections": s.upload_stats.get("active_connections", 0),
                "total_files": s.upload_stats.get("total_files", 0),
                "total_bytes": s.upload_stats.get("total_bytes", 0),
            }
        except Exception:
            tcp_info = {"error": "unavailable"}
    return {"status": "ok", "db_enabled": CONFIG.enabled, "tcp": tcp_info}


@app.post("/api/register")
def register(req: AuthRequest):
    if not CONFIG.enabled:
        raise HTTPException(status_code=503, detail="Database disabled (ENABLE_DB=false)")
    try:
        user_id = user_service.register_user(req.username, req.password)
        return {"user_id": user_id, "username": req.username}
    except Exception as e:
        # Likely duplicate username or DB error
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/login")
def login(req: AuthRequest):
    if not CONFIG.enabled:
        # Cho phép Guest khi DB tắt (chuẩn hóa user_id=1)
        return {"user_id": 1, "username": "Guest"}
    try:
        user_id: Optional[int] = user_service.authenticate_user(req.username, req.password)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"user_id": user_id, "username": req.username}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload(request: Request, file: UploadFile = File(...), user_id: int = Form(0)):
    # For consistency with TCP server: do not persist file bytes to disk.
    filename = file.filename or "unnamed"
    mime = file.content_type or None
    total = 0
    t0 = time.perf_counter()
    ip = request.client.host if request.client else None

    # Database optional handling
    if not CONFIG.enabled:
        # Drain stream to keep behavior consistent and measure
        while True:
            chunk = await file.read(8192)
            if not chunk:
                break
            total += len(chunk)
        dt = max(time.perf_counter() - t0, 1e-6)
        return {
            "status": "success",
            "filename": filename,
            "bytes": total,
            "seconds": round(dt, 4),
            "mbps": round((total / 1024 / 1024) / dt, 4),
            "stored": False,
        }

    # With DB enabled, record file + session lifecycle
    try:
        stored_name = filename  # no physical storage; mirror original
        file_id = file_service.create_file(user_id, filename, stored_name, 0, mime)
        session_id = DB.start_session(user_id, file_id, ip)
        file_service.update_file_status(file_id, 'in_progress')

        while True:
            chunk = await file.read(8192)
            if not chunk:
                break
            total += len(chunk)

        # finalize
        file_service.update_file_size(file_id, total)
        DB.finalize_session(session_id, 'success', total)
        DB.update_daily_stats(total, user_id)
        file_service.update_file_status(file_id, 'success')

        dt = max(time.perf_counter() - t0, 1e-6)
        return {
            "status": "success",
            "file_id": file_id,
            "session_id": session_id,
            "filename": filename,
            "bytes": total,
            "seconds": round(dt, 4),
            "mbps": round((total / 1024 / 1024) / dt, 4),
            "stored": False,
        }
    except Exception as e:
        try:
            # best-effort mark failed
            file_service.update_file_status(file_id, 'error')  # type: ignore[name-defined]
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
def list_files(user_id: int):
    if not CONFIG.enabled:
        raise HTTPException(status_code=503, detail="Database disabled (ENABLE_DB=false)")
    try:
        return {"user_id": user_id, "files": user_service.list_user_files(user_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def stats():
    if not CONFIG.enabled:
        return {"total_files": 0, "total_bytes": 0}
    try:
        return file_service.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
