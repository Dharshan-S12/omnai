import os
import socket
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ai_user:ai_password@localhost:5433/sovereign_db")
SQLITE_URL = "sqlite+aiosqlite:///./storage/sovereign.db"

def resolve_db_url(url: str) -> str:
    """Check if target Postgres DB port is responsive; otherwise fallback to local SQLite."""
    if "sqlite" in url:
        return url
    try:
        clean_url = url.replace("+asyncpg", "").replace("postgresql://", "http://")
        parsed = urlparse(clean_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5433
        with socket.create_connection((host, port), timeout=0.5):
            return url
    except Exception:
        os.makedirs("./storage", exist_ok=True)
        print(f"[DB Auto-Detect] PostgreSQL on port {port if 'port' in locals() else 5433} unreachable. Using local SQLite: {SQLITE_URL}")
        return SQLITE_URL

ACTIVE_DB_URL = resolve_db_url(DATABASE_URL)
engine = create_async_engine(ACTIVE_DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

