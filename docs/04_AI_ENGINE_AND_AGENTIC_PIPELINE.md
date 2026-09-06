# AI Architecture, Agentic Pipeline & Sovereign Engine Reference

---

## 1. AI Engine Overview

The AI Engine in the MRPL Sovereign Workbench is built on a **multi-model, agentic architecture**. Rather than treating a generic LLM as a black box, the system orchestrates specialized models, deterministic Python rule engines, isolated sandboxes, and vector stores to deliver verifiable, grounded industrial intelligence.

---

## 2. Intent Detection & Dynamic Model Routing

### A. Intent Auto-Detection (`backend/app/router/task_router.py`)
When a user submits a prompt or attachment to `/tasks/auto`, the `auto_detect_task_intent()` function analyzes the query using a combination of file extension inspection, semantic regex patterns, and keyword intent scoring:

```
                          Incoming Request (/tasks/auto)
                                        |
         +------------------------------+------------------------------+
         |                              |                              |
         v                              v                              v
[Attached Image/PDF?]          [Math / Python Code?]          [Word DocGen / SOP?]
  -> task_type: "ocr"            -> task_type: "code_exec"      -> task_type: "doc_gen"
  -> Model: qwen2.5vl:7b         -> Model: qwen2.5:3b           -> Model: qwen2.5:3b
         |                              |                              |
         +------------------------------+------------------------------+
                                        |
         +------------------------------+------------------------------+
         |                                                             |
         v                                                             v
[Historical Ledger / Anomaly?]                               [General Reasoning / QA]
  -> task_type: "cross_doc_query"                              -> task_type: "text_gen"
  -> Model: qwen2.5:3b                                         -> Model: qwen2.5:3b
```

### B. Dynamic Model Router (`backend/app/router/model_router.py`)
- **Capability Priority Tiers**: Automatically maps task requirements to the best locally installed Ollama model.
- **Adaptive Timeouts**: Allocates 300s for large Vision models, 120s for 3B fast inference models, and 240s for 7B text models.
- **VRAM Thrashing Prevention**: Prioritizes `qwen2.5:3b` across text, coding, and synthesis steps so that multi-step pipelines execute within seconds on GPU VRAM without constant weight unloading.

---

## 3. Multimodal Vision OCR Pipeline (`backend/app/models/`)

When a document (PDF or image) is processed, the system executes a dual-path pipeline:

```
                         Document Upload (PDF / Image)
                                        |
                         +--------------+--------------+
                         |                             |
                         v                             v
               [Is Vector/Digital PDF?]      [Is Scanned Image / Drawing?]
                         |                             |
                         v                             v
                 PATH A: Text Layer            PATH B: Multimodal Vision
                 (pypdf / pypdfium2)                (qwen2.5vl:7b)
                         |                             |
                         +--------------+--------------+
                                        |
                                        v
                       [Document Type Classification]
                   (Routine Pump Inspection, MTR, Valve SOP)
                                        |
                                        v
                       [Structured Field Extraction]
              (Equipment ID, Vibration RMS, ISO Zone, Seal Temp)
                                        |
                         +--------------+--------------+
                         |                             |
                         v                             v
               [Long-Term Memory Store]     [Equipment Knowledge Graph]
```

---

## 4. Multi-Agent Specialist DocGen Pipeline (`backend/app/agent/multi_agent_docgen.py`)

For official document generation (`doc_gen`), the system executes a rigorous 5-stage agentic workflow:

```
[User Request & Context]
         |
         v
+-----------------------------------------------------------------------------------+
| 1. EXTRACTOR AGENT (`agent_extractor` | qwen2.5:3b)                               |
|    - Normalizes technical facts into strict JSON (equipment, parameters, dates).  |
+-----------------------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------------------+
| 2. DETERMINISTIC RULE ENGINE (`rule_engine_check` | Pure Python - Zero LLM)       |
|    - Evaluates exact mathematical thresholds against ISO 10816-3 & MRPL SOPs:     |
|      * Zone A: RMS < 2.8 mm/s (Compliant)                                         |
|      * Zone B: 2.8 <= RMS <= 4.5 mm/s (Alert)                                     |
|      * Zone C: 4.5 < RMS <= 7.1 mm/s (Unsatisfactory)                             |
|      * Zone D: RMS > 7.1 mm/s (Immediate Emergency Shutdown)                      |
+-----------------------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------------------+
| 3. COMPLIANCE AGENT & ENSEMBLE (`agent_compliance` / `compliance_ensemble`)       |
|    - If borderline (within 10% of threshold), triggers 3-pass majority voting.    |
|    - Evaluates mandatory corrective actions without seeing draft text.            |
+-----------------------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------------------+
| 4. DRAFTING AGENT (`agent_drafter` | qwen2.5:3b / qwen2.5:7b)                     |
|    - Generates executive memorandum adhering strictly to rule engine truth.       |
|    - Compiles formal Word document (.docx) with MRPL styling & header.            |
+-----------------------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------------------+
| 5. VERIFIER AGENT (`agent_verifier` | qwen2.5:3b)                                 |
|    - Cross-checks draft against rule engine ground truth and compliance verdict.  |
|    - Computes Safety Confidence Score (0-100%).                                   |
|    - Hard Contradiction Failure: Caps confidence at 20% if numbers conflict.      |
+-----------------------------------------------------------------------------------+
         |
         v
+-----------------------------------------------------------------------------------+
| 6. HUMAN SUPERVISOR SIGN-OFF GATE (`human_approval_gate`)                         |
|    - Status set to `pending_approval`. Word download is cryptographically LOCKED. |
|    - Supervisor reviews in UI and approves -> Status: `done`, download unlocked.  |
+-----------------------------------------------------------------------------------+
```

---

## 5. Deterministic Rule Engine (`backend/app/rules/rule_engine.py`)

A pure Python rule engine with **zero LLM variance**. Evaluates numeric parameters against standard engineering limits:
- **`SOP-MNT-042`** (Pumps & Turbines):
  - Vibration Velocity RMS limit: $\le 2.8\text{ mm/s}$ (Zone A) / $4.5\text{ mm/s}$ (Zone B)
  - Bearing Seal Temperature: $\le 80^\circ\text{C}$
  - Peak Frequency: $10\text{ Hz} - 1000\text{ Hz}$
- **`SOP-SAF-104`** (High-Pressure Valves):
  - Operating Line Pressure: $\le 150\text{ bar}$
  - Toxic Gas Limit: $\le 25\text{ ppm}$
  - Pressure Drop: $\le 40\%$

---

## 6. Long-Term Evolving Memory Layer (`backend/app/memory/`)

1. **Entity Decay Weighting (Ebbinghaus Forgetting Curve)**:
   $$\text{Strength}(t) = S_0 \cdot e^{-\lambda \Delta t}$$
   Recent inspection memories are weighted higher, but old records decay gracefully unless reinforced by new readings.
2. **Supersede Lineage Chains**:
   When new inspection data arrives for equipment (e.g. `PMP-204`), the older memory is marked `is_current: false` and linked via `superseded_by: new_memory_id`.
3. **Cross-Entity Relation Graph**:
   Tracks component links (`PMP-204` is connected to `CDU-Column-1`, `Valve-ESD-101`).

---

## 7. Equipment Knowledge Graph & Predictive Trends (`backend/app/graph/`)

1. **Relational Event Nodes**:
   Tracks every inspection, anomaly, and work order linked to an equipment Tag ID.
2. **Predictive Linear Regression Trendlines (`trends.py`)**:
   Uses SciPy / NumPy Least Squares Linear Regression over historical vibration time-series data:
   $$y = mx + c$$
   - Calculates **Slope per day / month**.
   - Calculates **$R^2$ Statistical Goodness of Fit**.
   - Computes **Days to Threshold Violation**:
     $$\text{Days Remaining} = \frac{\text{Threshold} - \text{Current Value}}{\text{Slope per Day}}$$
   - Flags predictive alert banners in the UI when a machine is projected to breach compliance limits.

---

## 8. Python Sandbox Code Execution (`backend/app/sandbox/run_code.py`)

- **Subprocess Isolation**: Executes dynamically generated Python code inside an ephemeral temporary directory (`tempfile.TemporaryDirectory`).
- **Environment Sanitization**: Strips credentials, API keys, and repository paths from the execution environment.
- **Safety Timeout**: Hard 15-second subprocess execution limit (`subprocess.TimeoutExpired`).

---

## 9. Vector RAG & Corrective Grading (`backend/app/rag/`)

- **ChromaDB Local Vector Storage**: Embedded using local `all-MiniLM-L6-v2` (`sentence-transformers`).
- **Corrective Retrieval Grading**: Before passing retrieved SOP excerpts to the synthesizer, a grading LLM step evaluates each candidate chunk (`yes` / `no`). Irrelevant chunks are discarded to prevent ungrounded hallucinations.

---

## 10. Semantic Response Cache (`backend/app/cache/semantic_cache.py`)

- Computes cosine similarity between incoming user prompts and previously answered high-confidence tasks.
- If similarity exceeds $0.92$ on equivalent task types within a 48-hour window, the verified output is returned instantly with `< 50ms` latency.
