"""Database manager for MySQL using connection pooling.
Requires: pip install mysql-connector-python
Design: Thin wrapper to keep business logic separated for future HTTP layer.
"""
from __future__ import annotations
import mysql.connector
from mysql.connector import pooling
from typing import Optional, Dict, Any, List
from .config import CONFIG
import hashlib
from datetime import datetime

_pool: Optional[pooling.MySQLConnectionPool] = None

def _init_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name=CONFIG.pool_name,
            pool_size=CONFIG.pool_size,
            pool_reset_session=True,
            host=CONFIG.host,
            port=CONFIG.port,
            user=CONFIG.user,
            password=CONFIG.password,
            database=CONFIG.database
        )

class DatabaseManager:
    def __init__(self):
        if CONFIG.enabled:
            _init_pool()

    def _conn(self):
        if not CONFIG.enabled:
            raise RuntimeError("Database disabled (ENABLE_DB=false)")
        return _pool.get_connection()

    # ---- User operations ----
    def register_user(self, username: str, password: str) -> int:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        cn = self._conn(); cur = cn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s,%s)",
            (username, pw_hash)
        )
        cn.commit(); uid = cur.lastrowid
        cur.close(); cn.close()
        return uid

    def authenticate(self, username: str, password: str) -> Optional[int]:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        cn = self._conn(); cur = cn.cursor()
        cur.execute("SELECT user_id FROM users WHERE username=%s AND password_hash=%s AND is_active=1", (username, pw_hash))
        row = cur.fetchone()
        cur.close(); cn.close()
        return row[0] if row else None

    # ---- File operations ----
    def create_file_record(self, user_id: int, original: str, stored: str, size_bytes: int, file_type: str | None) -> int:
        cn = self._conn(); cur = cn.cursor()
        cur.execute(
            """INSERT INTO files (user_id, original_filename, stored_filename, file_size_bytes, file_type, status)
                VALUES (%s,%s,%s,%s,%s,'pending')""",
            (user_id, original, stored, size_bytes, file_type)
        )
        cn.commit(); fid = cur.lastrowid
        cur.close(); cn.close()
        return fid

    def update_file_status(self, file_id: int, status: str):
        cn = self._conn(); cur = cn.cursor()
        cur.execute("UPDATE files SET status=%s WHERE file_id=%s", (status, file_id))
        cn.commit(); cur.close(); cn.close()

    # ---- Session operations ----
    def start_session(self, user_id: int, file_id: int, ip: str | None) -> int:
        cn = self._conn(); cur = cn.cursor()
        cur.execute(
            "INSERT INTO upload_sessions (user_id, file_id, ip_address, status) VALUES (%s,%s,%s,'in_progress')",
            (user_id, file_id, ip)
        )
        cn.commit(); sid = cur.lastrowid
        cur.close(); cn.close()
        return sid

    def finalize_session(self, session_id: int, status: str, bytes_transferred: int, error_msg: str | None = None):
        cn = self._conn(); cur = cn.cursor()
        cur.execute(
            "UPDATE upload_sessions SET end_time=%s, status=%s, bytes_transferred=%s, error_message=%s WHERE session_id=%s",
            (datetime.now(), status, bytes_transferred, error_msg, session_id)
        )
        cn.commit(); cur.close(); cn.close()

    # ---- Statistics ----
    def update_daily_stats(self, bytes_added: int, user_id: int):
        cn = self._conn(); cur = cn.cursor()
        cur.execute("SELECT stat_date FROM statistics_daily WHERE stat_date=CURDATE()")
        if not cur.fetchone():
            cur.execute("INSERT INTO statistics_daily (stat_date, total_uploads, total_bytes, active_users) VALUES (CURDATE(),0,0,0)")
        cur.execute("UPDATE statistics_daily SET total_uploads=total_uploads+1, total_bytes=total_bytes+%s WHERE stat_date=CURDATE()", (bytes_added,))
        # simplistic active user increment (could be improved):
        cur.execute("UPDATE statistics_daily SET active_users=active_users+1 WHERE stat_date=CURDATE()")
        cn.commit(); cur.close(); cn.close()

    # ---- Query helpers ----
    def list_user_files(self, user_id: int) -> List[Dict[str, Any]]:
        cn = self._conn(); cur = cn.cursor(dictionary=True)
        cur.execute("SELECT file_id, original_filename, file_size_bytes, upload_date, status FROM files WHERE user_id=%s ORDER BY upload_date DESC", (user_id,))
        rows = cur.fetchall(); cur.close(); cn.close()
        return rows

    def get_stats(self) -> Dict[str, Any]:
        cn = self._conn(); cur = cn.cursor()
        cur.execute("SELECT COUNT(*), SUM(file_size_bytes) FROM files WHERE status='success'")
        r = cur.fetchone()
        cur.close(); cn.close()
        return {"total_files": r[0] or 0, "total_bytes": r[1] or 0}

DB = DatabaseManager()
