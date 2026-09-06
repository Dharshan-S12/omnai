import os
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ai_user:ai_password@localhost:5433/sovereign_db")
SQLITE_URL = "sqlite+aiosqlite:///./storage/sovereign.db"

IS_SQLITE_FALLBACK = False
FALLBACK_TIMESTAMP: Optional[str] = None
FALLBACK_REASON: Optional[str] = None

def resolve_db_url(url: str) -> str:
    """Check if target Postgres DB port is responsive; otherwise fallback to local SQLite."""
    global IS_SQLITE_FALLBACK, FALLBACK_TIMESTAMP, FALLBACK_REASON
    if "sqlite" in url:
        IS_SQLITE_FALLBACK = True
        FALLBACK_TIMESTAMP = datetime.now(timezone.utc).isoformat()
        FALLBACK_REASON = "Configured explicitly with SQLite URL"
        return url
    try:
        clean_url = url.replace("+asyncpg", "").replace("postgresql://", "http://")
        parsed = urlparse(clean_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5433
        with socket.create_connection((host, port), timeout=0.5):
            IS_SQLITE_FALLBACK = False
            return url
    except Exception as e:
        IS_SQLITE_FALLBACK = True
        FALLBACK_TIMESTAMP = datetime.now(timezone.utc).isoformat()
        FALLBACK_REASON = f"PostgreSQL port {port if 'port' in locals() else 5433} unreachable: {str(e)}"
        os.makedirs("./storage", exist_ok=True)
        print(f"[DB Auto-Detect] PostgreSQL on port {port if 'port' in locals() else 5433} unreachable. Using local SQLite fallback: {SQLITE_URL}")
        return SQLITE_URL

ACTIVE_DB_URL = resolve_db_url(DATABASE_URL)
engine = create_async_engine(ACTIVE_DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

def get_db_health_info() -> Dict[str, Any]:
    """Returns detailed database engine and fallback status metadata for health monitoring."""
    return {
        "active_backend": "sqlite" if IS_SQLITE_FALLBACK else "postgresql",
        "is_fallback": IS_SQLITE_FALLBACK,
        "fallback_timestamp": FALLBACK_TIMESTAMP,
        "fallback_reason": FALLBACK_REASON,
        "integrity_mode": "reduced_integrity_fallback" if IS_SQLITE_FALLBACK else "high_integrity_postgresql",
        "banner_message": (
            "Running in reduced-integrity mode (SQLite fallback) — concurrent multi-user writes and JSON-graph queries may degrade."
            if IS_SQLITE_FALLBACK else None
        )
    }

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
