"""
Test Suite: A5. PII-Safe Forensic Logging Verification
Proves that:
1. Operator personal identifiers (names, employee IDs, email, phone) are redacted or hashed with HMAC in storage/audit_forensics.jsonl.
2. Non-PII forensic audit properties (decision, hashes, task references, sequence numbers, timestamps) remain intact in the clear.
3. No raw PII strings leak into the flat-file mirror.
"""

import os
import sys
import json
import uuid
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.routers.audit import (
    record_approval_audit_event,
    anonymize_reviewer_identity,
    redact_pii_text,
    FORENSICS_MIRROR_PATH
)

def test_forensic_log_redaction_suite():
    print("================================================================================")
    print("TEST SUITE: A5 — PII-Safe Forensic Logging & Anonymization")
    print("================================================================================")

    # 1. Test Text Redaction Functionality
    sample_text_with_pii = (
        "Approved by Anil Verma (MRPL-EMP-1044). Please email anil.v@mrpl.gov.in "
        "or call +91-9845012345 for questions on EMP-1044 compliance signoff."
    )
    redacted = redact_pii_text(sample_text_with_pii)
    assert "MRPL-EMP-1044" not in redacted, "Employee ID was not redacted!"
    assert "EMP-1044" not in redacted, "Short Employee ID was not redacted!"
    assert "anil.v@mrpl.gov.in" not in redacted, "Email address was not redacted!"
    assert "+91-9845012345" not in redacted, "Phone number was not redacted!"
    assert "[REDACTED_EMP_ID]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    print("  [PASS] Regular expression sanitization scrubbed employee ID, email, and phone numbers")

    # 2. Test Keyed HMAC Pseudonymization
    name1 = "Rajesh Kumar (Lead Supervisor)"
    pseudo1 = anonymize_reviewer_identity(name1)
    pseudo2 = anonymize_reviewer_identity(name1)
    pseudo3 = anonymize_reviewer_identity("Anil Verma")
    
    assert pseudo1.startswith("OPERATOR_ID_"), "Pseudonym format mismatch"
    assert pseudo1 == pseudo2, "HMAC pseudonymization must be deterministic for same key & subject"
    assert pseudo1 != pseudo3, "Different operator names must produce distinct pseudonyms"
    assert "Rajesh" not in pseudo1 and "Kumar" not in pseudo1
    print("  [PASS] Keyed HMAC pseudonymization produces irreversible deterministic identifiers")

    # 3. Test Full Forensic Log Mirroring
    test_task_id = uuid.uuid4()
    operator_raw_name = "Vikram Aditya (Lead Engineer - MRPL-EMP-0077)"
    operator_sensitive_notes = "Inspected by Vikram (vikram.aditya@mrpl.in) on shift 2. Vibration within SOP limit."
    
    record_approval_audit_event(
        task_id=test_task_id,
        reviewer_name=operator_raw_name,
        decision="approved",
        reviewer_notes=operator_sensitive_notes
    )

    # Inspect the raw forensics mirror file
    assert os.path.exists(FORENSICS_MIRROR_PATH), "Forensics mirror log file must exist"
    with open(FORENSICS_MIRROR_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    matching_line = None
    for line in reversed(lines):
        if str(test_task_id) in line:
            matching_line = line
            break

    assert matching_line is not None, "Test entry not found in forensic mirror"
    
    # Assert zero raw PII strings in forensic line
    assert "Vikram Aditya" not in matching_line, "Raw operator full name leaked into forensics mirror!"
    assert "MRPL-EMP-0077" not in matching_line, "Raw employee ID leaked into forensics mirror!"
    assert "vikram.aditya@mrpl.in" not in matching_line, "Raw email leaked into forensics mirror!"

    # Assert decision, task_id, sequence_number, timestamp and hashes are preserved
    parsed = json.loads(matching_line)
    assert parsed["task_id"] == str(test_task_id)
    assert parsed["decision"] == "approved"
    assert "OPERATOR_ID_" in parsed["reviewer_identity_hash"]
    assert parsed["current_hash"] is not None
    assert parsed["prev_hash"] is not None
    print("  [PASS] Forensics mirror logged entry with 100% PII redaction and full audit trail integrity")

    print("\n>>> ALL A5 FORENSIC LOG REDACTION TESTS PASSED (3/3)\n")

if __name__ == "__main__":
    test_forensic_log_redaction_suite()
