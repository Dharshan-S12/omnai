import os
from typing import Optional
from app.models.ollama_client import generate_vision

VALID_DOC_TYPES = [
    "inspection_report",
    "engineering_drawing",
    "pid_diagram",
    "financial_report",
    "vendor_document",
    "correspondence",
    "confidential_strategy",
    "other"
]

async def classify_document_type(image_path: str, model: str = "qwen2.5vl:7b") -> str:
    """
    Classify a scanned or photographed document image into a standard industrial document category.
    Strictly uses the local vision model (qwen2.5vl:7b) with no external cloud calls.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    prompt = (
        "Classify this document image into EXACTLY ONE of the following categories:\n"
        "- inspection_report\n"
        "- engineering_drawing\n"
        "- pid_diagram\n"
        "- financial_report\n"
        "- vendor_document\n"
        "- correspondence\n"
        "- confidential_strategy\n"
        "- other\n\n"
        "Instructions:\n"
        "- Return ONLY the category name in lowercase with underscores.\n"
        "- Do not include any explanations, markdown, or punctuation."
    )

    try:
        raw_response = await generate_vision(prompt=prompt, image_path=image_path, model=model)
        cleaned = raw_response.strip().lower().replace('"', '').replace("'", "").replace(".", "").strip()

        # Direct match check
        for doc_type in VALID_DOC_TYPES:
            if doc_type == cleaned or doc_type in cleaned:
                return doc_type

        # Keyword heuristics for edge-case vision outputs
        if "inspection" in cleaned or "report" in cleaned and "pump" in cleaned:
            return "inspection_report"
        elif "drawing" in cleaned or "cad" in cleaned or "blueprint" in cleaned or "schematic" in cleaned:
            return "engineering_drawing"
        elif "pid" in cleaned or "p&id" in cleaned or "piping" in cleaned or "instrumentation" in cleaned:
            return "pid_diagram"
        elif "financial" in cleaned or "balance" in cleaned or "revenue" in cleaned or "income" in cleaned:
            return "financial_report"
        elif "vendor" in cleaned or "supplier" in cleaned or "invoice" in cleaned or "purchase" in cleaned:
            return "vendor_document"
        elif "letter" in cleaned or "memo" in cleaned or "email" in cleaned or "correspondence" in cleaned:
            return "correspondence"
        elif "strategy" in cleaned or "confidential" in cleaned or "roadmap" in cleaned:
            return "confidential_strategy"

        return "other"

    except Exception as e:
        print(f"Warning: OCR classification failed, falling back to 'other': {e}")
        return "other"
