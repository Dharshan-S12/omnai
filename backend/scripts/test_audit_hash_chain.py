import sys
import os
import json
import uuid
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.routers.audit import (
    record_approval_audit_event,
    verify_audit_hash_chain,
    AUDIT_CHAIN_PATH,
    compute_record_hash
)

def test_audit_hash_chain():
    print("=" * 70)
    print("   TEST: Tamper-Evident Append-Only Cryptographic Audit Hash Chain    ")
    print("=" * 70)

    # 1. Record several approval events
    task1 = uuid.uuid4()
    task2 = uuid.uuid4()
    task3 = uuid.uuid4()

    e1 = record_approval_audit_event(
        task_id=task1,
        reviewer_name="Chief Inspector Ramanathan",
        decision="approved",
        reviewer_notes="Vibration measurements compliant with ISO Zone A."
    )
    print(f" -> Event 1 Recorded: Seq #{e1['sequence_number']}, Hash: {e1['current_hash'][:16]}...")

    e2 = record_approval_audit_event(
        task_id=task2,
        reviewer_name="Supervisory Engineer Desai",
        decision="rejected",
        reviewer_notes="Bearing temperature exceeded 80 °C threshold."
    )
    print(f" -> Event 2 Recorded: Seq #{e2['sequence_number']}, Hash: {e2['current_hash'][:16]}... (Links to: {e2['prev_hash'][:16]}...)")

    e3 = record_approval_audit_event(
        task_id=task3,
        reviewer_name="Operations Lead Mehta",
        decision="approved",
        reviewer_notes="Corrective maintenance verified."
    )
    print(f" -> Event 3 Recorded: Seq #{e3['sequence_number']}, Hash: {e3['current_hash'][:16]}... (Links to: {e3['prev_hash'][:16]}...)")

    # 2. Verify intact chain
    v_clean = verify_audit_hash_chain()
    print(f" -> Intact Chain Verification: Verified={v_clean['verified']}, Total Records={v_clean['total_records']}")
    assert v_clean["verified"] is True, "Intact audit chain must verify with 100% cryptographic integrity"
    assert v_clean["tampered_sequence"] is None

    # 3. Simulate Row Tampering (Attacker modifies decision from 'rejected' to 'approved')
    with open(AUDIT_CHAIN_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    tampered_lines = []
    for line in lines:
        entry = json.loads(line.strip())
        if str(task2) in entry["task_id"]:
            # Tamper payload without updating hash
            entry["decision"] = "approved"
            entry["reviewer_notes"] = "TAMPERED: Falsely changed to approved"
            tampered_lines.append(json.dumps(entry) + "\n")
        else:
            tampered_lines.append(line)

    # Write tampered log temporarily
    with open(AUDIT_CHAIN_PATH, "w", encoding="utf-8") as f:
        f.writelines(tampered_lines)

    v_tampered = verify_audit_hash_chain()
    print(f" -> Tampered Chain Verification: Verified={v_tampered['verified']}, Detected Sequence=#{v_tampered['tampered_sequence']}, Error='{v_tampered['error_message']}'")
    assert v_tampered["verified"] is False, "Tampered chain MUST fail verification"
    assert v_tampered["tampered_sequence"] == e2["sequence_number"], "Tampering must point exactly to tampered sequence number"

    # Restore intact lines for clean state
    with open(AUDIT_CHAIN_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    v_restored = verify_audit_hash_chain()
    assert v_restored["verified"] is True, "Restored chain must verify cleanly"

    print("\n[PASS] Cryptographic hash-chaining and tamper detection verified successfully!")
    print("=" * 70)

if __name__ == "__main__":
    test_audit_hash_chain()
