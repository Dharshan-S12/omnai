import os
import math
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from sqlalchemy.future import select
from sqlalchemy import or_, and_, desc
from app.database import AsyncSessionLocal
from app.models import MemoryEntry, MemoryLink
from app.rag.client import get_embedding_function
from app.memory.client import get_memory_collection

# Named tuning parameters
DEDUP_SIMILARITY_THRESHOLD = 0.92
DECAY_HALF_LIFE_DAYS = 30.0

def cosine_similarity(vec1: Any, vec2: Any) -> float:
    """Calculates cosine similarity between two numeric vectors or numpy arrays."""
    if vec1 is None or vec2 is None:
        return 0.0
    v1 = list(vec1) if not isinstance(vec1, list) else vec1
    v2 = list(vec2) if not isinstance(vec2, list) else vec2
    if len(v1) == 0 or len(v2) == 0 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return float(dot_product / (norm1 * norm2))

def extract_entities(structured_output: Dict[str, Any], doc_type: str = "") -> Dict[str, Any]:
    """
    Extracts primary entity key (e.g. equipment_id:TRB-1105) and secondary entity
    attributes (inspector, sop_reference, date, measurements, status) from task structured output.
    """
    if not isinstance(structured_output, dict):
        return {
            "entity_key": f"doc_type:{doc_type or 'general'}",
            "secondary_keys": {},
            "raw_summary": str(structured_output)[:200]
        }

    metadata = structured_output.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    # Helper to check keys across metadata and top-level
    def find_field(keys: List[str]) -> Optional[str]:
        for k in keys:
            for source in [metadata, structured_output]:
                for candidate_key, val in source.items():
                    if str(candidate_key).strip().lower() == k.lower() and val:
                        val_str = str(val).strip()
                        if val_str and val_str.lower() not in ["none", "null", "n/a"]:
                            return val_str
        return None

    # 1. Primary Entity Extraction (Equipment Tag ID, Doc ID, Vendor, etc.)
    equipment_id = find_field([
        "equipment_id", "equipment tag id", "equipment tag", "equipment id",
        "tag id", "equipment", "pump id", "turbine id", "machine id", "asset id"
    ])
    
    doc_id = find_field([
        "doc_id", "document_id", "document reference", "doc reference",
        "report reference", "report id", "invoice #", "invoice no", "po #", "sop number"
    ])

    vendor_name = find_field([
        "vendor_name", "vendor", "supplier", "contractor", "manufacturer"
    ])

    if equipment_id:
        normalized_id = equipment_id.replace(" ", "").upper()
        entity_key = f"equipment_id:{normalized_id}"
    elif doc_id:
        normalized_id = doc_id.replace(" ", "").upper()
        entity_key = f"doc_id:{normalized_id}"
    elif vendor_name:
        entity_key = f"vendor_name:{vendor_name.strip()}"
    elif doc_type:
        entity_key = f"doc_type:{doc_type.strip()}"
    else:
        entity_key = "entity:general"

    # 2. Secondary Entities & Metadata Extraction
    sop_reference = find_field([
        "standard applied", "sop reference", "standard", "sop id", "sop", "reference standard"
    ])
    inspector = find_field([
        "inspector", "technician", "lead reliability engineer", "engineer", "auditor", "operator"
    ])
    inspection_date = find_field([
        "date of inspection", "inspection date", "date", "report date"
    ])

    # Extract measurements & findings
    measurements = structured_output.get("measurements", {})
    if not isinstance(measurements, dict):
        measurements = {}

    findings = structured_output.get("findings", "")
    compliance_status = structured_output.get("compliance_status", "")

    return {
        "entity_key": entity_key,
        "equipment_id": equipment_id,
        "secondary_keys": {
            "sop_reference": sop_reference,
            "inspector": inspector,
            "inspection_date": inspection_date,
        },
        "measurements": measurements,
        "findings": findings,
        "compliance_status": compliance_status
    }

def generate_summary_text(structured_output: Dict[str, Any], doc_type: str = "") -> str:
    """
    Generates a concise, high-information factual summary text (1-2 sentences)
    suitable for dense semantic embedding and deduplication comparison.
    """
    if not isinstance(structured_output, dict):
        return str(structured_output).strip()[:300]

    extracted = extract_entities(structured_output, doc_type)
    entity_key = extracted["entity_key"]
    sec = extracted["secondary_keys"]
    measurements = extracted["measurements"]
    findings = extracted["findings"]
    compliance = extracted["compliance_status"]

    doc_title = structured_output.get("document_title") or doc_type or "Inspection Report"
    
    parts = []
    # Main identification
    id_part = f"{doc_title} for {entity_key}"
    if sec.get("inspection_date"):
        id_part += f" on {sec['inspection_date']}"
    if sec.get("inspector"):
        id_part += f" (Inspector: {sec['inspector']})"
    parts.append(id_part + ".")

    # Measurements
    if measurements:
        meas_items = [f"{k}: {v}" for k, v in measurements.items() if v]
        if meas_items:
            parts.append(f"Recorded measurements: {', '.join(meas_items)}.")

    # Compliance & Findings
    if compliance:
        parts.append(f"Status: {compliance}.")
    if findings:
        clean_findings = str(findings).strip().replace("\n", " ")
        if len(clean_findings) > 160:
            clean_findings = clean_findings[:157] + "..."
        parts.append(f"Findings: {clean_findings}")

    summary = " ".join(parts).strip()
    return summary if summary else f"Structured record for {entity_key} (Type: {doc_type})"

def has_fact_evolution(summary1: str, summary2: str, struct1: Dict[str, Any], struct2: Dict[str, Any]) -> bool:
    """
    Determines if two records for the same entity represent an EVOLUTION (e.g. changing measurement values,
    different inspection dates, altered status) versus an identical near-duplicate.
    """
    if summary1.strip() == summary2.strip():
        return False

    # Check measurement differences
    m1 = struct1.get("measurements", {}) if isinstance(struct1, dict) else {}
    m2 = struct2.get("measurements", {}) if isinstance(struct2, dict) else {}
    if m1 and m2 and m1 != m2:
        return True

    # Check date differences
    e1 = extract_entities(struct1) if isinstance(struct1, dict) else {}
    e2 = extract_entities(struct2) if isinstance(struct2, dict) else {}
    d1 = e1.get("secondary_keys", {}).get("inspection_date")
    d2 = e2.get("secondary_keys", {}).get("inspection_date")
    if d1 and d2 and d1 != d2:
        return True

    # If summaries differ substantively in numbers or status
    if summary1 != summary2:
        return True

    return False

async def ingest_memory(
    task_id: UUID,
    structured_output: Dict[str, Any],
    doc_type: str = ""
) -> MemoryEntry:
    """
    Ingests structured data into the Long-Term Evolving Memory Layer:
    1. Extracts primary entity_key (e.g., 'equipment_id:TRB-1105') & secondary entities.
    2. Generates a concise factual summary_text (1-2 sentences).
    3. Computes vector embedding via local sentence-transformers.
    4. Performs deduplication & evolution check against existing memories for this entity:
       - If similarity >= DEDUP_SIMILARITY_THRESHOLD and values changed -> EVOLUTION: inserts new memory
         and sets old memory's superseded_by pointing to the new one.
       - If similarity >= DEDUP_SIMILARITY_THRESHOLD and identical -> DEDUPLICATION: refreshes timestamp.
       - Else -> INGESTION: inserts new memory entry.
    5. Saves embedding in dedicated ChromaDB collection 'memory_entries'.
    6. Automatically creates MemoryLink graph relationships ('same_equipment', 'same_sop_reference', etc.).
    """
    extracted = extract_entities(structured_output, doc_type)
    entity_key = extracted["entity_key"]
    summary_text = generate_summary_text(structured_output, doc_type)
    sec_keys = extracted["secondary_keys"]

    # Compute embedding
    embedding_fn = get_embedding_function()
    new_embedding = embedding_fn([summary_text])[0]

    async with AsyncSessionLocal() as db:
        # Fetch active memory entries for this entity
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.entity_key == entity_key,
                MemoryEntry.superseded_by.is_(None)
            )
            .order_by(desc(MemoryEntry.created_at))
        )
        res = await db.execute(stmt)
        active_entries = res.scalars().all()

        is_evolution = False
        is_exact_dup = False
        prior_entry_to_supersede: Optional[MemoryEntry] = None

        for existing in active_entries:
            # Compute similarity against existing summary
            existing_emb = embedding_fn([existing.summary_text])[0]
            sim = cosine_similarity(new_embedding, existing_emb)

            if sim >= DEDUP_SIMILARITY_THRESHOLD:
                # Compare content for evolution vs duplicate
                if has_fact_evolution(existing.summary_text, summary_text, {}, structured_output):
                    is_evolution = True
                    prior_entry_to_supersede = existing
                    break
                else:
                    is_exact_dup = True
                    existing.last_accessed_at = datetime.utcnow()
                    existing.access_count += 1
                    await db.commit()
                    return existing

        # Detect safety critical status from readings or explicit flag
        compliance = structured_output.get("compliance_status") or structured_output.get("compliance") or ""
        is_safety_critical = (
            bool(structured_output.get("safety_critical")) or
            "non_compliant" in str(compliance).lower() or
            "non-compliant" in str(compliance).lower() or
            "zone c" in str(summary_text).lower() or
            "zone d" in str(summary_text).lower() or
            "violation" in str(summary_text).lower() or
            "emergency" in str(summary_text).lower() or
            "fail" in str(compliance).lower()
        )

        # If it's not a duplicate, create a new MemoryEntry
        new_memory_id = uuid.uuid4()
        new_entry = MemoryEntry(
            id=new_memory_id,
            source_task_id=task_id,
            entity_key=entity_key,
            summary_text=summary_text,
            embedding_id=str(new_memory_id),
            strength_score=1.0,
            safety_critical=is_safety_critical,
            created_at=datetime.utcnow(),
            last_accessed_at=datetime.utcnow(),
            access_count=0,
            superseded_by=None
        )
        db.add(new_entry)
        await db.flush()

        # If evolution detected, mark previous entry as superseded by the new one
        if is_evolution and prior_entry_to_supersede:
            prior_entry_to_supersede.superseded_by = new_entry.id
            # Create temporal evolution link
            temporal_link = MemoryLink(
                id=uuid.uuid4(),
                source_memory_id=prior_entry_to_supersede.id,
                target_memory_id=new_entry.id,
                relation_type="temporal_sequence",
                created_at=datetime.utcnow()
            )
            db.add(temporal_link)

        # Store in ChromaDB dedicated 'memory_entries' collection
        collection = get_memory_collection()
        collection.add(
            ids=[str(new_entry.id)],
            documents=[summary_text],
            metadatas=[{
                "entity_key": entity_key,
                "task_id": str(task_id) if task_id else "",
                "created_at": new_entry.created_at.isoformat(),
                "strength_score": 1.0,
                "sop_reference": str(sec_keys.get("sop_reference") or ""),
                "inspector": str(sec_keys.get("inspector") or "")
            }]
        )

        # Auto-linking: Query all existing memory entries to discover relations
        all_mem_res = await db.execute(
            select(MemoryEntry).where(MemoryEntry.id != new_entry.id)
        )
        all_other_memories = all_mem_res.scalars().all()

        for other in all_other_memories:
            # 1. Same equipment / primary entity link
            if other.entity_key == entity_key:
                link = MemoryLink(
                    id=uuid.uuid4(),
                    source_memory_id=new_entry.id,
                    target_memory_id=other.id,
                    relation_type="same_equipment",
                    created_at=datetime.utcnow()
                )
                db.add(link)

            # 2. Same SOP reference link
            if sec_keys.get("sop_reference") and sec_keys["sop_reference"].lower() in other.summary_text.lower():
                link = MemoryLink(
                    id=uuid.uuid4(),
                    source_memory_id=new_entry.id,
                    target_memory_id=other.id,
                    relation_type="same_sop_reference",
                    created_at=datetime.utcnow()
                )
                db.add(link)

            # 3. Same Inspector link
            if sec_keys.get("inspector") and sec_keys["inspector"].lower() in other.summary_text.lower():
                link = MemoryLink(
                    id=uuid.uuid4(),
                    source_memory_id=new_entry.id,
                    target_memory_id=other.id,
                    relation_type="same_inspector",
                    created_at=datetime.utcnow()
                )
                db.add(link)

        await db.commit()
        await db.refresh(new_entry)
        return new_entry
