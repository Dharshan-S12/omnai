import sys
import httpx
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_auto_routing():
    test_prompts = [
        {"prompt": "Calculate the sum of first 25 prime numbers", "expected_type": "code_exec"},
        {"prompt": "Draft an executive SOP Word document for boiler inspection", "expected_type": "doc_gen"},
        {"prompt": "Compare previous inspection reports and find anomalies", "expected_type": "cross_doc_query"},
        {"prompt": "Summarize the key principles of industrial safety", "expected_type": "text_gen"}
    ]

    print("=== TESTING AUTONOMOUS INTENT ROUTER (/tasks/auto) ===")
    with httpx.Client(timeout=10.0) as client:
        for item in test_prompts:
            payload = {"prompt": item["prompt"]}
            res = client.post(f"{API_BASE_URL}/tasks/auto", json=payload)
            if res.status_code == 200:
                data = res.json()
                detected = data.get("task_type")
                steps = data.get("steps", [])
                first_step = steps[0] if steps else {}
                desc = first_step.get("description", "")
                print(f"\nPrompt: '{item['prompt']}'")
                print(f" -> Auto-Detected Type: {detected} (Expected: {item['expected_type']})")
                print(f" -> Initial Step: {desc}")
                print(f" -> Task ID: {data.get('id')}")
            else:
                print(f"Failed for prompt '{item['prompt']}': {res.status_code} {res.text}")

if __name__ == '__main__':
    test_auto_routing()
