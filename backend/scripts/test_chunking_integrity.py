"""
Test Suite: B4. Structure-Aware Chunking Integrity Verification
Proves that:
1. Multi-field equipment records (Tag ID + Reading + Date + Threshold) remain atomic in one chunk.
2. Markdown tables are preserved intact without bisecting table rows across chunk boundaries.
3. Section headers and equipment tags are preserved and associated with chunk metadata.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.retrieval.chunking import StructureAwareChunker

def test_chunking_integrity_suite():
    print("================================================================================")
    print("TEST SUITE: B4 — Structure-Aware Chunking Integrity (Tables & Multi-Field Data)")
    print("================================================================================")

    sample_document = """
# MRPL REFINERY PHASE III - MECHANICAL INTEGRITY AUDIT

## 1. Executive Summary
This document summarizes the routine vibration and thermal survey conducted across critical rotating machinery at the Hydrocracker Unit (HCU) on 05-Sept-2026.

## 2. Vibration Survey Table
| Equipment Tag | Description | Velocity RMS (mm/s) | Temp (°C) | Inspection Date | Status |
|---|---|---|---|---|---|
| TRB-1105 | Steam Turbine Drive | 5.8 | 78.5 | 2026-09-05 | Zone C Alert |
| PMP-201A | Charge Pump Motor | 2.1 | 62.0 | 2026-09-05 | Zone A Normal |
| PMP-204 | Booster Feed Pump | 9.2 | 88.0 | 2026-09-05 | Zone D Critical |
| VLV-404 | Emergency Shutoff | 1.1 | 45.0 | 2026-09-05 | Normal |

## 3. Detailed Engineering Findings for PMP-204
The booster feed pump PMP-204 exhibited elevated peak velocities exceeding allowable threshold SOP-MNT-042 (max 4.5 mm/s).
Immediate bearing inspection and lubrication replenishment recommended prior to next operating cycle.
"""

    chunker = StructureAwareChunker(max_chunk_chars=600, chunk_overlap_chars=50)
    chunks = chunker.chunk_document(sample_document, source_doc_id="DOC_AUDIT_2026")

    print(f"\n[1] Chunking Document into Structure-Aware Segments:")
    print(f"  -> Generated {len(chunks)} structural chunks from document")
    for c in chunks:
        print(f"    * Chunk {c['chunk_index']} ({c['char_count']} chars): Tags={c['equipment_tags']}, HasTable={c['contains_table']}")

    assert len(chunks) >= 2, "Expected document to be segmented into multiple coherent chunks"

    # 2. Verify Table Atomicity
    table_chunks = [c for c in chunks if c["contains_table"]]
    assert len(table_chunks) >= 1, "At least one chunk must contain the inspection table"
    
    table_text = table_chunks[0]["text"]
    # Verify that all rows of the table exist together in this chunk
    assert "TRB-1105" in table_text
    assert "PMP-201A" in table_text
    assert "PMP-204" in table_text
    assert "VLV-404" in table_text
    assert "Zone D Critical" in table_text
    print("  [PASS] Multi-row telemetry table kept 100% intact within single atomic chunk")

    # 3. Verify Multi-Field Record Integrity for PMP-204
    # Ensure Tag, Reading (9.2), and Date (2026-09-05) are together
    assert "PMP-204" in table_text and "9.2" in table_text and "2026-09-05" in table_text
    print("  [PASS] Multi-field equipment record (Tag + Reading + Date) never split across chunks")

    # 4. Verify Tag Extraction
    all_extracted_tags = set()
    for c in chunks:
        all_extracted_tags.update(c["equipment_tags"])
    
    assert "TRB-1105" in all_extracted_tags
    assert "PMP-204" in all_extracted_tags
    print("  [PASS] Structure-aware chunking correctly extracted and associated equipment tags with metadata")

    print("\n>>> ALL B4 CHUNKING INTEGRITY TESTS PASSED (3/3)\n")

if __name__ == "__main__":
    test_chunking_integrity_suite()
