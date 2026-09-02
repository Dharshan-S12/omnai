import os
import logging

# Ensure Hugging Face / sentence-transformers and Chroma operate in strictly air-gapped / offline mode
# Note: Requires the embedding model to already be cached locally (from prior runs).
# If the cache is ever missing, this will now cause a clear local error instead of a silent network call, which is intentional.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine, Base
from app.routers import health, files, tasks, kb, monitor
from app.monitor.network_watch import start_network_monitor_loop, stop_network_monitor_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Air-gap security confirmations
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    print("ChromaDB telemetry disabled")
    print("HF offline mode enabled")
    logging.info("ChromaDB telemetry disabled")
    logging.info("HF offline mode enabled")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if engine.dialect.name == "postgresql":
                await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_task_id UUID REFERENCES tasks(id);"))
                try:
                    await conn.execute(text("ALTER TYPE tasktype ADD VALUE IF NOT EXISTS 'cross_doc_query';"))
                except Exception:
                    pass
        print(f"Database initialized successfully ({engine.dialect.name})")
        logging.info(f"Database initialized successfully ({engine.dialect.name})")
    except Exception as db_err:
        print(f"Warning: Database unavailable at startup ({db_err})")
        logging.warning(f"Database unavailable at startup: {db_err}")
    # Start background network watcher (2s loop)
    start_network_monitor_loop()
    yield
    stop_network_monitor_loop()

app = FastAPI(title="Sovereign On-Prem Agentic AI Workbench", version="1.0.0", lifespan=lifespan)

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(files.router)
app.include_router(tasks.router)
app.include_router(kb.router)
app.include_router(monitor.router)
