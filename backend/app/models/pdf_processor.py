import os
import re
import json
import tempfile
from typing import Dict, Any, List
import pypdf
import pypdfium2

from app.models.ollama_client import generate_text
from app.models.ocr_classify import classify_document_type
from app.models.ocr_extract import extract_structured_fields

MAX_PDF_PAGES = 10

def is_pdf(file_path: str) -> bool:
    """Check if the provided file path is a PDF by extension or magic byte."""
    if not file_path or not os.path.exists(file_path):
        return False
    if file_path.lower().endswith(".pdf"):
        return True
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
            return header.startswith(b"%PDF-")
    except Exception:
        return False

def _extract_text_layer(file_path: str, max_pages: int = MAX_PDF_PAGES):
    """
    Extract embedded text layer using pypdf.
    Returns (page_texts, total_pages, is_truncated).
    """
    reader = pypdf.PdfReader(file_path)
    total_pages = len(reader.pages)
    pages_to_process = min(total_pages, max_pages)
    is_truncated = total_pages > max_pages

    page_texts = []
    for i in range(pages_to_process):
        try:
            txt = reader.pages[i].extract_text() or ""
            page_texts.append(txt.strip())
        except Exception:
            page_texts.append("")

    return page_texts, total_pages, is_truncated

async def _classify_text_content(text_content: str, model: str = "qwen2.5:3b") -> str:
    """Classify document category based on extracted text content."""
    prompt = (
        "Classify the following extracted document text into EXACTLY ONE of these categories:\n"
        "- inspection_report\n"
        "- engineering_drawing\n"
        "- pid_diagram\n"
        "- financial_report\n"
        "- vendor_document\n"
        "- correspondence\n"
        "- confidential_strategy\n"
        "- other\n\n"
        f"Document Text:\n{text_content[:2000]}\n\n"
        "Instructions: Return ONLY the category name in lowercase with underscores."
    )
    try:
        res = await generate_text(prompt=prompt, model=model)
        cleaned = res.strip().lower().replace('"', '').replace("'", "").replace(".", "").strip()
        for valid in [
            "inspection_report", "engineering_drawing", "pid_diagram",
            "financial_report", "vendor_document", "correspondence",
            "confidential_strategy"
        ]:
            if valid in cleaned:
                return valid
        return "other"
    except Exception:
        # Heuristic fallback
        lower = text_content.lower()
        if "inspection" in lower or "pump" in lower or "vibration" in lower:
            return "inspection_report"
        elif "drawing" in lower or "sheet" in lower:
            return "engineering_drawing"
        elif "financial" in lower or "balance" in lower:
            return "financial_report"
        elif "vendor" in lower or "supplier" in lower:
            return "vendor_document"
        return "other"

async def _extract_structured_from_text(
    text_content: str,
    doc_type: str = "document",
    model: str = "qwen2.5:3b"
) -> Dict[str, Any]:
    """Parse dynamic structured JSON fields, tables, and metadata from document text."""
    prompt = f"""You are an advanced sovereign OCR & document intelligence engine.
Analyze the source document text and extract ALL data dynamically into a structured JSON representation reflecting the ACTUAL structure, tables, and key-values of this document.

Extract into this format:
```json
{{
  "document_title": "Full title extracted from text header",
  "document_type": "Specific document category",
  "metadata": {{
    "Field 1": "Value 1",
    "Field 2": "Value 2"
  }},
  "tables": [
    {{
      "title": "Table Title",
      "headers": ["Col 1", "Col 2", "Col 3"],
      "rows": [
        ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"]
      ]
    }}
  ],
  "compliance_status": "COMPLIANT / NON-COMPLIANT / SATISFACTORY / WARNING (or null if not applicable)",
  "compliance_notes": "Criteria or threshold analysis if mentioned",
  "findings": "Detailed summary of observations, data points, and conclusions"
}}
```

Source Document Text:
{text_content[:6000]}

Output ONLY the JSON object within a ```json ``` block."""

    try:
        raw_response = await generate_text(prompt=prompt, model=model, timeout_seconds=120.0)
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

        parsed = json.loads(json_str)
        if isinstance(parsed, dict):
            if "document_type" not in parsed or not parsed["document_type"]:
                parsed["document_type"] = doc_type
            return parsed
        return {"document_type": doc_type, "data": parsed}
    except Exception as err:
        return {
            "document_type": doc_type,
            "raw_text": text_content[:2000],
            "parse_error": True,
            "error_detail": str(err)
        }

async def process_pdf_document(
    file_path: str,
    max_pages: int = MAX_PDF_PAGES,
    vision_model: str = "qwen2.5vl:7b",
    text_model: str = "qwen2.5:3b"
) -> Dict[str, Any]:
    """
    Process PDF documents transparently:
    - Path A (text_extraction): Fast text-layer extraction via pypdf
    - Path B (vision_ocr): Scanned page rendering via pypdfium2 + qwen2.5vl:7b OCR
    Capped at max_pages (default 10) with truncation tracking.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF document not found at {file_path}")

    # 1. Attempt Text Layer Extraction (Path A)
    page_texts, total_pages, is_truncated = _extract_text_layer(file_path, max_pages=max_pages)
    combined_text = "\n\n".join(
        f"--- Page {i+1} ---\n{t}" for i, t in enumerate(page_texts) if t
    ).strip()

    total_text_length = sum(len(t) for t in page_texts)

    if total_text_length >= 50:
        # PATH A: Text Layer Extraction (Native digital PDF)
        doc_type = await _classify_text_content(combined_text, model=text_model)
        structured_data = await _extract_structured_from_text(combined_text, doc_type=doc_type, model=text_model)

        structured_data["processing_path"] = "text_extraction"
        structured_data["page_count"] = len(page_texts)
        structured_data["total_pages"] = total_pages
        structured_data["truncated"] = is_truncated
        structured_data["raw_text"] = combined_text
        return structured_data

    # 2. Scanned PDF: Render Pages to Images via pypdfium2 (Path B)
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf = pypdfium2.PdfDocument(file_path)
        total_pages = len(pdf)
        pages_to_process = min(total_pages, max_pages)
        is_truncated = total_pages > max_pages

        rendered_image_paths: List[str] = []
        for i in range(pages_to_process):
            page = pdf[i]
            # Render at 2x scale (~144 DPI) for OCR clarity
            image = page.render(scale=2.0).to_pil()
            img_path = os.path.join(temp_dir, f"rendered_page_{i+1}.png")
            image.save(img_path, format="PNG")
            rendered_image_paths.append(img_path)

        if not rendered_image_paths:
            return {
                "document_type": "other",
                "processing_path": "vision_ocr",
                "page_count": 0,
                "total_pages": total_pages,
                "truncated": is_truncated,
                "raw_text": "Empty PDF document (0 renderable pages)",
                "parse_error": True
            }

        # Classify using first page
        doc_type = await classify_document_type(rendered_image_paths[0], model=vision_model)

        # Extract structured fields for each page
        all_page_results: List[Dict[str, Any]] = []
        all_raw_texts: List[str] = []

        for idx, img_p in enumerate(rendered_image_paths):
            res = await extract_structured_fields(img_p, doc_type=doc_type, model=vision_model)
            all_page_results.append(res)
            if res.get("raw_text"):
                all_raw_texts.append(f"--- Page {idx+1} ---\n{res['raw_text']}")
            elif res.get("findings"):
                all_raw_texts.append(f"--- Page {idx+1} ---\n{res['findings']}")

        # Merge page outputs
        primary_result = all_page_results[0].copy()
        primary_result["document_type"] = doc_type
        primary_result["processing_path"] = "vision_ocr"
        primary_result["page_count"] = pages_to_process
        primary_result["total_pages"] = total_pages
        primary_result["truncated"] = is_truncated

        if len(all_page_results) > 1:
            primary_result["multi_page_results"] = all_page_results
            if all_raw_texts:
                primary_result["raw_text"] = "\n\n".join(all_raw_texts)

        return primary_result
