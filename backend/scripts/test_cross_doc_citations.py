import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent.cross_doc import verify_citations_against_sources

def test_cross_doc_citations():
    print("=" * 70)
    print("   TEST: Cross-Document Inline Citation Tagging & Factual Verifier     ")
    print("=" * 70)

    # Mock historical source records
    source_records = [
        {"id": "dbbec45c-cea8-424e-b0ec-49d946a1cd6d", "short_id": "dbbec45c", "task_type": "doc_gen"},
        {"id": "71547860-41b5-4e62-85b6-c95a2332ac84", "short_id": "71547860", "task_type": "ocr"}
    ]

    # 1. Valid synthesis text with valid inline citations
    valid_synthesis = (
        "# Executive Cross-Plant Briefing\n"
        "- Turbine TRB-1105 vibration recorded at 5.8 mm/s in Zone C [Task #dbbec45c:vibration_rms].\n"
        "- Scanned inspection sheet confirmed bearing temperature was 78 °C [Task #71547860:temp]."
    )

    _, report_valid = verify_citations_against_sources(valid_synthesis, source_records)
    print(f" -> Valid Synthesis Citation Audit: Total={report_valid['total_citations']}, Verified={report_valid['verified_citations']}, Grounded={report_valid['is_grounded']}")
    assert report_valid["total_citations"] == 2
    assert report_valid["verified_citations"] == 2
    assert report_valid["is_grounded"] is True

    # 2. Synthesis text with an injected hallucinated/non-existent task ID
    hallucinated_synthesis = (
        "- Unverified anomaly claim referencing fabricated record [Task #99999999:unknown]."
    )
    _, report_hallucinated = verify_citations_against_sources(hallucinated_synthesis, source_records)
    print(f" -> Hallucinated Citation Audit: Total={report_hallucinated['total_citations']}, Unverified={report_hallucinated['unverified_citations']}, Grounded={report_hallucinated['is_grounded']}")
    assert report_hallucinated["unverified_citations"] == 1
    assert report_hallucinated["is_grounded"] is False, "Fabricated task citation must be flagged as ungrounded"

    print("\n[PASS] Inline citation extraction and source record verification verified successfully!")
    print("=" * 70)

if __name__ == "__main__":
    test_cross_doc_citations()
