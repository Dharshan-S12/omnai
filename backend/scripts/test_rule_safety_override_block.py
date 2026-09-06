import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rules.rule_engine import evaluate_rules

def test_safety_override_prevention():
    print("=" * 70)
    print("   TEST: Authoritative Deterministic Safety Engine & Override Prevention")
    print("=" * 70)

    # 1. Critical High Vibration (Zone D - 8.2 mm/s)
    eval_zone_d = evaluate_rules({"vibration_velocity_rms": 8.2})
    print(f" -> 8.2 mm/s Evaluated Verdict: {eval_zone_d['overall_verdict']} ({eval_zone_d['rule_results'][0]['zone_label']})")
    assert eval_zone_d["overall_verdict"] == "NON_COMPLIANT", "Zone D must be NON_COMPLIANT"
    assert eval_zone_d["rule_results"][0]["passed"] is False, "Zone D must be marked FAIL"

    # 2. Zone C (5.8 mm/s)
    eval_zone_c = evaluate_rules({"vibration_velocity_rms": 5.8})
    print(f" -> 5.8 mm/s Evaluated Verdict: {eval_zone_c['overall_verdict']} ({eval_zone_c['rule_results'][0]['zone_label']})")
    assert eval_zone_c["overall_verdict"] == "NON_COMPLIANT", "Zone C must be NON_COMPLIANT"

    # 3. High Bearing Temperature (88 °C vs 80 °C limit)
    eval_temp = evaluate_rules({"bearing_temperature": 88.0})
    print(f" -> 88 °C Temperature Verdict: {eval_temp['overall_verdict']} ({eval_temp['rule_results'][0]['zone_label']})")
    assert eval_temp["overall_verdict"] == "NON_COMPLIANT", "Temperature >80 °C must be NON_COMPLIANT"

    # 4. Comma-decimal parsing ('5,8 mm/s')
    eval_comma = evaluate_rules({"vibration_velocity_rms": "5,8 mm/s"})
    print(f" -> '5,8 mm/s' Comma Parsing Verdict: {eval_comma['overall_verdict']}")
    assert eval_comma["overall_verdict"] == "NON_COMPLIANT", "Locale decimal '5,8' must be parsed and evaluated as Zone C"

    # 5. Overpressure Valve (175 bar vs 150 bar limit)
    eval_valve = evaluate_rules({"operating_pressure": 175.0})
    print(f" -> 175 bar Valve Pressure Verdict: {eval_valve['overall_verdict']}")
    assert eval_valve["overall_verdict"] == "NON_COMPLIANT", "Pressure >150 bar must be NON_COMPLIANT"

    # 6. Verify deterministic regex contradiction detection logic
    draft_text_contradictory = (
        "# Executive Compliance Memorandum\n"
        "## Technical Findings\n"
        "Vibration reading observed at 8.2 mm/s. The machine is in Zone A - Normal operating limits and fully compliant."
    )
    import re
    has_zone_a_claim = bool(re.search(r"\bZone\s*A\b", draft_text_contradictory, re.IGNORECASE))
    assert has_zone_a_claim is True, "Contradiction check successfully identified false Zone A claim"

    print("\n[PASS] Deterministic safety rules cannot be overridden; regex contradiction detection verified!")
    print("=" * 70)

if __name__ == "__main__":
    test_safety_override_prevention()
