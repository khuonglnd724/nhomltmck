"""File service layer for future HTTP endpoints."""
from database.db_manager import DB

def create_file(user_id: int, original: str, stored: str, size_bytes: int, file_type: str | None):
    return DB.create_file_record(user_id, original, stored, size_bytes, file_type)

def update_file_status(file_id: int, status: str):
    DB.update_file_status(file_id, status)

def get_stats():
    return DB.get_stats()
