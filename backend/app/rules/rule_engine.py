import os
import re
import json
import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "thresholds_config.json")

_cached_config: Optional[Dict[str, Any]] = None
_cached_config_hash: Optional[str] = None
_cached_config_version: Optional[str] = None

def load_thresholds_config(force_reload: bool = False) -> Tuple[Dict[str, Any], str, str]:
    """
    Loads externalized threshold configuration file and computes its SHA-256 checksum.
    Returns (config_dict, config_version, config_sha256).
    """
    global _cached_config, _cached_config_hash, _cached_config_version
    if _cached_config is not None and not force_reload:
        return _cached_config, _cached_config_version or "1.0.0", _cached_config_hash or ""

    if os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            raw_content = f.read()
            sha256 = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
            config = json.loads(raw_content)
            version = config.get("version", "1.0.0")
            _cached_config = config
            _cached_config_hash = sha256
            _cached_config_version = version
            return config, version, sha256

    # Fallback minimal configuration
    fallback_config = {
        "version": "fallback-1.0.0",
        "standards": {}
    }
    fallback_hash = hashlib.sha256(b"fallback").hexdigest()
    return fallback_config, "fallback-1.0.0", fallback_hash

@dataclass
class Rule:
    field: str
    operator: str  # "<", "<=", ">", ">=", "==", "!="
    threshold: float
    zone_label: str
    sop_reference: str
    description: str = ""

# Backward compatibility dictionary
RULE_SETS: Dict[str, List[Rule]] = {
    "SOP-MNT-042": [
        Rule("vibration_velocity_rms", "<=", 4.5, "Zone B Alert limit (4.5 mm/s)", "SOP-MNT-042"),
        Rule("bearing_temperature", "<=", 80.0, "Bearing temperature limit (80 °C)", "SOP-MNT-042")
    ],
    "SOP-SAF-104": [
        Rule("operating_pressure", "<=", 150.0, "Line pressure limit (150 bar)", "SOP-SAF-104"),
        Rule("actuation_time", "<=", 2.5, "ESD actuation closure time (2.5s)", "SOP-SAF-104")
    ]
}

def extract_numeric_value(val: Any) -> Optional[float]:
    """
    Extract a clean float from numbers or strings.
    Handles:
    - Standard floats/integers: 5.8, 150
    - Unit strings: '5.8 mm/s', '78 °C', '2.5s', '150 bar', 'Zone C (5.8 mm/s)'
    - Locale-aware comma decimals: '7,1 mm/s', '2,8', '4,5 °C'
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    if not val_str:
        return None

    # Handle European/locale comma decimals if no dot exists: e.g. "7,1 mm/s" -> "7.1 mm/s"
    if "," in val_str and "." not in val_str:
        val_str = re.sub(r'(\d+),(\d+)', r'\1.\2', val_str)

    try:
        return float(val_str)
    except ValueError:
        pass

    # Find all float and integer candidates
    matches = re.findall(r'[-+]?\d+(?:\.\d+)?', val_str)
    if not matches:
        return None

    # Prioritize decimal number if present
    for m in matches:
        if "." in m:
            try:
                return float(m)
            except ValueError:
                pass

    try:
        return float(matches[-1])
    except ValueError:
        return None

def sanitize_and_validate_value(field_name: str, value: float) -> Tuple[bool, Optional[str]]:
    """
    Input Sanitization & Sanity Check:
    Verifies that numerical readings fall within physically plausible refinery ranges.
    Flags readings that are >100x expected or negative when disallowed.
    """
    config, _, _ = load_thresholds_config()
    standards = config.get("standards", {})

    field_norm = field_name.lower().replace("_", "").replace(" ", "")

    for std_name, std_data in standards.items():
        params = std_data.get("parameters", {})
        for p_key, p_val in params.items():
            aliases = [a.lower().replace("_", "").replace(" ", "") for a in p_val.get("field_aliases", [p_key])]
            if field_norm in aliases:
                plausible = p_val.get("plausible_range", {})
                p_min = plausible.get("min", -9999.0)
                p_max = plausible.get("max", 9999.0)
                if value < p_min or value > p_max:
                    return False, f"Value {value} for '{field_name}' is outside plausible operational range [{p_min}, {p_max}]. Possible OCR artifact or unit error."

    return True, None

def find_field_in_dict(data: dict, target_key: str) -> Optional[float]:
    """
    Recursively search for numeric value of target_key across flat and nested dictionaries.
    Handles variations like 'vibration', 'vibration_rms', 'bearing_temp', etc.
    """
    if not isinstance(data, dict):
        return None

    # Exact key match
    if target_key in data:
        num = extract_numeric_value(data[target_key])
        if num is not None:
            return num

    # Search in 'measurements' nested dict if present
    if "measurements" in data and isinstance(data["measurements"], dict):
        nested_val = find_field_in_dict(data["measurements"], target_key)
        if nested_val is not None:
            return nested_val

    # Fuzzy key normalization
    norm_target = target_key.lower().replace("_", "").replace(" ", "")
    for k, v in data.items():
        norm_k = k.lower().replace("_", "").replace(" ", "")
        if norm_k == norm_target or (norm_target in norm_k and len(norm_k) <= len(norm_target) + 5):
            num = extract_numeric_value(v)
            if num is not None:
                return num

    return None

def evaluate_rules(extracted_fields: dict, sop_reference: Optional[str] = None) -> Dict[str, Any]:
    """
    PURE DETERMINISTIC RULE EVALUATOR:
    - Zero LLM calls.
    - Loads externalized versioned config (thresholds_config.json) with SHA-256 hash traceability.
    - Sanitizes inputs and flags implausible outlier readings.
    - Matches rules by sop_reference or detects applicable parameters.
    - Evaluates exact Python numeric operators (<, <=, >, >=, ==).
    - Classifies ISO zones and produces authoritative overall verdict (COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW).
    - Detects borderline cases (within 10% of a critical threshold).
    """
    config, config_version, config_hash = load_thresholds_config()
    standards = config.get("standards", {})

    sanitization_warnings: List[str] = []
    rule_results: List[Dict[str, Any]] = []

    has_non_compliant = False
    has_alert_zone_b = False
    is_borderline = False
    has_sanitization_failure = False

    # 1. Evaluate Vibration Velocity RMS against ISO 10816-3 (or SOP-MNT-042)
    vib_value = None
    vib_field_names = ["vibration_velocity_rms", "vibration_rms_mms", "vibration_rms", "vibration", "overall_vibration"]
    for v_field in vib_field_names:
        v = find_field_in_dict(extracted_fields, v_field)
        if v is not None:
            vib_value = v
            break

    if vib_value is not None:
        is_valid, warn_msg = sanitize_and_validate_value("vibration_velocity_rms", vib_value)
        if not is_valid and warn_msg:
            sanitization_warnings.append(warn_msg)
            has_sanitization_failure = True

        # Load ISO zones from config
        iso_cfg = standards.get("ISO_10816_3", {}).get("parameters", {}).get("vibration_velocity_rms", {})
        zones_cfg = iso_cfg.get("zones", {})

        z_a = zones_cfg.get("Zone A", {}).get("max", 2.8)
        z_b = zones_cfg.get("Zone B", {}).get("max", 4.5)
        z_c = zones_cfg.get("Zone C", {}).get("max", 7.1)

        if vib_value < z_a:
            zone = "Zone A - Normal (Compliant)"
            passed = True
            rule_verdict = "COMPLIANT"
        elif vib_value <= z_b:
            zone = "Zone B - Acceptable for Restricted Long-Term Operation (Alert)"
            passed = True
            has_alert_zone_b = True
            rule_verdict = "NEEDS_REVIEW"
        elif vib_value <= z_c:
            zone = "Zone C - Unsatisfactory (Non-Compliant / Action Required)"
            passed = False
            has_non_compliant = True
            rule_verdict = "NON_COMPLIANT"
        else:
            zone = "Zone D - Unacceptable Vibration (Immediate Emergency Shutdown)"
            passed = False
            has_non_compliant = True
            rule_verdict = "NON_COMPLIANT"

        # Check borderline (within 10% of 4.5 mm/s or 2.8 mm/s)
        if (z_b * 0.90 <= vib_value <= z_b * 1.10) or (z_a * 0.90 <= vib_value <= z_a * 1.10):
            is_borderline = True

        rule_results.append({
            "rule_field": "vibration_velocity_rms",
            "field": "vibration_velocity_rms",
            "field_label": "Vibration Velocity RMS (mm/s)",
            "actual_value": vib_value,
            "threshold": z_b,
            "operator": "<=",
            "passed": passed,
            "zone_label": zone,
            "verdict": rule_verdict,
            "sop_reference": "ISO-10816-3 / SOP-MNT-042",
            "description": f"Observed {vib_value} mm/s classified deterministically as {zone}",
            "is_sanitized": is_valid
        })

    # 2. Evaluate Bearing / Seal Temperature
    temp_value = None
    for t_field in ["bearing_temperature", "bearing_temp", "seal_temp", "bearing_oil_temp", "oil_temperature", "bearing_temp_c", "seal_temperature_c"]:
        t = find_field_in_dict(extracted_fields, t_field)
        if t is not None:
            temp_value = t
            break

    if temp_value is not None:
        is_valid, warn_msg = sanitize_and_validate_value("bearing_temperature", temp_value)
        if not is_valid and warn_msg:
            sanitization_warnings.append(warn_msg)
            has_sanitization_failure = True

        temp_cfg = standards.get("ISO_10816_3", {}).get("parameters", {}).get("bearing_temperature", {})
        max_temp = temp_cfg.get("thresholds", {}).get("max_allowable", 80.0)
        t_passed = temp_value <= max_temp
        if not t_passed:
            has_non_compliant = True

        if abs(temp_value - max_temp) / max_temp <= 0.10:
            is_borderline = True

        rule_results.append({
            "rule_field": "bearing_temperature",
            "field": "bearing_temperature",
            "field_label": "Bearing / Seal Temperature (°C)",
            "actual_value": temp_value,
            "threshold": max_temp,
            "operator": "<=",
            "passed": t_passed,
            "zone_label": f"Normal Bearing Temperature (<= {max_temp} °C)" if t_passed else f"Overheating Violation (> {max_temp} °C)",
            "verdict": "COMPLIANT" if t_passed else "NON_COMPLIANT",
            "sop_reference": "SOP-MNT-042",
            "description": f"Observed {temp_value} °C vs max allowable {max_temp} °C ({'PASS' if t_passed else 'FAIL'})",
            "is_sanitized": is_valid
        })

    # 3. Evaluate Valve Parameters (SOP-SAF-104)
    valve_cfg = standards.get("SOP_SAF_104", {}).get("parameters", {})
    # Operating Pressure
    press_val = None
    for p_f in ["operating_pressure", "line_pressure", "inlet_pressure", "line_pressure_bar"]:
        p = find_field_in_dict(extracted_fields, p_f)
        if p is not None:
            press_val = p
            break
    if press_val is not None:
        max_p = valve_cfg.get("operating_pressure", {}).get("thresholds", {}).get("max_allowable", 150.0)
        p_passed = press_val <= max_p
        if not p_passed:
            has_non_compliant = True
        rule_results.append({
            "rule_field": "operating_pressure",
            "field": "operating_pressure",
            "field_label": "Operating Line Pressure (bar)",
            "actual_value": press_val,
            "threshold": max_p,
            "operator": "<=",
            "passed": p_passed,
            "zone_label": f"Normal Line Pressure (<= {max_p} bar)" if p_passed else "Overpressure Violation",
            "verdict": "COMPLIANT" if p_passed else "NON_COMPLIANT",
            "sop_reference": "SOP-SAF-104",
            "description": f"Observed {press_val} bar vs threshold {max_p} bar ({'PASS' if p_passed else 'FAIL'})",
            "is_sanitized": True
        })

    # Toxic Gas Concentration
    gas_val = None
    for g_f in ["toxic_gas", "h2s_concentration", "gas_leak", "toxic_gas_concentration", "toxic_gas_ppm"]:
        g = find_field_in_dict(extracted_fields, g_f)
        if g is not None:
            gas_val = g
            break
    if gas_val is not None:
        max_g = valve_cfg.get("toxic_gas_concentration", {}).get("thresholds", {}).get("max_allowable", 25.0)
        g_passed = gas_val <= max_g
        if not g_passed:
            has_non_compliant = True
        rule_results.append({
            "rule_field": "toxic_gas_concentration",
            "field": "toxic_gas_concentration",
            "field_label": "Toxic Gas Concentration (ppm)",
            "actual_value": gas_val,
            "threshold": max_g,
            "operator": "<=",
            "passed": g_passed,
            "zone_label": f"Safe Atmosphere (<= {max_g} ppm)" if g_passed else "Toxic Gas Leak Hazard",
            "verdict": "COMPLIANT" if g_passed else "NON_COMPLIANT",
            "sop_reference": "SOP-SAF-104",
            "description": f"Observed {gas_val} ppm vs threshold {max_g} ppm ({'PASS' if g_passed else 'FAIL'})",
            "is_sanitized": True
        })

    # Actuation Time
    act_val = None
    for a_f in ["actuation_time", "closing_time", "stroke_time", "actuation_time_s"]:
        a = find_field_in_dict(extracted_fields, a_f)
        if a is not None:
            act_val = a
            break
    if act_val is not None:
        max_a = valve_cfg.get("actuation_time", {}).get("thresholds", {}).get("max_allowable", 2.5)
        a_passed = act_val <= max_a
        if not a_passed:
            has_non_compliant = True
        rule_results.append({
            "rule_field": "actuation_time",
            "field": "actuation_time",
            "field_label": "ESD Actuation Closure Time (s)",
            "actual_value": act_val,
            "threshold": max_a,
            "operator": "<=",
            "passed": a_passed,
            "zone_label": f"Closure Speed Pass (<= {max_a}s)" if a_passed else "Closure Delay Violation",
            "verdict": "COMPLIANT" if a_passed else "NON_COMPLIANT",
            "sop_reference": "SOP-SAF-104",
            "description": f"Observed {act_val}s vs threshold {max_a}s ({'PASS' if a_passed else 'FAIL'})",
            "is_sanitized": True
        })

    if not rule_results:
        return {
            "evaluated": False,
            "sop_reference": sop_reference or "UNKNOWN",
            "config_version": config_version,
            "config_hash": config_hash,
            "reason": "No applicable numerical rule set found for document type/equipment.",
            "overall_verdict": None,
            "rule_results": [],
            "sanitization_warnings": sanitization_warnings,
            "is_borderline": False
        }

    # Authoritative overall verdict determination
    if has_sanitization_failure:
        overall_verdict = "NON_COMPLIANT"
    elif has_non_compliant:
        overall_verdict = "NON_COMPLIANT"
    elif has_alert_zone_b:
        overall_verdict = "NEEDS_REVIEW"
    else:
        overall_verdict = "COMPLIANT"

    return {
        "evaluated": True,
        "config_version": config_version,
        "config_hash": config_hash,
        "sop_reference": sop_reference or "ISO-10816-3 / MRPL-SOP",
        "overall_verdict": overall_verdict,
        "total_rules_evaluated": len(rule_results),
        "rules_passed": sum(1 for r in rule_results if r["passed"]),
        "rules_failed": sum(1 for r in rule_results if not r["passed"]),
        "is_borderline": is_borderline,
        "sanitization_warnings": sanitization_warnings,
        "rule_results": rule_results
    }
