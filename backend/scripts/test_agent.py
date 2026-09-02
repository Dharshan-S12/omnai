import time
import httpx
import json

API_BASE_URL = "http://localhost:8000"

def submit_and_poll_task(task_type: str, input_prompt: str, description: str):
    print(f"\n========================================================")
    print(f"=== TEST: {description} ===")
    print(f"========================================================")
    print(f"Task Type: {task_type}")
    print(f"Prompt: {input_prompt}")

    # 1. Submit task
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(
                f"{API_BASE_URL}/tasks/",
                json={"task_type": task_type, "input_ref": input_prompt}
            )
            res.raise_for_status()
            task_data = res.json()
            task_id = task_data["id"]
            print(f"\n[1] Task Submitted Successfully! Task ID: {task_id}")
    except Exception as e:
        print(f"Failed to submit task: {e}")
        print("Ensure FastAPI server is running on http://localhost:8000")
        return False

    # 2. Poll task status
    print(f"\n[2] Polling Multi-Step Execution Trace...", flush=True)
    start_time = time.time()
    max_wait = 180  # seconds

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
                    print(f" -> Status: {status.upper()} | Logged Steps: {len(steps)}")
                    last_step_count = len(steps)

                if status in ["done", "failed"]:
                    print(f"\n[3] Task Finished with Status: {status.upper()}")
                    print("\n--- STEP TRACE TIMELINE ---")
                    for s in steps:
                        tool_badge = f" [Tool: {s.get('tool_called')}]" if s.get('tool_called') else ""
                        print(f" • Step {s.get('step_number')}: {s.get('description')}{tool_badge}")
                        res_obj = s.get("tool_result")
                        if res_obj:
                            # Truncate large strings for compact printing
                            preview_obj = {}
                            for k, v in res_obj.items():
                                if isinstance(v, str) and len(v) > 200:
                                    preview_obj[k] = v[:200] + "... (truncated)"
                                else:
                                    preview_obj[k] = v
                            print(f"   Details: {json.dumps(preview_obj, indent=2)}")

                    print(f"\n[4] Final Synthesized Output:")
                    print("--------------------------------------------------------")
                    print(data.get("output_ref"))
                    print("--------------------------------------------------------")

                    # Verify output endpoint
                    out_res = client.get(f"{API_BASE_URL}/tasks/{task_id}/output")
                    print(f"\n[5] Verified GET /tasks/{task_id}/output -> HTTP {out_res.status_code} ({len(out_res.text)} bytes)")
                    return status == "done"

            time.sleep(2)
        except Exception as poll_err:
            print(f"Polling error: {poll_err}")
            time.sleep(2)

    print("\nTimeout waiting for task completion.")
    return False

def run_all_agent_tests():
    print("########################################################")
    print("## SOVEREIGN ON-PREM AGENTIC PIPELINE (PHASE 3) TEST  ##")
    print("########################################################")

    # Test 1: RAG-Grounded Multi-Step Document Synthesis (doc_gen)
    t1_success = submit_and_poll_task(
        task_type="doc_gen",
        input_prompt="Draft an approval note referencing our inspection report SOP for a routine pump inspection.",
        description="RAG-Grounded Document Generation (SOP Retrieval + Plan + Synthesis)"
    )

    # Test 2: Multi-Step Calculation with Code Execution Sandbox (code_exec)
    t2_success = submit_and_poll_task(
        task_type="code_exec",
        input_prompt="Calculate the mean and standard deviation for vibration sensor readings [4.1, 4.3, 4.9, 3.8, 4.2] and evaluate compliance with threshold 4.5.",
        description="Code Sandbox Execution (Python Subprocess Isolation)"
    )

    print("\n========================================================")
    print("=== SUMMARY RESULTS ===")
    print(f"Test 1 (RAG + Doc Gen): {'PASSED' if t1_success else 'FAILED'}")
    print(f"Test 2 (Code Sandbox):   {'PASSED' if t2_success else 'FAILED'}")
    print("========================================================")

if __name__ == "__main__":
    run_all_agent_tests()
