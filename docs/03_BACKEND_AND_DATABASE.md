# Backend Architecture & Database Reference

---

## 1. Backend Technology Stack

- **Web Framework**: FastAPI (Python 3.11+) with AsyncIO
- **Server Engine**: Uvicorn ASGI server with hot-reload (`uvicorn.workers.UvicornWorker`)
- **ORM & Database Engine**: SQLAlchemy 2.0 (Async Session) + `asyncpg` (PostgreSQL) + `aiosqlite` (SQLite Fallback)
- **Data Validation**: Pydantic v2 (`BaseModel`, `Field`)
- **Document Processing**: `python-docx` (Word synthesis), `pypdf` & `pypdfium2` (PDF text layer & rendering), `Pillow` (image optimization)
- **Vector Database**: ChromaDB (air-gapped local embeddings via `sentence-transformers`)
- **System Monitoring**: `psutil` (Socket connection inspection)

---

## 2. Directory Structure

```
backend/
├── .env                        # Environment variables (DATABASE_URL, etc.)
├── alembic.ini                 # Database migration config
├── seed.py                     # Initial test data seeder
├── requirements.txt            # Python dependencies
├── app/
│   ├── main.py                 # FastAPI application, CORS, lifespan, router inclusion
│   ├── database.py             # Dual-engine DB resolver (Postgres + SQLite auto-fallback)
│   ├── schemas.py              # Pydantic input/output validation schemas
│   ├── models/                 # SQLAlchemy ORM models & OCR helpers
│   ├── routers/                # REST API routers (/tasks, /files, /health, /graph, etc.)
│   ├── services/               # Background task processor & worker loop
│   ├── agent/                  # Multi-step agent loops & multi-agent docgen
│   ├── router/                 # Auto-intent router & dynamic model switcher
│   ├── rules/                  # Deterministic mathematical rule engine
│   ├── memory/                 # Long-term evolving entity memory layer
│   ├── graph/                  # Equipment knowledge graph & predictive trends
│   ├── rag/                    # ChromaDB vector knowledge base & corrective grading
│   ├── sandbox/                # Isolated subprocess Python execution engine
│   ├── docgen/                 # Word document (.docx) builder
│   ├── cache/                  # Semantic embedding response cache
│   └── monitor/                # psutil air-gap network socket monitor
└── scripts/                    # Test suites & seeders
```

---

## 3. Database Layer & Dual-Engine Resolver (`database.py`)

The application automatically checks if a local PostgreSQL database is responsive on port `5433`. If unavailable (or when running without Docker), it dynamically falls back to an on-disk SQLite database (`./storage/sovereign.db`).

### Resolver Implementation:
```python
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
        return "sqlite+aiosqlite:///./storage/sovereign.db"
```

---

## 4. Database Schema & ORM Models

### 1. `Task` (`tasks` table)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (Primary Key) | Unique task identifier |
| `task_type` | `Enum` (`TaskType`) | `ocr`, `text_gen`, `doc_gen`, `code_exec`, `cross_doc_query` |
| `status` | `Enum` (`TaskStatus`) | `pending`, `running`, `done`, `failed`, `pending_approval`, `rejected` |
| `input_ref` | `String` / `Text` | User prompt text or uploaded document file path |
| `output_ref` | `Text` (Nullable) | Synthesized output, JSON extraction, or error detail |
| `confidence_score`| `Float` (Nullable) | Calculated safety grounding confidence (0.0 to 100.0) |
| `source_task_id` | `UUID` (Nullable) | References upstream source task for conversational chaining |
| `created_at` | `DateTime` | Timestamp of creation (UTC) |
| `updated_at` | `DateTime` | Timestamp of latest state change |

### 2. `TaskStep` (`task_steps` table)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (Primary Key) | Unique step identifier |
| `task_id` | `UUID` (Foreign Key) | References `tasks.id` |
| `step_number` | `Integer` | Chronological execution index (1, 2, 3...) |
| `description` | `String` | Human-readable action description |
| `tool_called` | `String` (Nullable) | Tool identifier (e.g. `agent_extractor`, `search_kb`, `run_code`) |
| `tool_result` | `JSON` (Nullable) | Structured JSON output or diagnostic trace payload |
| `created_at` | `DateTime` | Execution timestamp |

### 3. `EquipmentNode` (`equipment_nodes` table)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (Primary Key) | Unique node identifier |
| `equipment_id` | `String` (Indexed) | Equipment Tag ID (e.g. `PMP-204`, `TRB-1105`) |
| `equipment_name` | `String` (Nullable) | Equipment Name (e.g. `Crude Distillation Centrifugal Pump`) |
| `unit` | `String` (Nullable) | Refinery Unit (e.g. `CDU`, `HCU`, `FCCU`) |
| `equipment_type` | `String` (Nullable) | `pump`, `turbine`, `boiler`, `heat_exchanger`, `valve` |
| `events_count` | `Integer` | Total recorded events |

### 4. `EquipmentEvent` (`equipment_events` table)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (Primary Key) | Unique event identifier |
| `equipment_node_id`| `UUID` (Foreign Key) | References `equipment_nodes.id` |
| `source_task_id` | `UUID` (Nullable) | References originating `tasks.id` |
| `event_type` | `String` | `inspection`, `anomaly`, `approval_note`, `maintenance` |
| `event_date` | `DateTime` | Timestamp of event occurrence |
| `event_data` | `JSON` | Structured measurements (vibration RMS, temperature, status) |

### 5. `MemoryEntry` (`memory_entries` table)
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` (Primary Key) | Unique memory identifier |
| `entity_key` | `String` (Indexed) | Target entity (e.g. `TRB-1105`) |
| `summary_text` | `Text` | Consolidated summary of facts |
| `strength_score` | `Float` | Initial memory strength (0.0 to 100.0) |
| `last_accessed` | `DateTime` | Timestamp of most recent recall |
| `superseded_by` | `UUID` (Nullable) | References newer memory entry if facts changed |

---

## 5. API Endpoints Reference

### Tasks Router (`/tasks`)
- `POST /tasks/auto` — Unified natural language entrypoint. Automatically classifies intent, creates task, logs router step, and triggers background execution.
- `POST /tasks/` — Explicit task creation endpoint.
- `GET /tasks/` — Returns list of all recorded tasks.
- `GET /tasks/{id}` — Returns task details including chronological execution steps.
- `POST /tasks/{id}/approve` — Human Approval Gate: Submits supervisor decision (`approved: true/false`), unlocks Word download.
- `GET /tasks/{id}/output` — Returns plain text output (`output.txt` or `output_ref`).
- `GET /tasks/{id}/output/docx` — Downloads generated Word document (`output.docx`). Locked if task is `pending_approval` or `rejected`.

### Files Router (`/files`)
- `POST /files/upload` — Multipart form file upload. Stores file in `./storage/uploads/` and returns metadata.

### Graph Router (`/graph`)
- `GET /graph/equipment` — Returns list of all equipment summaries.
- `GET /graph/equipment/{equipment_id}` — Returns full equipment history & events.
- `GET /graph/equipment/{equipment_id}/trend` — Computes predictive linear regression trend (e.g., vibration RMS velocity over time).
- `POST /graph/query` — Executes multi-criteria equipment graph search.

### Memory Router (`/memory`)
- `POST /memory/search` — Queries long-term evolving memory with entity decay weighting.
- `GET /memory/entity/{entity_key}` — Returns evolution history chain for a specific equipment entity.

### Monitor Router (`/monitor`)
- `GET /monitor/connections` — Returns active network sockets, local/external classification, and air-gap verification status.

### Health Router (`/health`)
- `GET /health` — Returns system health status, DB connectivity, and active Ollama model names.
