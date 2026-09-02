import os
import sys

# Ensure Hugging Face / sentence-transformers and Chroma operate in strictly air-gapped / offline mode
# Note: Requires the embedding model to already be cached locally (from prior runs).
# If the cache is missing, this will cause a clear local error instead of a silent network call, which is intentional.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag.ingest import ingest_document

SAMPLE_SOPS = [
    {
        "doc_id": "sop-mnt-042",
        "source": "SOP-MNT-042: Routine Pump & Turbine Vibration Inspection",
        "text": """Standard Operating Procedure SOP-MNT-042
Title: Routine Pump and Turbine Vibration Inspection & Approval Protocol
Department: Industrial Maintenance & Operations
Effective Date: 2024-01-15
Classification: Sovereign Confidential

1. Purpose and Scope:
This SOP establishes mandatory procedures for routine vibration analysis and inspection approval for centrifugal pumps, steam turbines, and industrial rotating machinery.

2. Vibration Thresholds & Criteria:
- Normal Operation (Zone A): Vibration velocity RMS < 2.8 mm/s. Immediate approval permitted.
- Acceptable / Alert (Zone B): Vibration velocity RMS between 2.8 and 4.5 mm/s. Requires supervisor review and re-measurement within 48 hours.
- Unsatisfactory / Action Required (Zone C): Vibration velocity RMS between 4.5 and 7.1 mm/s. Requires mandatory inspection report approval note, maintenance work order creation, and bearing lubrication check.
- Unacceptable / Immediate Shutdown (Zone D): Vibration velocity RMS > 7.1 mm/s. Immediate emergency isolation.

3. Approval Note Requirements:
Every pump inspection approval note must explicitly reference SOP-MNT-042 and document:
- Equipment Tag ID and Location
- Recorded Peak Vibration RMS (mm/s) and Peak Frequency (Hz)
- Oil cleanliness rating and seal temperature (must be below 80 deg C)
- Maintenance technician signature and certified supervisor endorsement.
"""
    },
    {
        "doc_id": "sop-doc-019",
        "source": "SOP-DOC-019: Vendor Technical Document Handling & Approval Policy",
        "text": """Standard Operating Procedure SOP-DOC-019
Title: Vendor Technical Document Handling, Verification, and Archival Policy
Department: Quality Assurance and Procurement
Effective Date: 2024-02-01

1. Purpose:
Governs the verification, classification, and cryptographic integrity verification of third-party vendor manuals, material test reports (MTRs), and compliance certificates.

2. Document Ingestion Requirements:
- All vendor documentation must be ingested into the on-premise document management system within 24 hours of receipt.
- Documents containing proprietary engineering schematics must be tagged with 'CONFIDENTIAL-LEVEL-2'.
- OCR extraction must verify vendor stamp, date of manufacture, and heat number against the original purchase order.

3. Approval Workflow:
- Level 1: Automatic OCR and structural validation.
- Level 2: QA engineer review and digital sign-off.
- Approved documents are stored in the local sovereign vault with immutable SHA-256 checksums.
"""
    },
    {
        "doc_id": "sec-pol-007",
        "source": "SEC-POL-007: Air-Gapped Sovereign AI Data Compliance Standard",
        "text": """Security Policy SEC-POL-007
Title: Air-Gapped Sovereign AI Infrastructure Compliance & Privacy Standard
Department: Information Security & Industrial Cyber Resilience
Effective Date: 2024-03-01

1. Sovereign Architecture Mandates:
- All Large Language Model (LLM) and Vision-Language Model (VLM) inference must execute strictly on local on-premise compute nodes (localhost / 127.0.0.1).
- Outbound internet connections and external telemetry reporting are strictly forbidden.
- Knowledge base embeddings must be computed using local open-weight encoders (e.g., sentence-transformers).

2. Audit & Traceability:
- Every autonomous agent action, tool invocation, and sandbox execution must be immutably recorded in the relational task_steps ledger.
- Step logs must capture tool name, execution timestamp, and sanitized structured input/output payloads.
"""
    },
    {
        "doc_id": "sop-saf-104",
        "source": "SOP-SAF-104: Emergency Shutdown & Containment Protocol for High-Pressure Valves",
        "text": """Standard Operating Procedure SOP-SAF-104
Title: Emergency Isolation and Safety Containment for High-Pressure Actuated Valves
Department: Process Safety & Emergency Response
Effective Date: 2024-04-10

1. Emergency Triggers:
- Line pressure exceeding 150 bar gauge.
- Toxic gas detector alarm level 2 (concentration > 25 ppm).
- Uncontrolled differential pressure drop across valve seat exceeding 40%.

2. Automated and Manual Intervention:
- Stage 1: Trigger emergency shutdown (ESD) valve solenoid closure.
- Stage 2: Verify zero flow through downstream ultrasonic sensors within 5 seconds.
- Stage 3: Initiate nitrogen purge loop to vent trapped volatile hydrocarbons.
"""
    }
]

def seed_knowledge_base():
    print("=== Seeding Sovereign On-Prem Knowledge Base (ChromaDB) ===")
    total_chunks = 0
    for doc in SAMPLE_SOPS:
        print(f"Ingesting: {doc['source']} (ID: {doc['doc_id']})...")
        chunks = ingest_document(
            text=doc["text"],
            source=doc["source"],
            doc_id=doc["doc_id"]
        )
        total_chunks += chunks
        print(f" -> Stored {chunks} chunks.")
        
    print(f"\nSuccessfully seeded {len(SAMPLE_SOPS)} SOP documents ({total_chunks} total vector chunks).")

if __name__ == "__main__":
    seed_knowledge_base()
