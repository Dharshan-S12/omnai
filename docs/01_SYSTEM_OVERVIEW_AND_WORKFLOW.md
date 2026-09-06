# MRPL Sovereign On-Prem Agentic AI Workbench
## System Architecture, End-to-End Workflow & Process Tool Matrix

---

## 1. Executive Summary & Core Mission

The **Sovereign On-Prem Agentic AI Workbench** is an industrial-grade, 100% air-gapped cognitive operating system designed specifically for **Mangalore Refinery and Petrochemicals Limited (MRPL)**. 

### Key Characteristics
1. **Zero Cloud Telemetry**: All Large Language Model (LLM) inference, Vision-Language Model (VLM) extraction, vector embeddings, code execution, and data storage occur strictly on local on-premise compute nodes (`localhost` / `127.0.0.1`).
2. **Deterministic Safety Gating**: Combines probabilistic generative AI with deterministic Python rule engines and mandatory human supervisory sign-off gates.
3. **Multi-Agent Specialist Orchestration**: Decomposes complex plant engineering requests into isolated agent roles: Intent Router, Extractor, Rule Engine, Compliance Officer, Drafter, and Verifier.
4. **Persistent Long-Term Memory & Knowledge Graphs**: Retains evolving equipment history, tracks vibration and thermal trendlines over time, and flags predictive maintenance alerts before machinery violations occur.

---

## 2. High-Level System Architecture Diagram

```
+---------------------------------------------------------------------------------------------+
|                                    USER / REFINERY ENGINEER                                 |
+---------------------------------------------------------------------------------------------+
                                              |
                                     (HTTP / React 19 UI)
                                              v
+---------------------------------------------------------------------------------------------+
|                                  FRONTEND CLIENT (Port 5173)                                |
|  - OmniAI Sovereign Chat Studio (ChatView.tsx)       - Equipment Knowledge Graph (GraphView)|
|  - OCR Document Vision Portal (UploadView.tsx)       - Live Air-Gap Security (MonitorView)  |
|  - Human Supervisory Approval Gate (TaskDetailView)  - Task History Ledger (TaskListView)   |
+---------------------------------------------------------------------------------------------+
                                              |
                                      (FastAPI REST APIs)
                                              v
+---------------------------------------------------------------------------------------------+
|                                 FASTAPI BACKEND (Port 8000)                                 |
|  [Routers]: /tasks, /files, /graph, /memory, /kb, /monitor, /health                         |
|  [Middleware]: Zero-Trust CORS, Air-Gap Network Sniffer Loop (psutil)                       |
+---------------------------------------------------------------------------------------------+
                                              |
                         +--------------------+--------------------+
                         |                                         |
                         v                                         v
+------------------------------------+   +----------------------------------------------------+
|         DATABASE PERSISTENCE       |   |              AUTONOMOUS INTENT ROUTER              |
| - PostgreSQL 15 (Port 5433)        |   | - Analyzes query intent (Regex + Semantic)         |
| - SQLite Auto-Fallback (Local DB)  |   | - Classifies task: ocr | code_exec | doc_gen       |
| - Tables: tasks, task_steps,       |   |                    | cross_doc_query | text_gen    |
|   equipment_nodes, memories        |   +----------------------------------------------------+
+------------------------------------+                             |
                                                                   v
+---------------------------------------------------------------------------------------------+
|                                 SOVEREIGN AGENT EXECUTION CORES                             |
|                                                                                             |
| 1. VISION OCR CORE:                                                                         |
|    - pypdf (Text Layer Extraction) + qwen2.5vl:7b (Scanned Page Vision OCR)                 |
|    - Dynamic field extraction (vibration RMS, ISO Zone, oil temp, signatures)               |
|                                                                                             |
| 2. PYTHON SANDBOX EXECUTION CORE:                                                           |
|    - Isolated subprocess runtime (15s timeout, sanitized env, clean tempfs)                 |
|    - Numerical computations (vibration RMS velocity, standard deviations, statistics)       |
|                                                                                             |
| 3. MULTI-AGENT COMPLIANCE DOCGEN PIPELINE:                                                  |
|    - Agent 1: Extractor (JSON parameter normalization)                                      |
|    - Agent 2: Deterministic Rule Engine (Zero-LLM mathematical ISO/SOP threshold validator) |
|    - Agent 3: Compliance Agent & Self-Consistency Ensemble (3-pass majority voting)          |
|    - Agent 4: Drafting Agent (MRPL executive memorandum & python-docx generator)            |
|    - Agent 5: Verifier Agent (Contradiction detection & confidence scoring 0-100%)          |
|    - Human Gate: Mandatory Supervisor Approval before .docx unlock                          |
|                                                                                             |
| 4. LONG-TERM EVOLVING MEMORY & KNOWLEDGE GRAPH:                                             |
|    - Entity decay weighting (Ebbinghaus curve), supersede lineage chains                    |
|    - Equipment Graph nodes & edges (inspections, anomalies, work orders)                    |
|    - Predictive linear regression trend forecasting (days to threshold violation)           |
|                                                                                             |
| 5. VECTOR RAG KNOWLEDGE BASE:                                                               |
|    - ChromaDB vector store + sentence-transformers (all-MiniLM-L6-v2 cached locally)        |
|    - Corrective Retrieval Grading (filters irrelevant SOP chunks before inference)          |
+---------------------------------------------------------------------------------------------+
                                              |
                                      (Localhost HTTP)
                                              v
+---------------------------------------------------------------------------------------------+
|                               LOCAL OLLAMA INFERENCE ENGINE                                 |
|  - qwen2.5:3b (High-throughput reasoning, coding, planning, synthesis)                      |
|  - qwen2.5vl:7b (Multimodal OCR & engineering drawing vision extraction)                    |
|  - qwen2.5:7b-instruct (Deep reasoning & executive document drafting)                       |
|  - deepseek-r1:1.5b (Chain-of-thought logical verification)                                 |
+---------------------------------------------------------------------------------------------+
```

---

## 3. Tool Matrix: Which Tool is Used for Which Single Process

| Process / Capability | Trigger Condition | Primary Tool / Sub-Process | AI Model / Engine | Output Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **Document Vision OCR** | Upload PDF / PNG / JPG | `pdf_inspector`, `pypdf`, `ocr_extract_fields` | `qwen2.5vl:7b` | Structured JSON + Raw Text |
| **Numerical Calculation** | Math keywords (`calculate`, `RMS`, `prime`, `numpy`) | `code_sandbox` (Subprocess runner) | `qwen2.5:3b` | STDOUT execution + Verified answer |
| **SOP Document (.docx) Generation** | DocGen keywords (`draft SOP`, `word doc`, `export docx`) | `agent_extractor` $\rightarrow$ `rule_engine_check` $\rightarrow$ `agent_compliance` $\rightarrow$ `agent_drafter` $\rightarrow$ `agent_verifier` $\rightarrow$ `generate_docx` | `qwen2.5:3b` / `qwen2.5:7b` + Python Rule Engine | `.docx` Word Document + Executive Memo + Confidence Score |
| **Historical Ledger Analysis** | Ledger keywords (`previous`, `history`, `recent`, `ledger`) | `search_memory` + `cross_doc_fetch` + `cross_doc_synthesizer` | `qwen2.5:3b` | Executive Cross-Task Briefing |
| **Regulatory SOP RAG Search** | SOP keywords (`sop`, `policy`, `guideline`) | `search_kb` (ChromaDB) + `corrective_rag_grade` | `all-MiniLM-L6-v2` + `qwen2.5:3b` | Kept grounded context chunks |
| **Long-Term Memory Recall** | Equipment query (`TRB-1105`, `PMP-204`) | `search_memory` (decay calculation & supersede tracking) | Relational SQL + Decay Formula | Current & linked superseded entities |
| **Predictive Trend Forecast** | Graph trend API / equipment view | `calculate_linear_trend` (Least Squares regression) | Pure Python Numerical SciPy | Days to threshold + R² confidence |
| **Air-Gap Telemetry Watch** | Background daemon loop (2s interval) | `get_system_network_connections` (`psutil`) | OS Socket Scanner | Network security connection log |
| **Human Approval Sign-off** | Generated DocGen task review | `human_approval` (POST `/tasks/{id}/approve`) | Human Supervisor | Unlocked `.docx` download + Audit Stamp |
