# Frontend Architecture & Component Reference

---

## 1. Frontend Technology Stack

- **Framework**: React 19 (`react`, `react-dom`) with TypeScript
- **Bundler & Build Tool**: Vite 8 with Hot Module Replacement (HMR)
- **Routing**: React Router DOM 7 (`BrowserRouter`, `Routes`, `Route`, `Link`, `useNavigate`, `useParams`)
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite`) + Lucide React icon library
- **Design Language**: Dark-emerald industrial aesthetic with slate neutral backgrounds, high-contrast monospace status pills, and glassmorphism accents.

---

## 2. Directory Structure

```
frontend/src/
├── App.tsx                     # Main Router Configuration & View Routes
├── index.css                   # Tailwind CSS styling & custom utility rules
├── main.tsx                    # React Root Mountpoint
├── api/
│   └── index.ts                # Centralized REST Client & TypeScript Interfaces
├── components/
│   ├── Layout.tsx              # Sidebar navigation, refinery header, and air-gap pill
│   ├── StepTimeline.tsx        # Vertical step execution timeline sequence
│   ├── StepItem.tsx            # Rich step card renderer (tool called, params, result)
│   ├── TaskOutputView.tsx      # Multi-type output renderer (OCR, DocGen, Code, Text)
│   ├── TaskStatusBadge.tsx     # Color-coded task status badge (pending, running, done, etc.)
│   ├── TaskTypeBadge.tsx       # Task type indicator badge (ocr, code_exec, doc_gen, etc.)
│   └── ToolBadge.tsx           # Tool badge with specialized icons & execution tags
└── views/
    ├── ChatView.tsx            # OmniAI Autonomous Studio (interactive chat & dispatcher)
    ├── UploadView.tsx          # Multi-format document upload & vision extraction portal
    ├── TaskListView.tsx        # Historical tasks ledger with filters & search
    ├── TaskDetailView.tsx      # Comprehensive task audit view with timeline & approval gate
    ├── EquipmentGraphView.tsx  # Interactive equipment knowledge graph & multi-criteria query
    ├── EquipmentDetailView.tsx # Deep-dive equipment historical trendline & event timeline
    └── MonitorView.tsx         # Live air-gap security sniffer & active network socket monitor
```

---

## 3. View-by-View Breakdown

### 1. `ChatView.tsx` — OmniAI Sovereign Studio
- **Purpose**: Interactive conversational workspace allowing engineers to type natural language commands, attach documents, execute Python calculations, query historical task ledgers, and draft official SOP documents.
- **Key State Variables**:
  - `messages: ChatMessage[]`: Array of conversation messages persisted to `localStorage` (`mrpl_omni_chat_history`).
  - `inputValue: string`: Current prompt in the composer textarea.
  - `attachedFile: { name: string; path: string } | null`: Uploaded document attachment reference.
  - `isProcessing: boolean`: Disables composer while task initialization is active.
- **Key Functions**:
  - `handleSendMessage(promptToSend?)`: Creates an auto-routed task via `createAutoTask()`, pushes a placeholder assistant message into state, and initiates polling.
  - `handleFileUpload(e)`: Uploads PDF/image via `uploadFile()` and attaches the returned storage path.
  - `handleRefreshTask(taskId)`: Updates task output in place when background processing or human approval completes.
  - `handleRetry(prompt, file)`: Re-dispatches failed tasks.
  - `handleClearHistory()`: Resets conversation history and clears localStorage.

---

### 2. `UploadView.tsx` — OCR & Document Vision Portal
- **Purpose**: Drag-and-drop document upload interface supporting `.pdf`, `.png`, `.jpg`, `.jpeg`, and `.docx` files.
- **Key Features**:
  - Live upload progress indicator.
  - Automatic task creation with `task_type: "ocr"`.
  - Immediate redirect to `TaskDetailView` or live trace stream upon dispatch.

---

### 3. `TaskListView.tsx` — Operational Task Ledger
- **Purpose**: Comprehensive table of all tasks executed on the on-premise workbench.
- **Key Features**:
  - Real-time search by task ID or prompt text.
  - Filtering by `task_type` (`ocr`, `code_exec`, `doc_gen`, `cross_doc_query`, `text_gen`).
  - Filtering by `status` (`pending`, `running`, `done`, `failed`, `pending_approval`, `rejected`).
  - One-click navigation to full execution traces and artifact downloads.

---

### 4. `TaskDetailView.tsx` — Task Audit & Supervisor Approval Gate
- **Purpose**: Complete audit trail showing task parameters, input/output artifacts, step-by-step tool execution timeline, and the human supervisor approval form for generated documents.
- **Key Features**:
  - Live polling of active task steps.
  - Supervisor Decision Form: Enter reviewer name and notes, then click **Approve** or **Reject**.
  - Output artifact download buttons: Word (`.docx`) and Plain Text (`.txt`).

---

### 5. `EquipmentGraphView.tsx` — Equipment Knowledge Graph & Query
- **Purpose**: Visual exploration of all registered plant equipment units (pumps, turbines, boilers, heat exchangers, valves).
- **Key Features**:
  - Filter equipment by refinery unit (e.g. CDU, HCU, FCCU, Pump House 3).
  - Multi-criteria graph search: Event type, compliance status, date range, and predictive violation flags.
  - Quick health summary cards for each machine.

---

### 6. `EquipmentDetailView.tsx` — Machine Evolution & Predictive Trendlines
- **Purpose**: Deep-dive machine history showing inspection event chains and linear regression trend projections.
- **Key Features**:
  - Predictive Trend Canvas: Plots historical vibration/temperature readings alongside future projected data points.
  - Calculates **Days to Threshold Violation** (e.g., alert when vibration will cross 4.5 mm/s ISO limit).
  - Historical inspection timeline with linked source task traces.

---

### 7. `MonitorView.tsx` — Zero-Cloud Air-Gap Telemetry Sniffer
- **Purpose**: Live security monitoring dashboard proving 100% offline isolation.
- **Key Features**:
  - Inspects active network connections via backend `psutil` scanner.
  - Classifies connections: `local` (127.0.0.1 / internal) vs `external`.
  - Prominently displays Air-Gap Status badge: `100% AIR-GAPPED & VERIFIED`.

---

## 4. Reusable UI Components

### 1. `TaskOutputView.tsx`
- Renders specialized output views depending on `task.task_type`:
  - **`ocr`**: Interactive tabbed view (Structured Field Tables vs Raw JSON).
  - **`code_exec`**: Terminal-styled block with output stream, exit codes, and timeout warnings.
  - **`doc_gen`**: Executive Word document preview, supervisor approval form, and download button.
  - **`cross_doc_query`**: Cross-task synthesized intelligence summary with clickable source task chips.
  - **`text_gen`**: Direct synthesized answer with rich markdown parsing.
- Includes `RichMarkdownText` sub-component to render headers, bold text, bullet lists, and code blocks with 1-click copying.

### 2. `StepTimeline.tsx` & `StepItem.tsx`
- Renders the vertical chronological execution trace of an agent task.
- Displays step number, description, execution tool badge, execution time, and expandable JSON payload inspector.

---

## 5. API Client Layer (`frontend/src/api/index.ts`)

Centralized TypeScript module for all backend REST communications:

| Function | Method & URL | Description |
| :--- | :--- | :--- |
| `uploadFile(file)` | `POST /files/upload` | Uploads document to local backend storage |
| `createTask(task_type, input_ref, source_task_id?)` | `POST /tasks/` | Creates explicit task |
| `createAutoTask(prompt, filePath?, sourceTaskId?)` | `POST /tasks/auto` | Creates auto-routed task from natural language |
| `fetchTasks()` | `GET /tasks/` | Retrieves all task ledger records |
| `fetchTaskDetails(id)` | `GET /tasks/{id}` | Fetches task record with all execution steps |
| `approveTask(id, payload)` | `POST /tasks/{id}/approve` | Submits supervisor approval/rejection decision |
| `fetchAllEquipment()` | `GET /graph/equipment` | Fetches equipment summaries |
| `fetchEquipmentDetail(eqId)` | `GET /graph/equipment/{id}` | Fetches equipment history & event records |
| `fetchEquipmentTrend(eqId, field, horizon)` | `GET /graph/equipment/{id}/trend` | Calculates predictive linear regression trend |
| `queryEquipmentGraph(criteria)` | `POST /graph/query` | Executes multi-criteria equipment graph search |
| `fetchNetworkStatus()` | `GET /monitor/connections` | Fetches active network connections & air-gap status |
| `fetchHealthStatus()` | `GET /health` | Fetches system health, DB status & Ollama model list |
| `getDocxDownloadUrl(id)` | `GET /tasks/{id}/output/docx` | Generates direct URL to download Word document |
| `getTextDownloadUrl(id)` | `GET /tasks/{id}/output` | Generates direct URL to download plain text |
