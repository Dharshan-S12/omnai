import os
import re
import json
from typing import Dict, Any, Optional
from app.models.ollama_client import generate_vision

DYNAMIC_EXTRACTION_PROMPT = """You are an advanced on-premise sovereign document OCR & intelligence engine.
Analyze this document image and extract ALL data dynamically into a rich, structured JSON representation that accurately captures the ACTUAL content, tables, and metadata of this document without inventing or forcing empty fields.

Extract into this JSON format:
```json
{
  "document_title": "Full title extracted from header",
  "document_type": "Specific document classification (e.g. Vibration Inspection Report, Equipment Maintenance Log, Invoice, Engineering Drawing, etc.)",
  "metadata": {
    "Field Name 1": "Extracted Value 1",
    "Field Name 2": "Extracted Value 2"
  },
  "tables": [
    {
      "title": "Title of the table if present",
      "headers": ["Column 1", "Column 2", "Column 3"],
      "rows": [
        ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
        ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
      ]
    }
  ],
  "measurements": {
    "metric_name": "recorded value"
  },
  "compliance_status": "COMPLIANT / NON-COMPLIANT / SATISFACTORY / WARNING (or null if not applicable)",
  "compliance_notes": "Extracted threshold, ISO standard, or compliance rule",
  "findings": "Authoritative summary of all key data points, findings, and technical observations"
}
```

Instructions:
1. Extract ALL tables with every row and column accurately.
2. Put all header key-value items (Plant, Department, Equipment, Dates, Technicians, Reference IDs) into `metadata`.
3. If compliance or limits are stated, evaluate the status and put the explanation in `compliance_notes`.
4. Output ONLY valid JSON within a ```json ``` block with no extra conversational text.
"""

async def extract_structured_fields(
    image_path: str,
    doc_type: str = "document",
    model: str = "qwen2.5vl:7b"
) -> Dict[str, Any]:
    """
    Extract dynamic structured key-value fields, tables, and observations from a document image.
    Uses local Ollama vision model defensively parsing the resulting JSON payload.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    prompt = DYNAMIC_EXTRACTION_PROMPT

    try:
        raw_response = await generate_vision(prompt=prompt, image_path=image_path, model=model)
    except Exception as vision_err:
        return {
            "document_type": doc_type,
            "raw_text": f"Vision model error: {str(vision_err)}",
            "parse_error": True,
            "error_detail": str(vision_err)
        }

    # Parse JSON defensively
    try:
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            start = raw_response.find('{')
            end = raw_response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = raw_response[start:end+1].strip()
            else:
                json_str = raw_response.strip()

        parsed_data = json.loads(json_str)
        if isinstance(parsed_data, dict):
            if "document_type" not in parsed_data or not parsed_data["document_type"]:
                parsed_data["document_type"] = doc_type
            return parsed_data
        else:
            return {
                "document_type": doc_type,
                "data": parsed_data
            }

    except Exception as parse_err:
        return {
            "document_type": doc_type,
            "raw_text": raw_response,
            "parse_error": True,
            "error_detail": f"JSON parse error: {str(parse_err)}"
        }
