from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.future import select
from sqlalchemy import desc, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MemoryEntry
from app.memory.retrieve import search_memory, get_memory_history, compute_strength

router = APIRouter(prefix="/memory", tags=["memory"])

class MemorySearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class MemorySearchResponse(BaseModel):
    query: str
    count: int
    results: List[Dict[str, Any]]

@router.get("/")
async def list_memories(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """
    Returns recent long-term memory entries and distinct known entity keys.
    """
    entries_res = await db.execute(
        select(MemoryEntry).order_by(desc(MemoryEntry.created_at)).limit(limit)
    )
    entries = entries_res.scalars().all()

    distinct_entities_res = await db.execute(
        select(distinct(MemoryEntry.entity_key))
    )
    distinct_keys = distinct_entities_res.scalars().all()

    formatted = []
    for e in entries:
        formatted.append({
            "id": str(e.id),
            "entity_key": e.entity_key,
            "summary_text": e.summary_text,
            "strength_score": e.strength_score,
            "computed_strength": round(compute_strength(e), 3),
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "last_accessed_at": e.last_accessed_at.isoformat() if e.last_accessed_at else None,
            "access_count": e.access_count,
            "superseded_by": str(e.superseded_by) if e.superseded_by else None,
            "is_current": e.superseded_by is None,
            "source_task_id": str(e.source_task_id) if e.source_task_id else None
        })

    return {
        "distinct_entities": sorted(list(distinct_keys)),
        "total_records": len(formatted),
        "memories": formatted
    }

@router.post("/search", response_model=MemorySearchResponse)
async def search_memory_endpoint(req: MemorySearchRequest):
    """
    Searches structured long-term memory, re-ranking by semantic similarity and decayed strength,
    and returning linked historical context with explainability metadata.
    """
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        results = await search_memory(query=req.query, top_k=req.top_k or 5)
        return MemorySearchResponse(
            query=req.query,
            count=len(results),
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memory layer: {str(e)}")

@router.get("/{entity_key:path}")
async def get_entity_memory_history(entity_key: str):
    """
    Returns the complete chronological memory evolution chain for a specific entity
    (e.g., equipment_id:PMP-7001 or equipment_id:TRB-1105).
    """
    if not entity_key or not entity_key.strip():
        raise HTTPException(status_code=400, detail="Entity key cannot be empty")

    history = await get_memory_history(entity_key=entity_key.strip())
    if history["total_memories"] == 0:
        raise HTTPException(status_code=404, detail=f"No long-term memories found for entity key '{entity_key}'")

    return history
