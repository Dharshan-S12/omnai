import time
import httpx
import json

API_BASE_URL = "http://localhost:8000"

def run_test():
    print("=== [1] Submitting Task to Sovereign Pipeline ===")
    task_payload = {
        "task_type": "text_gen",
        "input_ref": "Summarize in 2 sentences: On-premise agentic AI systems process confidential industrial documents locally without sending telemetry or sensitive data to third-party cloud providers."
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{API_BASE_URL}/tasks/", json=task_payload)
            res.raise_for_status()
            task = res.json()
            task_id = task["id"]
            print(f"Task created successfully! ID: {task_id}, Status: {task['status']}")
    except Exception as e:
        print(f"Error creating task: {e}")
        print("Ensure the FastAPI backend server is running on http://localhost:8000")
        return

    print(f"\n=== [2] Polling Task Execution Trace (Task ID: {task_id}) ===")
    start_time = time.time()
    max_wait = 60 # seconds

    while time.time() - start_time < max_wait:
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{API_BASE_URL}/tasks/{task_id}")
                res.raise_for_status()
                data = res.json()
                status = data.get("status")
                steps = data.get("steps", [])

                print(f"Status: {status.upper()} | Logged Steps: {len(steps)}")

                if status in ["done", "failed"]:
                    print("\n=== [3] Final Task Execution Details ===")
                    print(f"Final Status: {status}")
                    print(f"Output: \n{data.get('output_ref')}\n")

                    print("=== Step Trace Timeline ===")
                    for step in steps:
                        tool_info = f" [Tool: {step.get('tool_called')}]" if step.get('tool_called') else ""
                        print(f" • Step {step.get('step_number')}: {step.get('description')}{tool_info}")
                        if step.get("tool_result"):
                            print(f"   Result: {json.dumps(step.get('tool_result'), indent=2)}")

                    # Test output endpoint
                    print("\n=== [4] Verifying Output Endpoint ===")
                    out_res = client.get(f"{API_BASE_URL}/tasks/{task_id}/output")
                    print(f"GET /tasks/{task_id}/output Status: {out_res.status_code}")
                    print(f"Output Content Length: {len(out_res.text)} bytes")
                    return

            time.sleep(2)
        except Exception as poll_err:
            print(f"Polling error: {poll_err}")
            time.sleep(2)

    print("\nTimeout waiting for task to complete.")

if __name__ == "__main__":
    run_test()
