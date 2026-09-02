import httpx
from fastapi import APIRouter
from sqlalchemy import text
from app.database import engine
from app.models.ollama_client import OLLAMA_BASE_URL

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
@router.get("/")
async def health_check():
    """
    Health check endpoint verifying both Database connectivity and Local Ollama availability.
    """
    # 1. Check Database
    db_status = "unreachable"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "unreachable"

    # 2. Check Ollama Local Service
    ollama_status = "unreachable"
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                ollama_status = "connected"
                data = res.json()
                ollama_models = [m.get("name") for m in data.get("models", [])]
    except Exception:
        ollama_status = "unreachable"

    # 3. Model Router Status
    from app.router.model_router import get_installed_models, CAPABILITY_PRIORITY_TIERS
    installed_models = await get_installed_models()

    overall_status = "ok" if (db_status == "connected" and ollama_status == "connected") else "degraded"

    return {
        "status": overall_status,
        "db": db_status,
        "ollama_status": ollama_status,
        "ollama_models": ollama_models,
        "router_ready": bool(installed_models),
        "active_models_count": len(installed_models)
    }

@router.get("/models")
async def get_model_router_status():
    """
    Returns the dynamic model switcher capabilities, installed models, and routing matrix.
    """
    from app.router.model_router import get_installed_models, CAPABILITY_PRIORITY_TIERS
    installed = await get_installed_models(force_refresh=True)

    matrix = {}
    for category, priorities in CAPABILITY_PRIORITY_TIERS.items():
        matched = [p for p in priorities if any(p.split(":")[0].lower() in m.lower() for m in installed)]
        matrix[category.value] = {
            "preferred_models": priorities,
            "installed_matches": matched,
            "active_model": matched[0] if matched else (installed[0] if installed else "none")
        }

    return {
        "installed_models": installed,
        "routing_matrix": matrix,
        "air_gapped": True
    }
