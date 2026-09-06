import re
import httpx
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"

class ModelCategory(str, Enum):
    VISION = "vision"
    FAST_INFERENCE = "fast_inference"
    CODING = "coding"
    REASONING = "reasoning"
    GENERAL = "general"

@dataclass
class ModelRouteDecision:
    model_name: str
    category: str
    reason: str
    timeout_seconds: float
    is_fallback: bool = False
    available_candidates: List[str] = None

# Priority tiers for each capability category
CAPABILITY_PRIORITY_TIERS: Dict[ModelCategory, List[str]] = {
    ModelCategory.VISION: [
        "qwen2.5vl:7b",
        "qwen2.5vl",
        "llama3.2-vision:11b",
        "llava:7b",
        "llava"
    ],
    ModelCategory.FAST_INFERENCE: [
        "qwen2.5:3b",
        "llama3.2:3b",
        "qwen2.5:1.5b",
        "phi3:mini",
        "qwen2.5:7b-instruct",
        "qwen2.5:latest"
    ],
    ModelCategory.CODING: [
        "qwen2.5:3b",
        "qwen2.5-coder:3b",
        "qwen2.5-coder:7b",
        "qwen2.5-coder:1.5b",
        "qwen2.5:7b-instruct"
    ],
    ModelCategory.REASONING: [
        "qwen2.5:3b",
        "qwen2.5:7b-instruct",
        "deepseek-r1:1.5b",
        "deepseek-r1:7b"
    ],
    ModelCategory.GENERAL: [
        "qwen2.5:3b",
        "qwen2.5:7b-instruct",
        "llama3.1:8b",
        "mistral:7b",
        "qwen2.5:latest"
    ]
}

# Cache installed models briefly to prevent redundant HTTP probes on rapid bursts
_installed_models_cache: List[str] = []
_cache_timestamp: float = 0.0

async def get_installed_models(force_refresh: bool = False) -> List[str]:
    """Query local Ollama server for currently installed and ready models."""
    global _installed_models_cache, _cache_timestamp
    import time
    now = time.time()
    if not force_refresh and _installed_models_cache and (now - _cache_timestamp < 10.0):
        return list(_installed_models_cache)

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(OLLAMA_TAGS_URL)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                _installed_models_cache = models
                _cache_timestamp = now
                return models
    except Exception:
        pass

    return list(_installed_models_cache) or ["qwen2.5:7b-instruct", "qwen2.5vl:7b"]

def detect_category(task_type: str, prompt: str = "", is_vision: bool = False, category_hint: Optional[str] = None) -> ModelCategory:
    """Analyze prompt semantics and task context to select target capability category."""
    if category_hint:
        try:
            return ModelCategory(category_hint.lower())
        except ValueError:
            pass

    if is_vision or str(task_type).lower() in ["ocr", "vision", "multimodal"]:
        return ModelCategory.VISION

    text_lower = (prompt or "").lower()
    task_lower = (task_type or "").lower()

    # Code execution / Python script generation / calculation
    if (
        task_lower == "code_exec"
        or any(k in text_lower for k in ["python", "script", "function", "def ", "class ", "import ", "sql", "regex", "calculate", "algorithm", "code "])
    ):
        return ModelCategory.CODING

    # Deep reasoning / logic puzzles / proof / chain-of-thought
    if any(k in text_lower for k in ["step by step", "reasoning", "prove", "logic", "why did", "root cause", "deduce", "evaluate tradeoff"]):
        return ModelCategory.REASONING

    # Fast short Q&A or quick lookup / status check
    if (
        len(prompt.split()) < 20
        or task_lower == "cross_doc_query"
        or any(k in text_lower for k in ["status", "is any", "quick", "check", "summary", "list", "who is", "what is"])
    ):
        return ModelCategory.FAST_INFERENCE

    # Document generation / long reports / default general
    return ModelCategory.GENERAL

async def route_model(
    task_type: str,
    prompt: str = "",
    is_vision: bool = False,
    category_hint: Optional[str] = None
) -> ModelRouteDecision:
    """
    Intelligent Model Router / Dynamic Switcher:
    1. Analyzes the incoming task and intent to pick the optimal ModelCategory.
    2. Probes local Ollama instance for currently installed models.
    3. Selects the highest-priority installed model for that category.
    4. Automatically falls back to available models if top choice is uninstalled.
    5. Assigns adaptive timeouts based on model parameter scale.
    """
    category = detect_category(task_type=task_type, prompt=prompt, is_vision=is_vision, category_hint=category_hint)
    installed_models = await get_installed_models()

    candidate_list = CAPABILITY_PRIORITY_TIERS.get(category, CAPABILITY_PRIORITY_TIERS[ModelCategory.GENERAL])

    selected_model: Optional[str] = None
    is_fallback = False

    # Check for direct match or prefix match (e.g. qwen2.5:3b matching qwen2.5:3b-instruct-q4_K_M)
    for cand in candidate_list:
        cand_base = cand.split(":")[0].lower()
        cand_tag = cand.lower()

        # Exact match
        for inst in installed_models:
            inst_lower = inst.lower()
            if inst_lower == cand_tag or inst_lower.startswith(cand_tag):
                selected_model = inst
                break
        if selected_model:
            break

        # Base name match
        for inst in installed_models:
            inst_base = inst.split(":")[0].lower()
            if inst_base == cand_base:
                selected_model = inst
                break
        if selected_model:
            break

    # If no preferred model found in target category, fall back to any installed model
    if not selected_model:
        is_fallback = True
        if is_vision or category == ModelCategory.VISION:
            # Pick any vision model if possible
            vision_candidates = [m for m in installed_models if "vl" in m.lower() or "vision" in m.lower()]
            selected_model = vision_candidates[0] if vision_candidates else (installed_models[0] if installed_models else "qwen2.5vl:7b")
        else:
            # Pick any text model
            text_candidates = [m for m in installed_models if "vl" not in m.lower() and "vision" not in m.lower()]
            selected_model = text_candidates[0] if text_candidates else (installed_models[0] if installed_models else "qwen2.5:7b-instruct")

    # Dynamic timeout assignment based on model scale & vision
    if category == ModelCategory.VISION or "vl" in selected_model.lower() or "vision" in selected_model.lower():
        timeout_sec = 300.0
    elif any(tag in selected_model for tag in [":1.5b", ":3b", "3b", "1.5b"]):
        timeout_sec = 120.0
    else:
        timeout_sec = 240.0

    # Human-readable rationale
    reason_map = {
        ModelCategory.VISION: f"Switched to multimodal vision model '{selected_model}' for image/document OCR processing",
        ModelCategory.FAST_INFERENCE: f"Switched to low-latency model '{selected_model}' for rapid inference & high throughput",
        ModelCategory.CODING: f"Switched to coding-specialized model '{selected_model}' for Python script generation & calculations",
        ModelCategory.REASONING: f"Switched to deep reasoning model '{selected_model}' for structured logical deduction",
        ModelCategory.GENERAL: f"Switched to standard intelligence model '{selected_model}' for comprehensive synthesis"
    }

    reason = reason_map.get(category, f"Routed to '{selected_model}'")
    if is_fallback:
        reason += f" (Fallback: preferred {category.value} models not found locally)"

    return ModelRouteDecision(
        model_name=selected_model,
        category=category.value,
        reason=reason,
        timeout_seconds=timeout_sec,
        is_fallback=is_fallback,
        available_candidates=installed_models
    )

UNCERTAINTY_PATTERNS = [
    r"\bi am not sure\b",
    r"\bi'm not sure\b",
    r"\bit is unclear\b",
    r"\bit's unclear\b",
    r"\binsufficient information\b",
    r"\bcannot determine\b",
    r"\bnot enough data\b",
    r"\buncertain\b"
]

async def generate_with_escalation(
    prompt: str,
    system: str = "",
    min_length: int = 80,
    fast_model: str = "qwen2.5:3b",
    primary_model: str = "qwen2.5:7b-instruct",
    timeout_fast: float = 60.0,
    timeout_primary: float = 180.0
) -> tuple[str, Optional[Dict[str, Any]]]:
    """
    Confidence-Based Model Escalation:
    1. Attempts generation with fast low-latency model (e.g. qwen2.5:3b).
    2. Inspects response for brevity (< min_length) or hedging uncertainty.
    3. If uncertain or too brief, automatically escalates to primary 7B model.
    """
    from app.models.ollama_client import generate_text

    installed = await get_installed_models()
    fast_target = next((m for m in installed if fast_model.lower() in m.lower()), None)
    primary_target = next((m for m in installed if primary_model.lower() in m.lower()), primary_model)

    if not fast_target or fast_target == primary_target:
        output = await generate_text(prompt=prompt, system=system, model=primary_target, timeout_seconds=timeout_primary)
        return output, None

    # 1. Fast attempt
    try:
        fast_output = await generate_text(prompt=prompt, system=system, model=fast_target, timeout_seconds=timeout_fast)
    except Exception:
        fast_output = ""

    # 2. Check heuristics
    escalate_reason = None
    if not fast_output or len(fast_output.strip()) < min_length:
        escalate_reason = f"Response length ({len(fast_output.strip())} chars) below threshold of {min_length} chars"
    else:
        text_lower = fast_output.lower()
        for pat in UNCERTAINTY_PATTERNS:
            if re.search(pat, text_lower):
                escalate_reason = f"Fast model expressed hedging/uncertainty matching '{pat}'"
                break

    if escalate_reason:
        primary_output = await generate_text(prompt=prompt, system=system, model=primary_target, timeout_seconds=timeout_primary)
        return primary_output, {
            "escalated": True,
            "fast_model": fast_target,
            "primary_model": primary_target,
            "reason": escalate_reason,
            "fast_preview": fast_output[:120] if fast_output else "(empty)"
        }

    return fast_output, {
        "escalated": False,
        "fast_model": fast_target,
        "primary_model": primary_target,
        "reason": "Fast model response met quality threshold without uncertainty"
    }
