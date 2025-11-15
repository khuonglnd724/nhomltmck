"""User service abstraction for future HTTP layer."""
from database.db_manager import DB

def register_user(username: str, password: str) -> int:
    return DB.register_user(username, password)

def authenticate_user(username: str, password: str):
    return DB.authenticate(username, password)

def list_user_files(user_id: int):
    return DB.list_user_files(user_id)
