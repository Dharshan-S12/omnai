import os
import sys
import time
import json
import httpx
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

API_BASE_URL = "http://localhost:8000"
SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "samples"))
SAMPLE_IMAGE_PATH = os.path.join(SAMPLE_DIR, "fake_inspection_report.png")

def create_synthetic_inspection_report(file_path: str):
    """
    Creates a clean synthetic industrial inspection report image for local OCR validation.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    width, height = 900, 700
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # Draw border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#1A365D", width=3)
    draw.rectangle([(25, 25), (width - 25, 90)], fill="#1A365D")

    # Header title
    draw.text((45, 42), "SOVEREIGN INDUSTRIAL FACILITY - PUMP INSPECTION REPORT", fill="white")

    # Body text
    y_pos = 120
    report_lines = [
        "Document Reference: RPT-INSP-2024-03-88",
        "Standard Applied: SOP-MNT-042 Routine Pump & Turbine Vibration Inspection",
        "--------------------------------------------------------------------------------",
        "Equipment Tag ID: PMP-7001",
        "Location: Plant 1, Main Pump House Unit 3",
        "Date of Inspection: 2024-03-10",
        "Inspector: E. Sharma, Lead Reliability Engineer",
        "--------------------------------------------------------------------------------",
        "RECORDED MEASUREMENTS & READINGS:",
        "  - Vibration Velocity Peak RMS: 2.1 mm/s",
        "  - Peak Dominant Frequency: 48 Hz",
        "  - Lubrication Oil Cleanliness: ISO 16/13 Satisfactory",
        "  - Mechanical Seal Temperature: 65 deg C (Threshold < 80 deg C)",
        "--------------------------------------------------------------------------------",
        "COMPLIANCE EVALUATION & FINDINGS:",
        "  - Compliance Status: Compliant (Zone A Normal Operating Limits)",
        "  - Visual Inspection: No active seal leaks, oil discoloration, or bearing noise.",
        "  - Operational Recommendation: Approved for continuous operation until next cycle.",
        "--------------------------------------------------------------------------------",
        "Supervisor Approval: Approved by Maintenance Lead / Sovereign Confidential"
    ]

    for line in report_lines:
        if line.startswith("---"):
            draw.line([(45, y_pos + 6), (width - 45, y_pos + 6)], fill="#718096", width=1)
            y_pos += 18
        elif line.startswith("RECORDED") or line.startswith("COMPLIANCE") or line.startswith("Equipment"):
            draw.text((45, y_pos), line, fill="#1A202C")
            y_pos += 26
        else:
            draw.text((45, y_pos), line, fill="#2D3748")
            y_pos += 24

    image.save(file_path, "PNG")
    print(f"[0] Generated Synthetic Inspection Report at:\n    {file_path} ({os.path.getsize(file_path)} bytes)")
    return file_path

def test_ocr():
    print("########################################################")
    print("## SOVEREIGN ON-PREM STRUCTURED OCR EXTRACTION TEST   ##")
    print("########################################################")

    # Step 0: Ensure synthetic inspection report exists
    image_path = create_synthetic_inspection_report(SAMPLE_IMAGE_PATH)

    # Step 1: Submit OCR task
    payload = {
        "task_type": "ocr",
        "input_ref": image_path
    }

    print(f"\n[1] Submitting OCR Task with image: {image_path}")
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(f"{API_BASE_URL}/tasks/", json=payload)
            res.raise_for_status()
            task = res.json()
            task_id = task["id"]
            print(f" -> Task Created! ID: {task_id}, Status: {task['status']}")
    except Exception as e:
        print(f"Error submitting OCR task: {e}")
        print("Ensure FastAPI server is running on http://localhost:8000")
        return None

    print(f"\n[2] Polling OCR Execution Trace (Task ID: {task_id})...")
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
                    print(f" -> Status: {status.upper()} | Logged Steps: {len(steps)}", flush=True)
                    last_step_count = len(steps)

                if status in ["done", "failed"]:
                    print(f"\n[3] OCR Task Finished with Status: {status.upper()}")
                    print("\n--- STEP TRACE TIMELINE ---")
                    has_classify = False
                    has_extract = False
                    classified_type = ""

                    for s in steps:
                        tool_badge = f" [Tool: {s.get('tool_called')}]" if s.get('tool_called') else ""
                        print(f" • Step {s.get('step_number')}: {s.get('description')}{tool_badge}")
                        if s.get("tool_called") == "ocr_classify":
                            has_classify = True
                            classified_type = s.get("tool_result", {}).get("doc_type", "")
                        if s.get("tool_called") == "ocr_extract_fields":
                            has_extract = True
                        res_obj = s.get("tool_result")
                        if res_obj:
                            preview_obj = {}
                            for k, v in res_obj.items():
                                if isinstance(v, str) and len(v) > 150:
                                    preview_obj[k] = v[:150] + "... (truncated)"
                                else:
                                    preview_obj[k] = v
                            print(f"   Details: {json.dumps(preview_obj, indent=2)}")

                    if status != "done":
                        print("OCR execution failed.")
                        return None

                    print(f"\n[4] Structured Output Payload:")
                    print("--------------------------------------------------------")
                    try:
                        parsed_out = json.loads(data.get("output_ref", "{}"))
                        print(json.dumps(parsed_out, indent=2))
                    except Exception:
                        print(data.get("output_ref"))
                    print("--------------------------------------------------------")

                    # Validations
                    is_insp_report = "inspection" in classified_type.lower() or classified_type == "inspection_report"
                    has_equipment_id = "PMP" in str(data.get("output_ref")) or "7001" in str(data.get("output_ref"))

                    print("\n========================================================")
                    print("=== OCR STRUCTURED EXTRACTION VERIFICATION SUMMARY ===")
                    print(f"Classification Step Logged: {'PASSED' if has_classify else 'FAILED'}")
                    print(f"Doc Type Identified:        {'PASSED (' + classified_type + ')' if is_insp_report else 'WARNING (' + classified_type + ')'}")
                    print(f"Extraction Step Logged:     {'PASSED' if has_extract else 'FAILED'}")
                    print(f"Key Fields Detected:        {'PASSED' if has_equipment_id else 'FAILED'}")
                    print("========================================================")

                    if has_classify and has_extract:
                        return task_id
                    return None

            time.sleep(2)
        except Exception as poll_err:
            print(f"Polling error: {poll_err}")
            time.sleep(2)

    print("\nTimeout waiting for OCR task.")
    return None

if __name__ == "__main__":
    test_ocr()
