# MRPL Sovereign On-Prem Agentic AI Workbench — Threat Model & Security Specification

**Document Version**: 1.0.0  
**Classification**: MRPL Industrial Safety & Sovereign Computing Standard  
**Deployment Profile**: 100% Air-Gapped On-Premise Industrial Refinery Network  

---

## 1. System Mission & Security Perimeter

The MRPL Sovereign Workbench operates inside an isolated, air-gapped supervisory control and data acquisition (SCADA) / plant intranet zone. The core security mission is:
1. **Zero Exfiltration**: Zero data leaves the local host network interface under any condition.
2. **Deterministic Safety Gating**: Generative probabilistic AI cannot bypass or modify deterministic ISO engineering safety limits.
3. **Tamper-Evident Accountability**: All supervisory actions, model outputs, and rule engine checks are permanently hash-chained in an append-only audit trail.

---

## 2. Threat Actor Profiles & Risk Assessment

| Threat Profile | Description | Capability / Access | Primary Risk Vector |
| :--- | :--- | :--- | :--- |
| **Malicious Insider / Rogue Operator** | Plant operator or field technician attempting unauthorized document approval or record falsification. | Local LAN access, standard operator credentials. | Modifying database rows directly to forge supervisor approvals or bypass vibration violations. |
| **Adversarial / Malformed Document Upload** | Upload of crafted PDFs, images, or documents containing embedded macros, polyglot payloads, or prompt injections. | Web UI upload access (`/files/upload`). | Sandbox escape, memory exhaustion, prompt injection overriding safety checks. |
| **Compromised Local Model Weights** | Altered or poisoned open-weights model in local Ollama storage. | Local filesystem access. | Generating hallucinated PASS verdicts for faulty machinery. |
| **System Misconfiguration / Cloud Leakage** | Erroneous network routing, external dependency phone-home, or misconfigured DNS. | Network stack. | Telemetry leaks to cloud endpoints during vector embeddings or package execution. |

---

## 3. Defense-in-Depth Architecture Matrix

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AIR-GAP PERIMETER                                       │
│  [Enforcement]: OS Host Firewall / Disabled External Gateway / Zero Public DNS Routing    │
│  [Verification]: psutil Continuous Socket Sniffer + Build-time Dependency Call Scanner     │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                     API & ROLE GATING                                     │
│  [Operator Role]: Submits prompts, uploads PDFs, views traces (Raw logs hidden by default)│
│  [Supervisor Role]: Required for POST /tasks/{id}/approve (403 Forbidden for Operators)   │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                DETERMINISTIC SAFETY ENGINE                                │
│  - Pure Python ISO 10816-3 rule engine (Zero LLM variance)                                 │
│  - Authoritative Gating: LLM CANNOT override a rule engine FAIL/Zone C/D to PASS          │
│  - Deterministic Contradiction Detection: Regex parses draft zones vs computed ground truth │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                                  ISOLATED PYTHON SANDBOX                                  │
│  - AST Static Analysis: Blocks subprocess, socket, os.system, pty, ctypes, urllib, etc.   │
│  - Ephemeral TempFS: Working directory destroyed upon execution completion                │
│  - Execution Bounds: Strict 15-second subprocess timeout + memory limits                  │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│                             TAMPER-EVIDENT AUDIT HASH CHAIN                               │
│  - Cryptographic Hash Chaining: H_n = SHA-256(H_{n-1} + Timestamp + Reviewer + DocxHash)  │
│  - Endpoint /audit/verify detects any retrospective database row alteration or tampering  │
│  - External Flat-File Forensic Mirror (storage/audit_forensics.jsonl)                     │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Threat Mitigations & Countermeasures

### A. Malicious Uploads & Prompt Injections
- **Defense**:
  1. Strict MIME type and extension white-listing (`.pdf`, `.png`, `.jpg`, `.jpeg`, `.docx`).
  2. OCR text extraction runs in isolated subprocesses using `pypdf` and `qwen2.5vl:7b`.
  3. System prompts explicitly isolate user input from instructional control tokens.
  4. Extracted measurements are strictly validated against plausible range bounds before entering rule engines.

### B. Rogue / Hallucinated Safety Approvals
- **Defense**:
  1. The deterministic rule engine is the **sole authoritative decision-maker** for numerical limits.
  2. If the rule engine computes `NON_COMPLIANT` or Zone C/D, the task status is locked to non-compliant.
  3. Word document downloads remain locked until a designated supervisor signs off.
  4. Disagreements between model narrative and rule engine force human review.

### C. Arbitrary Code Execution in Sandboxed Python
- **Defense**:
  1. **AST Pre-Execution Inspection**: Code is parsed into an Abstract Syntax Tree before execution. Any node matching `Import` or `ImportFrom` of blocked modules (`subprocess`, `os`, `sys`, `socket`, `pty`, `ctypes`, `requests`, `urllib`, `shutil`, `multiprocessing`) causes immediate rejection.
  2. **Filesystem Confinement**: File operations attempting relative or absolute traversal outside the ephemeral temp directory are blocked.
  3. **Resource Caps**: Subprocess execution is strictly capped at 15 seconds.

### D. Audit Trail Tampering
- **Defense**:
  1. Every approval event calculates a SHA-256 hash chaining back to the previous entry ($H_n = \text{SHA256}(H_{n-1} + \text{Payload})$).
  2. Document hash (`SHA-256` of `output.docx`) is permanently stored at the time of approval.
  3. Continuous verification endpoint `/audit/verify` recomputes the entire chain and flags invalid sequence links.
  4. An independent append-only log `storage/audit_forensics.jsonl` provides out-of-band forensics evidence.

---

### E. Model Supply-Chain & Integrity Tampering (Phase 2 Hardening — MITIGATED)
- **Defense**:
  1. On startup, `backend/app/startup/model_integrity.py` computes SHA-256 hashes of model manifests and compares against `storage/model_manifest.json`.
  2. Any hash mismatch immediately prevents the system from serving requests to that model and surfaces `model_integrity: "FAILED"` in `/health`.

### F. Data & Artifact Encryption at Rest (Phase 2 Hardening — MITIGATED)
- **Defense**:
  1. `backend/app/security/encryption.py` enforces AES-256 authenticated encryption for `.docx` outputs and forensic logs on disk.
  2. Raw file inspection without the authorized master key produces zero plaintext leakage.
  3. Postgres database volume encryption is maintained via OS-level disk encryption / pgcrypto.

### G. Cryptographic Identity & Subject-Bound Authorization (Phase 2 Hardening — MITIGATED)
- **Defense**:
  1. Replaced plain `X-User-Role` trust with cryptographically signed JSON Web Tokens (JWT, HS256) backed by local bcrypt-hashed directory (`backend/app/auth/jwt_auth.py`).
  2. Every approval gate binds the supervisor's verified subject claim (`sub`) directly into the immutable audit hash chain.
  3. Forged, expired, or missing JWTs are rejected with 401 Unauthorized.

### H. Secrets & Key Management (Phase 2 Hardening — MITIGATED)
- **Defense**:
  1. `backend/app/security/secrets.py` manages master keys and tokens via OS Keyring and secured master vault key file (`storage/.vault_key`).
  2. Automated CI scanner `test_secrets_not_in_plaintext.py` enforces zero hardcoded secrets in source code.

### I. PII-Safe Forensic Audit Logging (Phase 2 Hardening — MITIGATED)
- **Defense**:
  1. `storage/audit_forensics.jsonl` scrubs operator personal identifiers (names, employee IDs, emails, phone numbers) using keyed HMAC pseudonyms.
  2. Decision hashes, timestamps, and task references remain intact for compliance audits.

### J. Adversarial Prompt-Injection Red-Teaming (Phase 2 Hardening — MITIGATED)
- **Defense**:
  1. `test_prompt_injection_resistance.py` validates that adversarial prompt overrides in OCR / extracted documents cannot alter rule engine status or bypass human approval gates.

---

## 5. Phase 2 Retrieval & Performance Architecture

1. **Local Vector Index**: Vectorized inner-product indexing (`LocalVectorIndex`) providing sub-linear query latency across 1,000+ documents.
2. **Embedding Quantization**: `float16` and calibrated `int8` storage achieving 50% to 75% memory footprint reduction while retaining >99.6% top-5 retrieval accuracy.
3. **Hybrid Search (Dense + BM25Okapi)**: Reciprocal Rank Fusion (RRF) prioritizes exact equipment tag IDs (e.g. `PMP-204`, `TRB-1105`) over generic semantic matches.
4. **Structure-Aware Chunking**: Preserves markdown tables and multi-field equipment telemetry records (Tag + Reading + Date) atomically within single chunks.
5. **Semantic Cache Threshold & Telemetry**: Enforces strict cosine threshold ($\ge 0.92$) and equipment tag boundary isolation with live hit/miss/near-miss telemetry.
6. **Async Batched Ingestion**: Batches embedding vectors and async pipelines achieving 7.4x throughput speedup.

---

## 6. Enterprise Roadmap & Deferred Items

The following enterprise capabilities are roadmapped for future production refinery integration:
1. **Physical Hardware TPM Enclave**: Hardware-rooted PKCS#11 key management.
2. **Full Centralized LDAP/Active Directory Kerberos Sync**: Enterprise directory integration (local bcrypt store deployed for air-gapped sovereign scope).
3. **Hardware Memory Confidential Computing**: AMD SEV / Intel SGX for host memory encryption.
