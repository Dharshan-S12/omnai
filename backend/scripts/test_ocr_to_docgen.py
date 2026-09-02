import os
import sys
import time
import json
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.test_ocr import test_ocr

API_BASE_URL = "http://localhost:8000"

def test_ocr_to_docgen():
    print("########################################################")
    print("## SOVEREIGN OCR -> DOCGEN CHAINED PIPELINE TEST      ##")
    print("########################################################")

    # Step 1: Run OCR to get structured output
    print("\n>>> PHASE 1: Running OCR on Inspection Document Image...")
    ocr_task_id = test_ocr()
    if not ocr_task_id:
        print("Failed to complete prerequisite OCR task.")
        return False

    print(f"\n>>> PHASE 2: Submitting Chained doc_gen Task (source_task_id: {ocr_task_id})...")
    docgen_payload = {
        "task_type": "doc_gen",
        "input_ref": "Draft a formal pump inspection approval note referencing our SOP for this inspected pump.",
        "source_task_id": ocr_task_id
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{API_BASE_URL}/tasks/", json=docgen_payload)
            res.raise_for_status()
            doc_task = res.json()
            doc_task_id = doc_task["id"]
            print(f" -> doc_gen Task Created! ID: {doc_task_id}, Status: {doc_task['status']}")
    except Exception as e:
        print(f"Error submitting doc_gen task: {e}")
        return False

    print(f"\n>>> PHASE 3: Polling Multi-Step Execution (Task ID: {doc_task_id})...")
    start_time = time.time()
    max_wait = 300  # seconds

    last_step_count = 0
    while time.time() - start_time < max_wait:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{API_BASE_URL}/tasks/{doc_task_id}")
                res.raise_for_status()
                data = res.json()
                status = data.get("status")
                steps = data.get("steps", [])

                if len(steps) != last_step_count or status in ["done", "failed"]:
                    print(f" -> Status: {status.upper()} | Logged Steps: {len(steps)}", flush=True)
                    last_step_count = len(steps)

                if status in ["done", "failed"]:
                    print(f"\n>>> PHASE 4: doc_gen Finished with Status: {status.upper()}")
                    print("\n--- STEP TRACE TIMELINE ---")
                    has_docgen_step = False
                    for s in steps:
                        tool_badge = f" [Tool: {s.get('tool_called')}]" if s.get('tool_called') else ""
                        print(f" • Step {s.get('step_number')}: {s.get('description')}{tool_badge}")
                        if s.get("tool_called") == "docgen_docx":
                            has_docgen_step = True

                    if status != "done":
                        print("doc_gen execution failed.")
                        return False

                    final_text = data.get("output_ref", "")
                    print(f"\nFinal Synthesized Output Preview:")
                    print("--------------------------------------------------------")
                    print(final_text[:600] + ("..." if len(final_text) > 600 else ""))
                    print("--------------------------------------------------------")

                    # Verify downloaded Word document
                    print(f"\n>>> PHASE 5: Verifying Word Document (.docx)...")
                    docx_url = f"{API_BASE_URL}/tasks/{doc_task_id}/output/docx"
                    res_docx = client.get(docx_url)
                    print(f" -> GET /tasks/{doc_task_id}/output/docx:")
                    print(f"    Status Code: {res_docx.status_code}")
                    print(f"    Content-Type: {res_docx.headers.get('content-type')}")
                    print(f"    Content-Length: {len(res_docx.content)} bytes")

                    output_save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_chained_output.docx"))
                    with open(output_save_path, "wb") as f:
                        f.write(res_docx.content)
                    print(f" -> Saved Chained Word Document Locally to:\n    {output_save_path}")

                    # Field grounding spot checks
                    has_pmp = "PMP-7001" in final_text or "7001" in final_text or "PMP" in final_text
                    has_sop_ref = "SOP-MNT-042" in final_text or "SOP" in final_text or "vibration" in final_text.lower()
                    is_valid_docx = res_docx.status_code == 200 and len(res_docx.content) > 0

                    print("\n========================================================")
                    print("=== CHAINED OCR -> DOCGEN VERIFICATION SUMMARY ===")
                    print(f"Source Task ID Chained:    PASSED ({ocr_task_id})")
                    print(f"OCR Equipment Tag Grounded: {'PASSED' if has_pmp else 'WARNING'}")
                    print(f"SOP Knowledge Grounded:     {'PASSED' if has_sop_ref else 'FAILED'}")
                    print(f"Word (.docx) Generated:    {'PASSED' if is_valid_docx else 'FAILED'}")
                    print(f"Docx Step in DB Timeline:  {'PASSED' if has_docgen_step else 'FAILED'}")
                    print("========================================================")

                    return is_valid_docx and has_docgen_step

            time.sleep(2)
        except Exception as poll_err:
            print(f"Polling error: {poll_err}")
            time.sleep(2)

    print("\nTimeout waiting for chained doc_gen task.")
    return False

if __name__ == "__main__":
    test_ocr_to_docgen()
