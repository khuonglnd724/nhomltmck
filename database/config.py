"""Database configuration and factory.
Adjust credentials to match XAMPP MySQL settings.
"""
from dataclasses import dataclass
import os

@dataclass
class DBConfig:
    host: str = os.getenv("DB_HOST", "127.0.0.1")
    port: int = int(os.getenv("DB_PORT", "3306"))
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "123456")  # XAMPP default empty
    database: str = os.getenv("DB_NAME", "fileupload")
    pool_name: str = "fileupload_pool"
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))
    enabled: bool = os.getenv("ENABLE_DB", "true").lower() == "true"

CONFIG = DBConfig()
