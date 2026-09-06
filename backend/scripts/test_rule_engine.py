import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rules.rule_engine import evaluate_rules, extract_numeric_value, Rule, RULE_SETS

def test_deterministic_rule_engine():
    print("=====================================================================")
    print("   TEST: Pure Deterministic Rule Engine (No LLM Calls)               ")
    print("=====================================================================")

    # 1. Test numeric extraction
    assert extract_numeric_value("5.8 mm/s") == 5.8
    assert extract_numeric_value("78 °C") == 78.0
    assert extract_numeric_value("2.5s") == 2.5
    assert extract_numeric_value("150 bar") == 150.0
    assert extract_numeric_value(4.2) == 4.2
    assert extract_numeric_value("Zone C (5.8 mm/s)") == 5.8
    print(" [PASS] Deterministic numeric string regex parsing verified")

    # 2. Test TRB-1105 vibration scenario (5.8 mm/s against SOP-MNT-042)
    eval_c = evaluate_rules(
        extracted_fields={
            "equipment_id": "TRB-1105",
            "unit": "HCU",
            "vibration_rms_mms": 5.8,
            "bearing_temp_c": 75.0
        },
        sop_reference="SOP-MNT-042"
    )

    assert eval_c["evaluated"] is True
    assert eval_c["overall_verdict"] == "NON_COMPLIANT"
    assert eval_c["sop_reference"] == "SOP-MNT-042"
    assert len(eval_c["rule_results"]) >= 2

    vib_rule = next((r for r in eval_c["rule_results"] if "vibration" in r["field"]), None)
    assert vib_rule is not None
    assert vib_rule["actual_value"] == 5.8
    assert "Zone C" in vib_rule["zone_label"]
    assert vib_rule["passed"] is False
    print(f" [PASS] 5.8 mm/s correctly classified deterministically as Zone C / NON_COMPLIANT: {vib_rule['zone_label']}")

    # 3. Test Zone A Normal operating vibration (2.1 mm/s)
    eval_a = evaluate_rules(
        extracted_fields={"equipment_id": "PMP-201", "vibration_rms_mms": 2.1, "bearing_temp_c": 62.0},
        sop_reference="SOP-MNT-042"
    )
    assert eval_a["overall_verdict"] == "COMPLIANT"
    vib_a = next(r for r in eval_a["rule_results"] if "vibration" in r["field"])
    assert "Zone A" in vib_a["zone_label"]
    assert vib_a["passed"] is True
    print(f" [PASS] 2.1 mm/s correctly classified as Zone A / COMPLIANT: {vib_a['zone_label']}")

    # 4. Test Zone B Alert vibration (3.8 mm/s)
    eval_b = evaluate_rules(
        extracted_fields={"equipment_id": "PMP-202", "vibration_rms_mms": 3.8, "bearing_temp_c": 70.0},
        sop_reference="SOP-MNT-042"
    )
    assert eval_b["overall_verdict"] == "NEEDS_REVIEW"
    vib_b = next(r for r in eval_b["rule_results"] if "vibration" in r["field"])
    assert "Zone B" in vib_b["zone_label"]
    print(f" [PASS] 3.8 mm/s correctly classified as Zone B / Alert (NEEDS_REVIEW)")

    # 5. Test Zone D Emergency Shutdown vibration (8.2 mm/s)
    eval_d = evaluate_rules(
        extracted_fields={"equipment_id": "TRB-990", "vibration_rms_mms": 8.2},
        sop_reference="SOP-MNT-042"
    )
    assert eval_d["overall_verdict"] == "NON_COMPLIANT"
    vib_d = next(r for r in eval_d["rule_results"] if "vibration" in r["field"])
    assert "Zone D" in vib_d["zone_label"]
    print(f" [PASS] 8.2 mm/s correctly classified as Zone D / Emergency Shutdown")

    # 6. Test Bearing Temperature limit (85°C > 80°C threshold)
    eval_temp = evaluate_rules(
        extracted_fields={"equipment_id": "PMP-300", "vibration_rms_mms": 2.0, "bearing_temp_c": 85.0},
        sop_reference="SOP-MNT-042"
    )
    assert eval_temp["overall_verdict"] == "NON_COMPLIANT"
    temp_rule = next(r for r in eval_temp["rule_results"] if "temp" in r["field"])
    assert temp_rule["passed"] is False
    print(f" [PASS] Bearing temp 85 °C correctly evaluated as FAIL (> 80 °C)")

    # 7. Test SOP-SAF-104 Emergency Valve Closure Speed
    eval_vlv_pass = evaluate_rules(
        extracted_fields={"equipment_id": "VLV-7788", "actuation_time_s": "1.8s", "line_pressure_bar": 120},
        sop_reference="SOP-SAF-104"
    )
    assert eval_vlv_pass["overall_verdict"] == "COMPLIANT"

    eval_vlv_fail = evaluate_rules(
        extracted_fields={"equipment_id": "VLV-7788", "actuation_time_s": "3.1s", "line_pressure_bar": 120},
        sop_reference="SOP-SAF-104"
    )
    assert eval_vlv_fail["overall_verdict"] == "NON_COMPLIANT"
    vlv_act = next(r for r in eval_vlv_fail["rule_results"] if "actuation" in r["field"])
    assert vlv_act["passed"] is False
    print(f" [PASS] ESD Valve actuation 3.1s evaluated as FAIL (> 2.5s limit)")

    # 8. Test unruled / general text (no numerical thresholds) -> graceful skip
    eval_unruled = evaluate_rules(
        extracted_fields={"document_type": "correspondence", "subject": "Quarterly staffing update"},
        sop_reference=None
    )
    assert eval_unruled["evaluated"] is False
    assert "No applicable numerical rule set" in eval_unruled["reason"]
    print(" [PASS] Unruled document type skipped gracefully with evaluated=False")

    print("\n=====================================================================")
    print("   ALL DETERMINISTIC RULE ENGINE TESTS PASSED!                       ")
    print("=====================================================================")

if __name__ == "__main__":
    test_deterministic_rule_engine()
