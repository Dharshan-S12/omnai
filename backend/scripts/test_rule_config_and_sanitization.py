import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rules.rule_engine import load_thresholds_config, evaluate_rules, sanitize_and_validate_value

def test_config_and_sanitization():
    print("=" * 70)
    print("   TEST: Versioned Threshold Config & Input Sanitization Gating       ")
    print("=" * 70)

    # 1. Test Config Loading & SHA-256 Hash
    cfg, version, sha256_hash = load_thresholds_config(force_reload=True)
    print(f" -> Loaded Config Version: {version}")
    print(f" -> Config SHA-256 Checksum: {sha256_hash}")
    assert version.startswith("1."), f"Expected version 1.x, got {version}"
    assert len(sha256_hash) == 64, "Expected valid 64-char SHA-256 hash"

    # 2. Test Input Sanitization - Implausible Outlier Magnitude (e.g. 710 mm/s)
    is_valid, warn = sanitize_and_validate_value("vibration_velocity_rms", 710.0)
    print(f" -> 710.0 mm/s Sanitization Check: Valid={is_valid}, Alert='{warn}'")
    assert is_valid is False, "710 mm/s must be flagged as out-of-range (>100 mm/s)"

    # Negative vibration velocity
    is_valid_neg, warn_neg = sanitize_and_validate_value("vibration_velocity_rms", -5.0)
    print(f" -> -5.0 mm/s Sanitization Check: Valid={is_valid_neg}, Alert='{warn_neg}'")
    assert is_valid_neg is False, "Negative vibration must be rejected"

    # Plausible normal vibration (2.4 mm/s)
    is_valid_norm, _ = sanitize_and_validate_value("vibration_velocity_rms", 2.4)
    assert is_valid_norm is True, "2.4 mm/s must pass sanitization"

    # 3. Test Full Evaluation with Sanitization Alerts
    res_malformed = evaluate_rules({"vibration_velocity_rms": "710 mm/s"})
    print(f" -> Malformed reading evaluation: Verdict={res_malformed['overall_verdict']}, Warnings={res_malformed['sanitization_warnings']}")
    assert res_malformed["overall_verdict"] == "NON_COMPLIANT", "Out-of-range reading must result in NON_COMPLIANT"
    assert len(res_malformed["sanitization_warnings"]) > 0, "Sanitization warning must be surfaced"

    # 4. Test Locale Decimal Parsing
    res_locale = evaluate_rules({"vibration_velocity_rms": "4,2 mm/s"})
    print(f" -> Locale '4,2 mm/s' evaluation: Zone={res_locale['rule_results'][0]['zone_label']}, Actual={res_locale['rule_results'][0]['actual_value']}")
    assert res_locale["rule_results"][0]["actual_value"] == 4.2, "Locale '4,2' must parse to 4.2"
    assert "Zone B" in res_locale["rule_results"][0]["zone_label"], "4.2 mm/s must be Zone B"

    print("\n[PASS] Externalized versioned config, checksums, and input sanitization verified!")
    print("=" * 70)

if __name__ == "__main__":
    test_config_and_sanitization()
