import sys
import os
import json
import uuid
from datetime import datetime, timezone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.multi_agent_docgen import log_ensemble_dissent_record, DISSENT_LOG_PATH

def test_ensemble_dissent():
    print("=" * 70)
    print("   TEST: Diverse 3-Model Ensemble Voting & Dissent Audit Trail       ")
    print("=" * 70)

    test_task_id = uuid.uuid4()
    mock_runs = [
        {"config": "Config A (7B @ temp 0.0)", "verdict": "NON_COMPLIANT", "summary_reason": "Vibration 4.6 mm/s exceeds ISO Zone B limit"},
        {"config": "Config B (7B @ temp 0.3)", "verdict": "NEEDS_REVIEW", "summary_reason": "Borderline Zone B/C proximity, re-inspect in 48h"},
        {"config": "Config C (3B @ temp 0.7)", "verdict": "NON_COMPLIANT", "summary_reason": "Over-threshold condition observed"}
    ]

    # Majority vote calculation
    from collections import Counter
    verdicts = [r["verdict"] for r in mock_runs]
    counts = Counter(verdicts)
    majority_verdict, count = counts.most_common(1)[0]
    is_unanimous = (count == len(mock_runs))

    print(f" -> Ensemble Votes: {verdicts}")
    print(f" -> Majority Verdict: {majority_verdict} ({count}/3 votes)")
    print(f" -> Is Unanimous: {is_unanimous}")

    assert majority_verdict == "NON_COMPLIANT", "Majority must be NON_COMPLIANT"
    assert is_unanimous is False, "Split vote must be identified as non-unanimous"

    # Log dissent record
    log_ensemble_dissent_record(
        task_id=test_task_id,
        individual_runs=mock_runs,
        majority_verdict=majority_verdict,
        trigger_reason="Borderline measurement (4.6 mm/s)"
    )

    # Verify log file exists and contains the entry
    assert os.path.exists(DISSENT_LOG_PATH), f"Dissent log not found at {DISSENT_LOG_PATH}"
    found = False
    with open(DISSENT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if str(test_task_id) in line:
                entry = json.loads(line)
                assert entry["majority_verdict"] == "NON_COMPLIANT"
                assert len(entry["runs"]) == 3
                found = True
                print(f" -> Dissent audit entry verified in {DISSENT_LOG_PATH}: {entry['id']}")
                break

    assert found is True, "Dissent record was not properly stored"
    print("\n[PASS] Split-vote ensemble dissent logging and audit recording verified!")
    print("=" * 70)

if __name__ == "__main__":
    test_ensemble_dissent()
