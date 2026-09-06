import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.future import select
from sqlalchemy import desc, func
from app.database import AsyncSessionLocal
from app.models import EquipmentNode, EquipmentEvent, Task

async def get_equipment_history(equipment_id: str) -> Optional[Dict[str, Any]]:
    """
    Returns full chronological event history for a single equipment node.
    """
    if not equipment_id:
        return None

    eq_clean = equipment_id.strip().upper()

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(EquipmentNode).where(func.upper(EquipmentNode.equipment_id) == eq_clean)
        )
        node = res.scalars().first()
        if not node:
            return None

        events_res = await db.execute(
            select(EquipmentEvent)
            .where(EquipmentEvent.equipment_node_id == node.id)
            .order_by(desc(EquipmentEvent.event_date), desc(EquipmentEvent.created_at))
        )
        events = events_res.scalars().all()

        formatted_events = []
        for ev in events:
            formatted_events.append({
                "id": str(ev.id),
                "event_type": ev.event_type,
                "event_date": ev.event_date.strftime("%Y-%m-%d") if ev.event_date else (ev.created_at.strftime("%Y-%m-%d") if ev.created_at else None),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
                "source_task_id": str(ev.source_task_id) if ev.source_task_id else None,
                "event_data": ev.event_data
            })

        return {
            "id": str(node.id),
            "equipment_id": node.equipment_id,
            "equipment_name": node.equipment_name,
            "unit": node.unit,
            "equipment_type": node.equipment_type,
            "created_at": node.created_at.isoformat() if node.created_at else None,
            "updated_at": node.updated_at.isoformat() if node.updated_at else None,
            "events_count": len(formatted_events),
            "events": formatted_events
        }

async def query_equipment_by_criteria(
    unit: Optional[str] = None,
    event_type: Optional[str] = None,
    compliance_status: Optional[str] = None,
    date_range: Optional[Dict[str, str]] = None,
    trending_toward_violation: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """
    Filter equipment nodes and their events by unit, event type, date range,
    compliance status inside the JSONB event_data, and proactive predictive trend projection.
    """
    async with AsyncSessionLocal() as db:
        # Load all nodes with optional unit filtering
        node_query = select(EquipmentNode)
        if unit and unit.strip().upper() not in ["ALL", ""]:
            node_query = node_query.where(func.upper(EquipmentNode.unit) == unit.strip().upper())

        nodes_res = await db.execute(node_query.order_by(EquipmentNode.equipment_id))
        nodes = nodes_res.scalars().all()

        results = []

        for node in nodes:
            ev_query = (
                select(EquipmentEvent)
                .where(EquipmentEvent.equipment_node_id == node.id)
                .order_by(desc(EquipmentEvent.event_date), desc(EquipmentEvent.created_at))
            )

            if event_type and event_type.strip().lower() not in ["all", ""]:
                ev_query = ev_query.where(func.lower(EquipmentEvent.event_type) == event_type.strip().lower())

            events_res = await db.execute(ev_query)
            events = events_res.scalars().all()

            # Filter events by compliance_status inside event_data if specified
            filtered_events = []
            for ev in events:
                data = ev.event_data if isinstance(ev.event_data, dict) else {}
                
                # Check compliance status
                if compliance_status and compliance_status.strip().upper() not in ["ALL", ""]:
                    req_status = compliance_status.strip().upper()
                    ev_status = str(data.get("status") or data.get("compliance_status") or "").upper()
                    findings = str(data.get("findings") or data.get("findings_and_summary") or "").upper()
                    
                    status_match = False
                    if req_status in ["NON_COMPLIANT", "NON-COMPLIANT", "FAIL", "FAILED", "WARNING", "ANOMALY"]:
                        status_match = any(w in ev_status for w in ["NON_COMPLIANT", "NON-COMPLIANT", "WARNING", "FAIL", "ANOMALY", "ALERT"]) or \
                                       any(w in findings for w in ["NON_COMPLIANT", "NON-COMPLIANT", "ZONE C", "ZONE D", "UNACCEPTABLE", "EXCEEDED", "ANOMALY"])
                    elif req_status in ["COMPLIANT", "PASS", "PASSED", "OK"]:
                        status_match = ("COMPLIANT" in ev_status and "NON" not in ev_status) or \
                                       ("PASSED" in ev_status or "ZONE A" in findings or "NORMAL" in findings)
                    else:
                        status_match = req_status in ev_status or req_status in findings

                    if not status_match:
                        continue

                filtered_events.append({
                    "id": str(ev.id),
                    "event_type": ev.event_type,
                    "event_date": ev.event_date.strftime("%Y-%m-%d") if ev.event_date else (ev.created_at.strftime("%Y-%m-%d") if ev.created_at else None),
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    "source_task_id": str(ev.source_task_id) if ev.source_task_id else None,
                    "event_data": data
                })

            if filtered_events or (not compliance_status and not event_type):
                # Check predictive trend filter if requested
                trend_data = None
                if trending_toward_violation is not None:
                    from app.graph.trends import analyze_trend
                    trend_data = await analyze_trend(equipment_id=node.equipment_id)
                    is_trending = trend_data.get("trending", False)
                    if trending_toward_violation is True and not is_trending:
                        continue
                    if trending_toward_violation is False and is_trending:
                        continue
                else:
                    # Opportunistically run lightweight trend check for display
                    try:
                        from app.graph.trends import analyze_trend
                        trend_data = await analyze_trend(equipment_id=node.equipment_id)
                    except Exception:
                        trend_data = None

                results.append({
                    "id": str(node.id),
                    "equipment_id": node.equipment_id,
                    "equipment_name": node.equipment_name,
                    "unit": node.unit,
                    "equipment_type": node.equipment_type,
                    "created_at": node.created_at.isoformat() if node.created_at else None,
                    "matching_events_count": len(filtered_events),
                    "events": filtered_events,
                    "trend_analysis": trend_data
                })

        return results

async def list_all_equipment() -> List[Dict[str, Any]]:
    """
    Returns list of all registered equipment nodes with summary metrics.
    """
    async with AsyncSessionLocal() as db:
        nodes_res = await db.execute(select(EquipmentNode).order_by(EquipmentNode.equipment_id))
        nodes = nodes_res.scalars().all()

        out = []
        for node in nodes:
            events_count_res = await db.execute(
                select(func.count(EquipmentEvent.id)).where(EquipmentEvent.equipment_node_id == node.id)
            )
            count = events_count_res.scalar() or 0

            latest_event_res = await db.execute(
                select(EquipmentEvent)
                .where(EquipmentEvent.equipment_node_id == node.id)
                .order_by(desc(EquipmentEvent.event_date), desc(EquipmentEvent.created_at))
                .limit(1)
            )
            latest_ev = latest_event_res.scalars().first()

            out.append({
                "id": str(node.id),
                "equipment_id": node.equipment_id,
                "equipment_name": node.equipment_name,
                "unit": node.unit,
                "equipment_type": node.equipment_type,
                "events_count": count,
                "latest_event_date": latest_ev.event_date.strftime("%Y-%m-%d") if (latest_ev and latest_ev.event_date) else None,
                "latest_event_type": latest_ev.event_type if latest_ev else None,
                "latest_status": (latest_ev.event_data.get("status") or latest_ev.event_data.get("compliance_status")) if (latest_ev and isinstance(latest_ev.event_data, dict)) else None
            })

        return out
