from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.graph.query import get_equipment_history, query_equipment_by_criteria, list_all_equipment
from app.graph.trends import analyze_trend

router = APIRouter(prefix="/graph", tags=["equipment_graph"])

class GraphQueryRequest(BaseModel):
    unit: Optional[str] = None
    event_type: Optional[str] = None
    compliance_status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    trending_toward_violation: Optional[bool] = None

@router.get("/equipment")
async def get_all_equipment():
    """
    List all registered equipment nodes in the Sovereign Equipment Knowledge Graph.
    """
    return await list_all_equipment()

@router.get("/equipment/{equipment_id}")
async def get_equipment_detail(equipment_id: str):
    """
    Retrieve full historical timeline and inspection events for a specific equipment ID.
    """
    history = await get_equipment_history(equipment_id)
    if not history:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_id}' not found in knowledge graph")
    return history

@router.get("/equipment/{equipment_id}/trend")
async def get_equipment_trend(
    equipment_id: str,
    field: str = Query("vibration_rms_mms", description="Parameter field to compute linear regression over"),
    horizon_days: int = Query(90, description="Horizon horizon in days to project threshold breach")
):
    """
    Predictive deterministic trend analysis (numpy linear regression) for equipment measurements.
    Computes slope per day, days to threshold breach, and projected trajectory.
    """
    trend_result = await analyze_trend(equipment_id=equipment_id, field=field, horizon_days=horizon_days)
    if trend_result.get("error") and "not found" in trend_result["error"].lower():
        raise HTTPException(status_code=404, detail=trend_result["error"])
    return trend_result

@router.post("/query")
async def query_equipment_graph(req: GraphQueryRequest):
    """
    Structured query over equipment events (e.g. all equipment in HCU with non-compliant findings,
    or equipment proactively trending toward threshold violations).
    """
    date_range = None
    if req.start_date or req.end_date:
        date_range = {"start_date": req.start_date, "end_date": req.end_date}

    results = await query_equipment_by_criteria(
        unit=req.unit,
        event_type=req.event_type,
        compliance_status=req.compliance_status,
        date_range=date_range,
        trending_toward_violation=req.trending_toward_violation
    )
    return {
        "query": req.model_dump(),
        "total_equipment_matched": len(results),
        "results": results
    }
