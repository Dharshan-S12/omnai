import asyncio
import json
import sys
sys.path.insert(0, ".")
from app.models.ollama_client import generate_text

sample_text = """EQUIPMENT VIBRATION INSPECTION REPORT
Plant / Facility: Sample Refinery Operations Unit
Department: Mechanical Maintenance
Equipment: Centrifugal Pump P-101
Equipment Tag: P-101A
Inspection Date: 01 September 2026
Inspection Type: Routine Predictive Maintenance
Technician: Maintenance Inspection Team

Vibration Measurement Data:
Measurement Point | Velocity (mm/s RMS) | Condition
Motor Drive End | 1.8 | Normal
Motor Non-Drive End | 2.1 | Normal
Pump Drive End | 1.9 | Normal
Pump Non-Drive End | 2.3 | Normal

Compliance Requirement:
For this demonstration dataset, the acceptance criterion is defined as ISO Zone A vibration velocity RMS < 2.8 mm/s.

Expected Compliance Logic:
2.1 mm/s < 2.8 mm/s -> COMPLIANT
"""

prompt = f"""You are an advanced sovereign OCR & document intelligence engine.
Analyze the source document and extract all data dynamically into a structured JSON representation reflecting the ACTUAL structure and content of this document.

Format:
```json
{{
  "document_title": "Title of document",
  "document_type": "specific document category",
  "metadata": {{
    "Plant / Facility": "...",
    "Department": "...",
    "Equipment": "...",
    "Equipment Tag": "...",
    "Inspection Date": "...",
    "Technician": "..."
  }},
  "tables": [
    {{
      "title": "Vibration Measurement Data",
      "headers": ["Measurement Point", "Velocity (mm/s RMS)", "Condition"],
      "rows": [
        ["Motor Drive End", "1.8", "Normal"],
        ["Motor Non-Drive End", "2.1", "Normal"],
        ["Pump Drive End", "1.9", "Normal"],
        ["Pump Non-Drive End", "2.3", "Normal"]
      ]
    }}
  ],
  "compliance_status": "COMPLIANT / NON-COMPLIANT / SATISFACTORY / WARNING",
  "compliance_notes": "Criteria and threshold evaluation",
  "findings_and_summary": "Comprehensive summary of observations and data"
}}
```

Document content:
{sample_text}

Output ONLY the JSON object within a ```json ``` block."""

async def run_test():
    res = await generate_text(prompt=prompt, model="qwen2.5:3b")
    print("--- EXTRACTED JSON ---")
    print(res)

if __name__ == '__main__':
    asyncio.run(run_test())
