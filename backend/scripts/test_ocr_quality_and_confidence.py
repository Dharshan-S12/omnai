import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.pdf_processor import evaluate_text_layer_quality
from app.models.ocr_extract import evaluate_numeric_reading_confidence

def test_ocr_quality_and_confidence():
    print("=" * 70)
    print("   TEST: OCR Digital Text Quality Fallback & Numeric Confidence Gating")
    print("=" * 70)

    # 1. Clean High-Quality Digital Text Layer
    clean_text = (
        "MRPL ROUTINE PUMP INSPECTION REPORT\n"
        "Equipment ID: PMP-204 | Unit: CDU | Date: 2026-09-01\n"
        "Vibration Velocity RMS: 2.4 mm/s | Bearing Temperature: 68.5 °C\n"
        "Status: COMPLIANT according to ISO 10816-3 Group 1 standards."
    )
    score_clean, reason_clean = evaluate_text_layer_quality(clean_text)
    print(f" -> Clean Text Quality: Score={score_clean:.2f}, Diagnostic='{reason_clean}'")
    assert score_clean >= 0.70, f"Clean text layer must pass with quality >= 0.70, got {score_clean}"

    # 2. Corrupted / Garbled Digital Text Layer (Broken font encoding)
    corrupted_text = (
        "\x00\ufffd?\ufffd?\x00\x01\x02\x03\ufffd\ufffd?????????\n"
        "\x00\ufffd\ufffd???????????????"
    )
    score_corrupt, reason_corrupt = evaluate_text_layer_quality(corrupted_text)
    print(f" -> Corrupted Text Quality: Score={score_corrupt:.2f}, Diagnostic='{reason_corrupt}'")
    assert score_corrupt < 0.70, f"Corrupted text layer must fail quality check (<0.70) and trigger Vision OCR fallback, got {score_corrupt}"

    # 3. Numeric Confidence Scoring - Plausible reading (2.4 mm/s)
    conf_norm, manual_norm, _ = evaluate_numeric_reading_confidence("vibration_rms", "2.4 mm/s")
    print(f" -> Normal Reading (2.4 mm/s): Conf={conf_norm}%, NeedsManual={manual_norm}")
    assert conf_norm >= 85.0 and manual_norm is False, "Normal reading must have >=85% confidence and not require manual verification"

    # 4. Outlier reading requiring manual verification (e.g. 710 mm/s or non-numeric)
    conf_outlier, manual_outlier, warn_outlier = evaluate_numeric_reading_confidence("vibration_rms", "710 mm/s")
    print(f" -> Outlier Reading (710 mm/s): Conf={conf_outlier}%, NeedsManual={manual_outlier}, Alert='{warn_outlier}'")
    assert conf_outlier < 85.0 and manual_outlier is True, "Outlier reading must be flagged with needs_manual_verification=True"

    # 5. Non-numeric garbage in measurement field
    conf_garbage, manual_garbage, warn_garbage = evaluate_numeric_reading_confidence("bearing_temp", "UNKNOWN_TEXT")
    print(f" -> Garbage String: Conf={conf_garbage}%, NeedsManual={manual_garbage}, Alert='{warn_garbage}'")
    assert manual_garbage is True, "Garbage measurement text must require manual verification"

    print("\n[PASS] OCR digital quality fallback and numeric confidence gating verified successfully!")
    print("=" * 70)

if __name__ == "__main__":
    test_ocr_quality_and_confidence()
