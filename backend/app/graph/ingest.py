import os
import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models import EquipmentNode, EquipmentEvent

def infer_equipment_type(equipment_id: str, context: str = "") -> str:
    eq_upper = (equipment_id or "").upper()
    ctx_lower = (context or "").lower()

    if eq_upper.startswith("TRB") or "turbine" in ctx_lower:
        return "turbine"
    elif eq_upper.startswith("PMP") or "pump" in ctx_lower:
        return "pump"
    elif eq_upper.startswith("VLV") or "valve" in ctx_lower:
        return "valve"
    elif eq_upper.startswith("CMP") or "compressor" in ctx_lower:
        return "compressor"
    elif eq_upper.startswith("TNK") or eq_upper.startswith("TK") or "tank" in ctx_lower:
        return "tank"
    elif eq_upper.startswith("HEX") or eq_upper.startswith("EXC") or "exchanger" in ctx_lower:
        return "exchanger"
    return "equipment"

def infer_unit(equipment_id: str, data: Dict[str, Any]) -> str:
    # 1. Direct field
    if data.get("unit"):
        return str(data["unit"]).strip().upper()
    if data.get("plant_unit"):
        return str(data["plant_unit"]).strip().upper()
    if isinstance(data.get("metadata"), dict) and data["metadata"].get("unit"):
        return str(data["metadata"]["unit"]).strip().upper()

    # 2. Text scanning
    combined_text = (
        str(data.get("document_title", "")) + " " +
        str(data.get("findings", "")) + " " +
        str(data.get("findings_and_summary", "")) + " " +
        str(data.get("notes", ""))
    ).upper()

    for unit_code in ["HCU", "CDU", "VGO", "FCCU", "DHDS", "OM&S", "SRU", "CCR"]:
        if re.search(rf'\b{unit_code}\b', combined_text):
            return unit_code

    return "HCU"  # Default refinery unit for MRPL

def parse_event_date(data: Dict[str, Any]) -> datetime:
    raw_date = (
        data.get("inspection_date") or
        data.get("date") or
        (data.get("metadata") and isinstance(data["metadata"], dict) and data["metadata"].get("date")) or
        (data.get("metadata") and isinstance(data["metadata"], dict) and data["metadata"].get("inspection_date"))
    )

    if raw_date:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(str(raw_date).strip(), fmt)
            except Exception:
                pass

    return datetime.utcnow()

async def record_equipment_event(
    task_id: Optional[UUID],
    structured_data: Dict[str, Any],
    event_type: str = "inspection",
    fallback_equipment_id: Optional[str] = None
) -> Optional[EquipmentNode]:
    """
    Auto-creates or updates EquipmentNode and logs an EquipmentEvent row
    from completed task extractions or doc_gen pipelines.
    """
    if not isinstance(structured_data, dict):
        return None

    # 1. Resolve Equipment ID
    eq_id = (
        structured_data.get("equipment_id") or
        (isinstance(structured_data.get("metadata"), dict) and structured_data["metadata"].get("equipment_id")) or
        fallback_equipment_id
    )

    if not eq_id:
        # Try extracting from text fields
        text_blob = (
            str(structured_data.get("document_title", "")) + " " +
            str(structured_data.get("findings", "")) + " " +
            str(structured_data.get("task_prompt", ""))
        )
        match = re.search(r'\b([A-Z]{3,4}-\d{3,5}[A-Z]?)\b', text_blob)
        if match:
            eq_id = match.group(1)

    if not eq_id or str(eq_id).strip().lower() in ["null", "none", "unknown", ""]:
        return None

    eq_id = str(eq_id).strip().upper()
    eq_type = structured_data.get("equipment_type") or infer_equipment_type(eq_id, str(structured_data))
    unit = infer_unit(eq_id, structured_data)
    eq_name = structured_data.get("equipment_name") or f"{eq_type.capitalize()} {eq_id}"
    event_dt = parse_event_date(structured_data)

    async with AsyncSessionLocal() as db:
        # Check existing EquipmentNode
        res = await db.execute(select(EquipmentNode).where(EquipmentNode.equipment_id == eq_id))
        node = res.scalars().first()

        if not node:
            node = EquipmentNode(
                id=uuid.uuid4(),
                equipment_id=eq_id,
                equipment_name=eq_name,
                unit=unit,
                equipment_type=eq_type,
                created_at=datetime.utcnow()
            )
            db.add(node)
            await db.flush()
        else:
            # Update fields if new info available
            if eq_name and eq_name != node.equipment_name:
                node.equipment_name = eq_name
            if unit and (not node.unit or node.unit == "Unit-1"):
                node.unit = unit
            if eq_type and (not node.equipment_type or node.equipment_type == "equipment"):
                node.equipment_type = eq_type
            node.updated_at = datetime.utcnow()

        valid_task_id = None
        if task_id:
            from app.models import Task
            task_res = await db.execute(select(Task.id).where(Task.id == task_id))
            if task_res.scalar():
                valid_task_id = task_id

        # Create EquipmentEvent
        event = EquipmentEvent(
            id=uuid.uuid4(),
            equipment_node_id=node.id,
            source_task_id=valid_task_id,
            event_type=event_type,
            event_data=structured_data,
            event_date=event_dt,
            created_at=datetime.utcnow()
        )
        db.add(event)
        await db.commit()
        await db.refresh(node)
        return node
