import os
import re
import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any

ROUTER_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "router_decisions.jsonl")

DISAMBIGUATION_THRESHOLD = 0.65

@dataclass
class ModelChoice:
    model_name: str
    task_type: str
    reason: str
    system_prompt: Optional[str] = None
    downstream_tool: Optional[str] = None

@dataclass
class IntentRouteResult:
    task_type: str
    routing_reason: str
    model_name: str
    confidence: float
    is_ambiguous: bool = False
    suggested_options: List[Dict[str, str]] = field(default_factory=list)

def log_router_decision(
    prompt: str,
    chosen_intent: str,
    confidence: float,
    routing_reason: str,
    was_disambiguated: bool = False,
    confirmed_by_user: bool = False
) -> Dict[str, Any]:
    """
    Logs every autonomous routing decision to an append-only JSONL log for continuous accuracy auditing.
    """
    os.makedirs(os.path.dirname(ROUTER_LOG_PATH), exist_ok=True)
    decision_record = {
        "id": str(uuid.uuid4()),
        "prompt": prompt,
        "chosen_intent": chosen_intent,
        "confidence": round(confidence, 3),
        "routing_reason": routing_reason,
        "was_disambiguated": was_disambiguated,
        "confirmed_by_user": confirmed_by_user,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    try:
        with open(ROUTER_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision_record) + "\n")
    except Exception as e:
        print(f"[Router Log Warning] Could not persist decision: {e}")
    return decision_record

def get_router_audit_records(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves the recent router decision audit records."""
    if not os.path.exists(ROUTER_LOG_PATH):
        return []
    records = []
    try:
        with open(ROUTER_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line.strip()))
    except Exception:
        pass
    return records[-limit:]

def auto_detect_task_intent(
    prompt: str,
    file_path: Optional[str] = None,
    confirmed_intent: Optional[str] = None
) -> IntentRouteResult:
    """
    Intelligently analyzes the incoming prompt and optional attachment to determine
    the optimal task_type, routing rationale, confidence score, and model choice.

    If confidence is below DISAMBIGUATION_THRESHOLD (0.65) and no explicit confirmation
    is supplied, flags is_ambiguous=True and provides one-click selectable alternatives.
    """
    prompt_clean = (prompt or "").strip()
    prompt_lower = prompt_clean.lower()

    # If user explicitly confirmed an intent (e.g. from disambiguation button click)
    if confirmed_intent:
        c_intent = confirmed_intent.lower().strip()
        model_name = "qwen2.5vl:7b" if c_intent == "ocr" else ("qwen2.5-coder:3b" if c_intent == "code_exec" else "qwen2.5:3b")
        res = IntentRouteResult(
            task_type=c_intent,
            routing_reason=f"User-Confirmed Intent Selection: Routed to '{c_intent}'",
            model_name=model_name,
            confidence=1.0,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, c_intent, 1.0, res.routing_reason, was_disambiguated=True, confirmed_by_user=True)
        return res

    # 1. Image / PDF File Attachment -> High-confidence OCR Intent
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
            res = IntentRouteResult(
                task_type="ocr",
                routing_reason=f"Document/Image attached ({os.path.basename(file_path)}): Auto-routed to Vision OCR & Dynamic Document Intelligence",
                model_name="qwen2.5vl:7b",
                confidence=0.98,
                is_ambiguous=False
            )
            log_router_decision(prompt_clean, "ocr", 0.98, res.routing_reason)
            return res

    # Check for extremely short or ambiguous prompts (e.g. "report", "check", "check the pump", "analyze", "test")
    single_word_ambiguous = prompt_lower.strip() in [
        "report", "check", "run", "analyze", "test", "status", "data", "file", "document", "calculate", "summary", "help",
        "check the pump", "check pump", "inspect pump", "test system", "view status"
    ]
    is_very_short = (len(prompt_clean.split()) <= 3 and not re.search(r"\b[a-z]{2,4}-\d{2,4}[a-z]?\b|\b(sop|memo|docx|calculate|compute|rms|vibration|temp|iso|variance|integral|derivative)\b", prompt_lower))

    # 2. Check for Code Execution / Math / Computation Intent
    code_strong_pattern = r"\b(calculate|compute|solve|sum of|prime|primes|fibonacci|factorial|algorithm|numpy|pandas|derivative|integral|matrix multiplication|run python script|execute code|standard deviation|variance|mean of)\b"
    code_weak_pattern = r"\b(math|code|script|python|multiply|add|numbers|values)\b"

    code_match_strong = re.search(code_strong_pattern, prompt_lower)
    code_match_weak = re.search(code_weak_pattern, prompt_lower)

    # 3. Check for Word Document (.docx) / Executive Report / SOP Generation Intent
    doc_strong_pattern = r"\b(convert to word|make into a docx|turn into docx|export to word|export docx|generate word doc|draft sop|draft memo|compliance memo|executive memorandum|write sop|generate sop document|create docx document|formal compliance report|word file)\b"
    doc_weak_pattern = r"\b(word doc|docx|sop|memo|memorandum|formal report|draft document|template)\b"

    doc_match_strong = re.search(doc_strong_pattern, prompt_lower)
    doc_match_weak = re.search(doc_weak_pattern, prompt_lower)

    # 4. Check for Cross-Document / Historical Task Ledger Intent
    cross_strong_pattern = r"\b(across documents|cross doc|compare reports|compare previous|compare past|all tasks|historical tasks|database history|past \d+|last \d+|previous \d+|summarize recent|what happened in the last|plant anomalies ledger)\b"
    cross_weak_pattern = r"\b(latest|recent|records|history|historical|previous|earlier|events|ledger|inspections)\b"

    cross_match_strong = re.search(cross_strong_pattern, prompt_lower)
    cross_match_weak = re.search(cross_weak_pattern, prompt_lower)

    # 5. Check if prompt explicitly references a document file
    ocr_file_ref_match = re.search(r"\.(pdf|png|jpg|jpeg)\b", prompt_lower)

    # Score calculation
    if ocr_file_ref_match:
        res = IntentRouteResult(
            task_type="ocr",
            routing_reason="Document file extension reference detected in prompt: Auto-routed to OCR & Document Intelligence",
            model_name="qwen2.5vl:7b",
            confidence=0.92,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "ocr", 0.92, res.routing_reason)
        return res

    if doc_match_strong:
        res = IntentRouteResult(
            task_type="doc_gen",
            routing_reason="Strong Document Generation syntax detected: Auto-routed to Multi-Agent DocGen Pipeline",
            model_name="qwen2.5:3b",
            confidence=0.95,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "doc_gen", 0.95, res.routing_reason)
        return res

    if code_match_strong:
        res = IntentRouteResult(
            task_type="code_exec",
            routing_reason="Strong Mathematical / Computational syntax detected: Auto-routed to Python Sandbox Code Engine",
            model_name="qwen2.5-coder:3b",
            confidence=0.94,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "code_exec", 0.94, res.routing_reason)
        return res

    if cross_match_strong:
        res = IntentRouteResult(
            task_type="cross_doc_query",
            routing_reason="Strong Historical Cross-Document syntax detected: Auto-routed to Cross-Doc Synthesis Engine",
            model_name="qwen2.5:3b",
            confidence=0.93,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "cross_doc_query", 0.93, res.routing_reason)
        return res

    # Ambiguity check for short/weak prompts
    if single_word_ambiguous or is_very_short:
        confidence = 0.45
        suggested_options = [
            {"task_type": "doc_gen", "label": "Draft Compliance Memo / SOP (.docx)", "description": "Draft formal Word memorandum with rule engine checks", "model_name": "qwen2.5:3b"},
            {"task_type": "cross_doc_query", "label": "Query Historical Ledger", "description": "Search across recent inspection records and past anomalies", "model_name": "qwen2.5:3b"},
            {"task_type": "code_exec", "label": "Run Python Calculation", "description": "Perform numerical RMS computation or data analysis in sandbox", "model_name": "qwen2.5-coder:3b"},
            {"task_type": "text_gen", "label": "General Agent QA & Reasoning", "description": "Ask engineering questions or get operational recommendations", "model_name": "qwen2.5:3b"}
        ]
        res = IntentRouteResult(
            task_type="disambiguation",
            routing_reason=f"Ambiguous query (confidence {confidence:.2f} < {DISAMBIGUATION_THRESHOLD}): Disambiguation required",
            model_name="qwen2.5:3b",
            confidence=confidence,
            is_ambiguous=True,
            suggested_options=suggested_options
        )
        log_router_decision(prompt_clean, "disambiguation", confidence, res.routing_reason, was_disambiguated=True)
        return res

    # Moderately confident matches
    if doc_match_weak:
        res = IntentRouteResult(
            task_type="doc_gen",
            routing_reason="Document drafting keywords detected: Routed to DocGen Engine",
            model_name="qwen2.5:3b",
            confidence=0.78,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "doc_gen", 0.78, res.routing_reason)
        return res

    if code_match_weak:
        res = IntentRouteResult(
            task_type="code_exec",
            routing_reason="Computational / code keywords detected: Routed to Python Sandbox Engine",
            model_name="qwen2.5-coder:3b",
            confidence=0.75,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "code_exec", 0.75, res.routing_reason)
        return res

    if cross_match_weak:
        res = IntentRouteResult(
            task_type="cross_doc_query",
            routing_reason="Historical / ledger keywords detected: Routed to Cross-Doc Query Engine",
            model_name="qwen2.5:3b",
            confidence=0.72,
            is_ambiguous=False
        )
        log_router_decision(prompt_clean, "cross_doc_query", 0.72, res.routing_reason)
        return res

    # Default to General Text Synthesis with standard confidence
    res = IntentRouteResult(
        task_type="text_gen",
        routing_reason="Autonomous Reasoning: Routed to High-Throughput Agent Reasoning Engine",
        model_name="qwen2.5:3b",
        confidence=0.80,
        is_ambiguous=False
    )
    log_router_decision(prompt_clean, "text_gen", 0.80, res.routing_reason)
    return res

def route_task(task_type: str, input_ref: str) -> ModelChoice:
    """Synchronous fallback routing mapping task types to default model choices."""
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
            model_name="qwen2.5:3b",
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
