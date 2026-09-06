import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from app.database import engine, Base
import app.models  # Ensures all models including MemoryEntry and MemoryLink are in Base.metadata

async def run_migrations():
    print("Running database migrations...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_task_id UUID REFERENCES tasks(id);"))
            await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS confidence_score FLOAT;"))
            await conn.execute(text("ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS safety_critical BOOLEAN DEFAULT FALSE;"))
            try:
                await conn.execute(text("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'cross_doc_query';"))
                await conn.execute(text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'pending_approval';"))
                await conn.execute(text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'rejected';"))
            except Exception:
                pass
        elif engine.dialect.name == "sqlite":
            try:
                await conn.execute(text("ALTER TABLE tasks ADD COLUMN confidence_score FLOAT;"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE tasks ADD COLUMN source_task_id VARCHAR(36);"))
            except Exception:
                pass
            try:
                await conn.execute(text("ALTER TABLE memory_entries ADD COLUMN safety_critical BOOLEAN DEFAULT 0;"))
            except Exception:
                pass
        print("Migration complete: all tables (tasks, task_steps, documents, memory_entries, memory_links, equipment_nodes, equipment_events) ensured.")

if __name__ == "__main__":
    asyncio.run(run_migrations())
