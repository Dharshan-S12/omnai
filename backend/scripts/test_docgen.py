import time
import os
import httpx
import json

API_BASE_URL = "http://localhost:8000"

def test_docgen():
    print("########################################################")
    print("## SOVEREIGN ON-PREM DOCX GENERATION TEST             ##")
    print("########################################################")

    prompt = "Draft an approval note referencing our inspection report SOP for a routine pump inspection."
    payload = {
        "task_type": "doc_gen",
        "input_ref": prompt
    }

    print(f"\n[1] Submitting doc_gen Task to Pipeline...")
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{API_BASE_URL}/tasks/", json=payload)
            res.raise_for_status()
            task = res.json()
            task_id = task["id"]
            print(f" -> Task Created! ID: {task_id}, Status: {task['status']}")
    except Exception as e:
        print(f"Error submitting task: {e}")
        print("Ensure FastAPI server is running on http://localhost:8000")
        return False

    print(f"\n[2] Polling Multi-Step Execution Trace (Task ID: {task_id})...")
    start_time = time.time()
    max_wait = 300  # seconds

    last_step_count = 0
    while time.time() - start_time < max_wait:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{API_BASE_URL}/tasks/{task_id}")
                res.raise_for_status()
                data = res.json()
                status = data.get("status")
                steps = data.get("steps", [])

                if len(steps) != last_step_count or status in ["done", "failed"]:
                    print(f" -> Status: {status.upper()} | Logged Steps: {len(steps)}", flush=True)
                    last_step_count = len(steps)

                if status in ["done", "failed"]:
                    print(f"\n[3] Task Finished with Status: {status.upper()}")
                    print("\n--- STEP TRACE TIMELINE ---")
                    has_docgen_step = False
                    for s in steps:
                        tool_badge = f" [Tool: {s.get('tool_called')}]" if s.get('tool_called') else ""
                        print(f" • Step {s.get('step_number')}: {s.get('description')}{tool_badge}")
                        if s.get("tool_called") == "docgen_docx":
                            has_docgen_step = True
                        res_obj = s.get("tool_result")
                        if res_obj:
                            preview_obj = {}
                            for k, v in res_obj.items():
                                if isinstance(v, str) and len(v) > 200:
                                    preview_obj[k] = v[:200] + "... (truncated)"
                                else:
                                    preview_obj[k] = v
                            print(f"   Details: {json.dumps(preview_obj, indent=2)}")

                    if status != "done":
                        print("Task execution failed.")
                        return False

                    print(f"\n[4] Verifying Word Document (.docx) Endpoints...")
                    
                    # Test A: GET /tasks/{id}/output?format=docx
                    docx_url_param = f"{API_BASE_URL}/tasks/{task_id}/output?format=docx"
                    res_docx_param = client.get(docx_url_param)
                    print(f" -> GET /tasks/{task_id}/output?format=docx:")
                    print(f"    Status Code: {res_docx_param.status_code}")
                    print(f"    Content-Type: {res_docx_param.headers.get('content-type')}")
                    print(f"    Content-Length: {len(res_docx_param.content)} bytes")

                    # Test B: GET /tasks/{id}/output/docx
                    docx_url_direct = f"{API_BASE_URL}/tasks/{task_id}/output/docx"
                    res_docx_direct = client.get(docx_url_direct)
                    print(f" -> GET /tasks/{task_id}/output/docx:")
                    print(f"    Status Code: {res_docx_direct.status_code}")
                    print(f"    Content-Type: {res_docx_direct.headers.get('content-type')}")
                    print(f"    Content-Length: {len(res_docx_direct.content)} bytes")

                    # Validation checks
                    expected_mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    is_valid_type = expected_mimetype in (res_docx_param.headers.get("content-type") or "")
                    is_valid_size = len(res_docx_param.content) > 0

                    # Save to local test_output.docx
                    output_save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_output.docx"))
                    with open(output_save_path, "wb") as f:
                        f.write(res_docx_param.content)
                    print(f"\n[5] Saved Downloaded Word Document Locally to:")
                    print(f"    {output_save_path} ({os.path.getsize(output_save_path)} bytes)")

                    print("\n========================================================")
                    print("=== DOCX GENERATION VERIFICATION SUMMARY ===")
                    print(f"Status HTTP 200:        {'PASSED' if res_docx_param.status_code == 200 else 'FAILED'}")
                    print(f"Word MIME Type Match:   {'PASSED' if is_valid_type else 'FAILED'}")
                    print(f"Docx Step Logged in DB: {'PASSED' if has_docgen_step else 'FAILED'}")
                    print(f"File Non-Empty:         {'PASSED' if is_valid_size else 'FAILED'}")
                    print("========================================================")

                    return res_docx_param.status_code == 200 and is_valid_type and is_valid_size and has_docgen_step

            time.sleep(2)
        except Exception as poll_err:
            print(f"Polling error: {poll_err}")
            time.sleep(2)

    print("\nTimeout waiting for doc_gen task.")
    return False

if __name__ == "__main__":
    test_docgen()
