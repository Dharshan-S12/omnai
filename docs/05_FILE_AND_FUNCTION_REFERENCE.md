# Complete File-by-File & Function-by-Function Reference

This document provides a comprehensive code inventory of every file, function, class, and tool in the repository.

---

## 1. Backend Core & Server Files

### `backend/app/main.py`
- **Purpose**: Application bootstrap, lifespan management, database initialization, CORS configuration, and router aggregation.
- **Key Functions**:
  - `lifespan(app: FastAPI)`: Async context manager. Enforces air-gap environment flags (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`), runs table creation / migration checks, and starts the background `network_watch` sniffer loop.
  - `app`: Main FastAPI instance configured with CORS middleware and all route inclusions (`health`, `files`, `tasks`, `kb`, `memory`, `graph`, `monitor`).

---

### `backend/app/database.py`
- **Purpose**: Dual-engine database connection manager and session factory.
- **Key Functions**:
  - `resolve_db_url(url: str) -> str`: Tests if PostgreSQL port 5433 is responsive within 500ms; falls back to `sqlite+aiosqlite:///./storage/sovereign.db` if unreachable.
  - `get_db()`: Async dependency injection yielding SQLAlchemy `AsyncSession` for FastAPI route handlers.
- **Key Objects**:
  - `engine`: SQLAlchemy async engine instance.
  - `AsyncSessionLocal`: Sessionmaker bound to the active engine.
  - `Base`: Declarative base for ORM models.

---

### `backend/app/schemas.py`
- **Purpose**: Pydantic v2 schemas for request validation and response serialization.
- **Key Classes**:
  - `TaskBase`, `TaskCreate`, `AutoTaskCreate`: Payload models for task dispatching.
  - `TaskApprovalRequest`: Validates reviewer decisions (`approved: bool`, `reviewer_name: str`, `reviewer_notes: str`).
  - `TaskStepSchema`: Schema for individual execution step objects.
  - `TaskWithSteps`: Complete task response schema including the chronological step sequence.

---

### `backend/app/services/task_processor.py`
- **Purpose**: Primary asynchronous task executor invoked by FastAPI `BackgroundTasks`.
- **Key Functions**:
  - `log_step(db, task_id, step_number, description, tool_called, tool_result) -> TaskStep`: Persists an individual agent action step to the database.
  - `process_task(task_id: UUID)`: Main dispatcher:
    - If `task_type == "cross_doc_query"`: Calls `run_cross_doc_query()`.
    - If `task_type in ("doc_gen", "text_gen", "code_exec")`: Calls `run_agent()`.
    - If `task_type == "ocr"`: Runs `process_pdf_document()` or `classify_document_type()` + `extract_structured_fields()`, saves outputs, and ingests facts into Long-Term Memory and Equipment Graph.

---

## 2. Intent Routing & Dynamic Model Switching

### `backend/app/router/task_router.py`
- **Purpose**: Intent classification and default task routing.
- **Key Functions**:
  - `auto_detect_task_intent(prompt: str, file_path: Optional[str]) -> Tuple[str, str, str]`: Analyzes prompts using regex patterns for math, document generation, cross-doc ledger, or OCR. Returns `(task_type, routing_reason, model_name)`.
  - `route_task(task_type: str, input_ref: str) -> ModelChoice`: Fallback synchronous model mapper.

---

### `backend/app/router/model_router.py`
- **Purpose**: Dynamic model selection, capability priority tiers, installed model probing, and confidence escalation.
- **Key Classes & Enums**:
  - `ModelCategory`: Enum (`VISION`, `FAST_INFERENCE`, `CODING`, `REASONING`, `GENERAL`).
  - `ModelRouteDecision`: Dataclass containing `model_name`, `category`, `reason`, and `timeout_seconds`.
- **Key Functions**:
  - `get_installed_models(force_refresh: bool) -> List[str]`: Probes local Ollama instance (`GET /api/tags`) and caches active models.
  - `detect_category(task_type, prompt, is_vision, category_hint) -> ModelCategory`: Maps semantics to optimal category.
  - `route_model(task_type, prompt, is_vision, category_hint) -> ModelRouteDecision`: Dynamically picks the best available model with adaptive timeouts.
  - `generate_with_escalation(...) -> Tuple[str, Dict]`: Attempts fast 3B model generation; escalates to 7B if hedging or brief answers are detected.

---

## 3. Sovereign Agent Loops & Specialist Pipelines

### `backend/app/agent/loop.py`
- **Purpose**: General multi-step sovereign agent loop for code execution, reasoning, and document drafting.
- **Key Functions**:
  - `extract_python_code(raw_text: str) -> str`: Extracts executable code from markdown fences.
  - `parse_plan_json(raw_text, task_type, input_text) -> List[Dict]`: Parses model plan JSON with heuristic keyword fallbacks.
  - `run_agent(task_id: UUID, task_type: str, input_text: str)`: 3-phase sovereign agent loop:
    1. **Plan**: Model planner generates a 2-3 step execution plan.
    2. **Act & Observe**: Executes tools (`search_memory`, `search_kb`, `run_code`, `generate_text`).
    3. **Synthesize & Critique**: Generates authoritative final response and runs self-critique.

---

### `backend/app/agent/multi_agent_docgen.py`
- **Purpose**: 5-agent sequential specialist pipeline for compliance documents (.docx).
- **Key Functions**:
  - `run_multi_agent_docgen_pipeline(...)`:
    - **Extractor Agent (`agent_extractor`)**: Normalizes parameters into JSON.
    - **Rule Engine (`rule_engine_check`)**: Pure Python numerical evaluation.
    - **Compliance Agent / Ensemble (`agent_compliance` / `compliance_ensemble`)**: Narrative evaluation with 3-pass self-consistency voting on borderline cases.
    - **Drafting Agent (`agent_drafter`)**: Drafts memorandum and compiles Word document.
    - **Verifier Agent (`agent_verifier`)**: Contradiction cross-check, confidence calculation (0-100%), and hard failure capping at 20%.

---

### `backend/app/agent/cross_doc.py`
- **Purpose**: Multi-document historical ledger synthesis.
- **Key Functions**:
  - `parse_doc_count(query: str, default: int, max_cap: int) -> Tuple[int, bool, Optional[int]]`: Extracts requested record count from natural language (e.g. "past 5 inspections").
  - `run_cross_doc_query(task_id: UUID, query: str)`: Fetches historical task outputs and long-term memory, then synthesizes a cross-plant executive briefing.

---

## 4. Deterministic Rule Engine

### `backend/app/rules/rule_engine.py`
- **Purpose**: Exact mathematical threshold evaluation with zero LLM variance.
- **Key Functions**:
  - `evaluate_rules(extracted_fields: Dict, sop_reference: Optional[str]) -> Dict`: Matches fields against ISO 10816-3 and MRPL SOPs.
  - `_evaluate_pump_vibration(...)`: Evaluates vibration velocity RMS against Zone A (< 2.8), Zone B (2.8-4.5), Zone C (4.5-7.1), Zone D (> 7.1).
  - `_evaluate_valve_safety(...)`: Evaluates high-pressure valve parameters (pressure, toxic gas, differential pressure).

---

## 5. Long-Term Evolving Memory

### `backend/app/memory/ingest.py`
- **Purpose**: Entity extraction, decay computation, and memory consolidation.
- **Key Functions**:
  - `extract_entity_key(data: Dict) -> str`: Identifies equipment tag (e.g. `PMP-204`).
  - `ingest_memory(task_id, structured_output, doc_type) -> MemoryEntry`: Stores memory, supersedes older records for the same entity, and links cross-entity relations.

### `backend/app/memory/retrieve.py`
- **Purpose**: Memory recall with Ebbinghaus exponential decay weighting.
- **Key Functions**:
  - `calculate_decayed_strength(strength, last_accessed_dt, decay_rate=0.05) -> float`: Calculates current memory strength:
    $$S(t) = S_0 \cdot e^{-\lambda \Delta t}$$
  - `search_memory(query: str, top_k: int = 5) -> List[Dict]`: Retrieves current and linked superseded memory chains.

---

## 6. Equipment Knowledge Graph & Predictive Trends

### `backend/app/graph/ingest.py`
- **Purpose**: Registers equipment nodes and logs chronological inspection events.
- **Key Functions**:
  - `record_equipment_event(task_id, structured_data, event_type) -> EquipmentNode`: Updates or creates equipment nodes, logs event records, and updates machine status.

### `backend/app/graph/trends.py`
- **Purpose**: SciPy / NumPy linear regression trend forecasting over historical data.
- **Key Functions**:
  - `calculate_linear_trend(equipment_id, field, horizon_days) -> Dict`: Performs Least Squares regression ($y = mx + c$), calculates $R^2$ goodness of fit, and computes exact days remaining until threshold violation.

### `backend/app/graph/query.py`
- **Purpose**: Multi-criteria graph querying.
- **Key Functions**:
  - `query_equipment(criteria: Dict) -> Dict`: Filters machines by unit, event type, compliance status, date range, or predictive violation flag.

---

## 7. Vision OCR & PDF Processing

### `backend/app/models/pdf_processor.py`
- **Purpose**: Dual-path PDF text layer extraction and image rendering.
- **Key Functions**:
  - `is_pdf(file_path: str) -> bool`: Checks if file is a PDF.
  - `extract_pdf_text_layer(pdf_path, max_pages=10) -> Tuple[str, int, int]`: Extracts embedded text via `pypdf`.
  - `render_pdf_page_as_image(pdf_path, page_num=0) -> str`: Renders scanned pages to PNG using `pypdfium2` for vision OCR.
  - `process_pdf_document(...) -> Dict`: Orchestrates text vs vision paths.

### `backend/app/models/ocr_classify.py` & `ocr_extract.py`
- **Purpose**: Document type classification and schema extraction using `qwen2.5vl:7b`.
- **Key Functions**:
  - `classify_document_type(image_path, model) -> str`: Classifies image into document categories.
  - `extract_structured_fields(image_path, doc_type, model) -> Dict`: Extracts key-value measurement pairs and tables.

---

## 8. Sandbox, DocGen, Cache & Monitoring

### `backend/app/sandbox/run_code.py`
- **Purpose**: Isolated Python execution.
- **Key Functions**:
  - `run_code(code: str, timeout_seconds: int = 15) -> Dict`: Executes code in an ephemeral temporary directory with sanitized environment and strict timeout.

### `backend/app/docgen/generate_docx.py`
- **Purpose**: Word document compilation via `python-docx`.
- **Key Functions**:
  - `generate_docx(title: str, content: str, output_path: str) -> str`: Builds professional Word documents with MRPL headers, callout boxes, and confidentiality footers.

### `backend/app/cache/semantic_cache.py`
- **Purpose**: Semantic prompt caching using vector cosine similarity.
- **Key Functions**:
  - `lookup_semantic_cache(prompt_text, task_type, threshold=0.92) -> Optional[Dict]`: Returns cached outputs for near-duplicate prompts.
  - `store_semantic_cache(task_id, prompt_text, output_text, task_type, confidence_score)`: Saves high-confidence responses into the cache.

### `backend/app/monitor/network_watch.py`
- **Purpose**: Zero-cloud air-gap socket scanner.
- **Key Functions**:
  - `get_system_network_connections() -> Dict`: Scans network sockets using `psutil`, classifies connections as `local` vs `external`, and verifies air-gap integrity.
  - `start_network_monitor_loop()` / `stop_network_monitor_loop()`: Background daemon thread updating network metrics every 2 seconds.
