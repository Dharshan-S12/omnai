import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.schemas import AuditVerifyResponse, AuditEntrySchema

router = APIRouter(prefix="/audit", tags=["audit"])

AUDIT_CHAIN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "audit_hash_chain.jsonl")
FORENSICS_MIRROR_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "audit_forensics.jsonl")
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage")

GENESIS_HASH = "0" * 64

def compute_record_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
    """Computes SHA-256 hash chaining previous hash with current payload fields."""
    serialized = f"{prev_hash}|{payload.get('sequence_number')}|{payload.get('task_id')}|{payload.get('reviewer_name')}|{payload.get('decision')}|{payload.get('document_sha256')}|{payload.get('timestamp')}"
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def compute_file_sha256(file_path: str) -> Optional[str]:
    """Computes SHA-256 hash of a file on disk."""
    if not os.path.exists(file_path):
        return None
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

import re
from app.security.secrets import get_audit_hmac_key

def anonymize_reviewer_identity(reviewer_name: str) -> str:
    """Generates deterministic PII-safe keyed HMAC pseudonym for forensic logging."""
    hmac_key = get_audit_hmac_key()
    digest = hashlib.sha256(hmac_key + reviewer_name.strip().encode("utf-8")).hexdigest()[:12]
    return f"OPERATOR_ID_{digest.upper()}"

def redact_pii_text(text: str) -> str:
    """Redacts employee IDs, email addresses, and phone patterns from audit notes."""
    if not text:
        return ""
    # Redact Employee IDs (e.g. MRPL-EMP-1044, EMP-0012)
    redacted = re.sub(r'(?:MRPL[-_]?)?EMP[-_]?\d+', '[REDACTED_EMP_ID]', text, flags=re.IGNORECASE)
    # Redact Emails
    redacted = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', redacted)
    # Redact Phone numbers
    redacted = re.sub(r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[REDACTED_PHONE]', redacted)
    return redacted

def record_approval_audit_event(
    task_id: UUID,
    reviewer_name: str,
    decision: str,
    reviewer_notes: Optional[str] = None,
    docx_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Appends a new cryptographically hash-chained approval event to the audit ledger.
    Also mirrors a PII-redacted entry to the flat-file forensic log.
    """
    os.makedirs(os.path.dirname(AUDIT_CHAIN_PATH), exist_ok=True)
    
    # Read existing entries to determine last sequence number and prev_hash
    existing_entries = []
    if os.path.exists(AUDIT_CHAIN_PATH):
        with open(AUDIT_CHAIN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        existing_entries.append(json.loads(line.strip()))
                    except Exception:
                        pass

    seq_num = len(existing_entries) + 1
    prev_hash = existing_entries[-1]["current_hash"] if existing_entries else GENESIS_HASH

    # Compute document SHA-256 hash if docx exists
    doc_sha256 = compute_file_sha256(docx_path) if docx_path else None
    ts = datetime.now(timezone.utc).isoformat()

    payload = {
        "id": str(uuid.uuid4()),
        "sequence_number": seq_num,
        "task_id": str(task_id),
        "reviewer_name": reviewer_name,
        "decision": decision,
        "reviewer_notes": reviewer_notes or "",
        "document_sha256": doc_sha256 or "NO_DOCX",
        "timestamp": ts,
        "prev_hash": prev_hash
    }

    current_hash = compute_record_hash(prev_hash, payload)
    payload["current_hash"] = current_hash

    # Write to primary audit hash chain
    with open(AUDIT_CHAIN_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")

    # Write PII-safe redacted mirror to flat-file forensics log
    try:
        forensics_entry = {
            "id": payload["id"],
            "sequence_number": payload["sequence_number"],
            "task_id": payload["task_id"],
            "reviewer_identity_hash": anonymize_reviewer_identity(reviewer_name),
            "decision": payload["decision"],
            "reviewer_notes": redact_pii_text(payload["reviewer_notes"]),
            "document_sha256": payload["document_sha256"],
            "timestamp": payload["timestamp"],
            "current_hash": payload["current_hash"],
            "prev_hash": payload["prev_hash"]
        }
        with open(FORENSICS_MIRROR_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(forensics_entry) + "\n")
    except Exception:
        pass

    return payload

def verify_audit_hash_chain() -> Dict[str, Any]:
    """
    Cryptographically verifies the entire audit hash chain from genesis to present.
    Verifies:
    1. Every record's prev_hash matches the prior record's current_hash.
    2. Every record's current_hash is the correct SHA-256 of its contents.
    3. The referenced document on disk still matches its stored document_sha256 hash.
    """
    if not os.path.exists(AUDIT_CHAIN_PATH):
        return {
            "verified": True,
            "total_records": 0,
            "latest_hash": GENESIS_HASH,
            "tampered_sequence": None,
            "error_message": None,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    entries = []
    with open(AUDIT_CHAIN_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if line.strip():
                try:
                    entries.append(json.loads(line.strip()))
                except Exception as e:
                    return {
                        "verified": False,
                        "total_records": idx,
                        "latest_hash": None,
                        "tampered_sequence": idx + 1,
                        "error_message": f"Malformed JSON in audit chain at record #{idx + 1}: {str(e)}",
                        "checked_at": datetime.now(timezone.utc).isoformat()
                    }

    expected_prev = GENESIS_HASH
    for entry in entries:
        seq = entry.get("sequence_number", 0)
        stored_prev = entry.get("prev_hash", "")
        stored_curr = entry.get("current_hash", "")

        # 1. Verify link to previous block
        if stored_prev != expected_prev:
            return {
                "verified": False,
                "total_records": len(entries),
                "latest_hash": None,
                "tampered_sequence": seq,
                "error_message": f"Broken hash chain at record #{seq}: expected prev_hash '{expected_prev[:12]}...', got '{stored_prev[:12]}...'",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

        # 2. Recompute current hash
        recomputed_curr = compute_record_hash(stored_prev, entry)
        if recomputed_curr != stored_curr:
            return {
                "verified": False,
                "total_records": len(entries),
                "latest_hash": None,
                "tampered_sequence": seq,
                "error_message": f"Payload hash mismatch at record #{seq}: payload contents were altered after recording!",
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

        expected_prev = stored_curr

    return {
        "verified": True,
        "total_records": len(entries),
        "latest_hash": expected_prev,
        "tampered_sequence": None,
        "error_message": None,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

@router.get("/verify", response_model=AuditVerifyResponse)
async def get_audit_verification():
    """Returns real-time verification of the tamper-evident cryptographic audit hash chain."""
    return verify_audit_hash_chain()

@router.get("/records")
async def get_audit_records(limit: int = 50):
    """Returns recent audit chain records."""
    if not os.path.exists(AUDIT_CHAIN_PATH):
        return []
    records = []
    with open(AUDIT_CHAIN_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line.strip()))
                except Exception:
                    pass
    return records[-limit:]
