import re
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from app.router.model_router import route_model, ModelRouteDecision, ModelCategory

@dataclass
class ModelChoice:
    model_name: str
    task_type: str
    reason: str
    system_prompt: Optional[str] = None
    downstream_tool: Optional[str] = None

def auto_detect_task_intent(prompt: str, file_path: Optional[str] = None) -> Tuple[str, str, str]:
    """
    Intelligently analyzes the incoming chat prompt and optional file attachment
    to automatically determine the optimal task_type, routing rationale, and initial model.
    """
    prompt_clean = (prompt or "").strip()
    prompt_lower = prompt_clean.lower()

    # 1. If an image or PDF file is provided, prioritize Vision OCR / Document Intelligence
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
            return (
                "ocr",
                f"Document/Image attached ({os.path.basename(file_path)}): Auto-routed to Vision OCR & Dynamic Document Intelligence",
                "qwen2.5vl:7b"
            )

    # 2. Check for Code Execution / Math / Computation Intent
    code_pattern = r"\b(calculate|calc|compute|solve|sum of|prime|primes|fibonacci|factorial|algorithm|python|script|code|numpy|pandas|math|matrix|derivative|integral|multiply|sum of first|execute code|run python)\b"
    if re.search(code_pattern, prompt_lower):
        return (
            "code_exec",
            "Computational / Mathematical / Coding query: Auto-routed to Python Sandboxed Code Engine",
            "qwen2.5-coder:3b"
        )

    # 3. Check for Cross-Document / Historical Task Ledger Intent (latest records, previous tasks, anomalies)
    cross_doc_pattern = r"\b(latest|recent|recorded|record|records|news|problem|problems|updates|events|happened|what happened|previous|past|earlier|history|historical|across documents|cross doc|all tasks|compare reports|previous inspection|ledger|historical tasks|database history|compare previous)\b"
    if re.search(cross_doc_pattern, prompt_lower):
        return (
            "cross_doc_query",
            "Historical / Ledger / Recent Records query: Auto-routed to Cross-Document Ledger Intelligence Engine",
            "qwen2.5:3b"
        )

    # 4. Check for Word Document (.docx) / Executive Report Generation Intent
    doc_gen_pattern = r"\b(word doc|word document|docx|generate doc|generate document|draft sop|generate report|export docx|document template|write sop|create docx|create document)\b"
    if re.search(doc_gen_pattern, prompt_lower):
        return (
            "doc_gen",
            "Executive Document Generation: Auto-routed to Word DocGen Engine",
            "qwen2.5:7b-instruct"
        )

    # 5. Check if the prompt explicitly mentions a file path or image
    if re.search(r"\.(pdf|png|jpg|jpeg)\b", prompt_lower):
        return (
            "ocr",
            "Document file reference detected: Auto-routed to OCR & Document Intelligence Engine",
            "qwen2.5vl:7b"
        )

    # 6. Default to General Text Synthesis & Autonomous Agent Reasoning
    return (
        "text_gen",
        "Autonomous Reasoning: Auto-routed to High-Throughput Agent Reasoning Engine",
        "qwen2.5:3b"
    )

def route_task(task_type: str, input_ref: str) -> ModelChoice:
    """
    Synchronous fallback routing mapping task types to default model choices.
    For full asynchronous model switching with dynamic probing, use route_model().
    """
    normalized_type = (task_type or "").lower()

    if normalized_type == "ocr":
        return ModelChoice(
            model_name="qwen2.5vl:7b",
            task_type="ocr",
            reason="Routed to vision model for document OCR and extraction"
        )
    elif normalized_type == "code_exec":
        return ModelChoice(
            model_name="qwen2.5-coder:3b",
            task_type="code_exec",
            reason="Routed to coding model for Python script synthesis and execution",
            system_prompt="You are an expert Python engineer and data analyst. Write clean, self-contained, executable code adhering to on-prem air-gapped constraints. Output markdown code blocks.",
            downstream_tool="sandbox_exec"
        )
    elif normalized_type == "cross_doc_query":
        return ModelChoice(
            model_name="qwen2.5:3b",
            task_type="cross_doc_query",
            reason="Routed to low-latency model for rapid cross-document synthesis"
        )
    elif normalized_type == "doc_gen":
        return ModelChoice(
            model_name="qwen2.5:7b-instruct",
            task_type="doc_gen",
            reason="Routed to text model for document drafting with downstream document writer tool",
            system_prompt="You are a sovereign confidential document synthesis agent. Generate well-structured technical/industrial documentation based on the user instructions.",
            downstream_tool="doc_writer"
        )
    else:
        return ModelChoice(
            model_name="qwen2.5:3b",
            task_type=normalized_type,
            reason=f"Default routing to fast text model for task type '{normalized_type}'"
        )
