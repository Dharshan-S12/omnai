import os
import math
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional

from sqlalchemy.future import select
from sqlalchemy import or_, and_, desc, asc
from app.database import AsyncSessionLocal
from app.models import MemoryEntry, MemoryLink
from app.memory.client import get_memory_collection

# Named tuning parameters
DECAY_HALF_LIFE_DAYS = 30.0

def compute_strength(entry: MemoryEntry) -> float:
    """
    Computes dynamic memory strength:
    - Base strength score (default 1.0)
    - Safety-Critical Exemption: Past Zone C/D readings, equipment faults, and violations
      are tagged safety_critical=True and EXEMPT from decay (decay rate = 0.0, factor = 1.0).
    - General conversational/contextual memories decay exponentially on Ebbinghaus curve (half-life of ~30 days).
    - Boosted by access_count (frequently retrieved memories strengthen).
    """
    now = datetime.utcnow()
    last_accessed = entry.last_accessed_at or entry.created_at or now
    
    # Handle timezone awareness safely if stored as naive utc
    if last_accessed.tzinfo is not None:
        last_accessed = last_accessed.replace(tzinfo=None)
    
    delta_seconds = max(0.0, (now - last_accessed).total_seconds())
    delta_days = delta_seconds / 86400.0

    # Safety-critical facts never decay
    is_safety_critical = getattr(entry, "safety_critical", False) is True
    if is_safety_critical:
        decay_factor = 1.0
    else:
        # Exponential decay formula: 2^(-delta_days / half_life)
        decay_factor = math.pow(2.0, - (delta_days / DECAY_HALF_LIFE_DAYS))
    
    # Access frequency boost (each access adds 10% boost, up to 2.0x multiplier)
    access_boost = 1.0 + 0.1 * min(float(entry.access_count or 0), 10.0)

    base_score = float(entry.strength_score or 1.0)
    return max(0.01, base_score * decay_factor * access_boost)

async def search_memory(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Searches the structured long-term memory layer:
    1. Performs vector semantic query against dedicated ChromaDB collection 'memory_entries'.
    2. Fetches MemoryEntry database entities and calculates dynamic strength score.
    3. Re-ranks results by (vector_similarity * computed_strength).
    4. Increments access_count and updates last_accessed_at (memory strengthening).
    5. Resolves memory_links graph to include linked historical/related memories in context.
    6. Constructs human-readable explanation of why each memory was retrieved and how it links.
    """
    if not query or not query.strip():
        return []

    collection = get_memory_collection()
    # Query ChromaDB for candidate semantic matches
    try:
        results = collection.query(
            query_texts=[query.strip()],
            n_results=min(max(top_k * 2, 5), 20)
        )
    except Exception as e:
        print(f"Warning: Memory collection search failed or empty ({e})")
        return []

    if not results or "ids" not in results or not results["ids"] or not results["ids"][0]:
        return []

    chroma_ids = results["ids"][0]
    chroma_distances = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(chroma_ids)

    # Convert string IDs to UUIDs for DB lookup
    id_dist_map = {}
    for cid, dist in zip(chroma_ids, chroma_distances):
        try:
            id_dist_map[UUID(cid)] = dist
        except Exception:
            pass

    if not id_dist_map:
        return []

    async with AsyncSessionLocal() as db:
        # Fetch matching DB entries
        stmt = select(MemoryEntry).where(MemoryEntry.id.in_(list(id_dist_map.keys())))
        res = await db.execute(stmt)
        entries = res.scalars().all()

        scored_candidates = []
        for entry in entries:
            dist = id_dist_map.get(entry.id, 1.0)
            # Cosine distance in Chroma: 0 is exact match, 2 is opposite.
            # Convert distance to similarity score in [0.0, 1.0]
            sim_score = max(0.0, 1.0 - (dist / 2.0))
            strength = compute_strength(entry)
            combined_score = sim_score * strength

            scored_candidates.append({
                "entry": entry,
                "distance": dist,
                "similarity": sim_score,
                "strength": strength,
                "combined_score": combined_score
            })

        # Rank by combined score descending
        scored_candidates.sort(key=lambda x: x["combined_score"], reverse=True)
        top_candidates = scored_candidates[:top_k]

        formatted_results = []
        for item in top_candidates:
            entry = item["entry"]

            # Update access statistics (strengthening upon recall)
            entry.access_count = (entry.access_count or 0) + 1
            entry.last_accessed_at = datetime.utcnow()

            # Query all related links (bidirectional)
            link_stmt = (
                select(MemoryLink)
                .where(
                    or_(
                        MemoryLink.source_memory_id == entry.id,
                        MemoryLink.target_memory_id == entry.id
                    )
                )
            )
            link_res = await db.execute(link_stmt)
            links = link_res.scalars().all()

            # Collect linked memory IDs
            linked_ids = set()
            relations_by_id = {}
            for l in links:
                other_id = l.target_memory_id if l.source_memory_id == entry.id else l.source_memory_id
                linked_ids.add(other_id)
                relations_by_id.setdefault(other_id, set()).add(l.relation_type)

            # Fetch linked memory records
            linked_memories = []
            if linked_ids:
                linked_entries_res = await db.execute(
                    select(MemoryEntry).where(MemoryEntry.id.in_(list(linked_ids))).order_by(asc(MemoryEntry.created_at))
                )
                for linked_e in linked_entries_res.scalars().all():
                    rels = list(relations_by_id.get(linked_e.id, ["related"]))
                    linked_memories.append({
                        "id": str(linked_e.id),
                        "entity_key": linked_e.entity_key,
                        "summary_text": linked_e.summary_text,
                        "relation_types": rels,
                        "is_current": linked_e.superseded_by is None,
                        "created_at": linked_e.created_at.isoformat() if linked_e.created_at else None
                    })

            # Build explainability description
            rel_types_all = set()
            for rel_set in relations_by_id.values():
                rel_types_all.update(rel_set)
            rel_summary = ", ".join(sorted(rel_types_all)) if rel_types_all else "direct match"

            explanation = (
                f"Matched query via semantic similarity (distance: {item['distance']:.2f}, "
                f"strength: {item['strength']:.2f}); linked to {len(linked_memories)} "
                f"prior/related memories for {entry.entity_key} via [{rel_summary}]"
            )

            formatted_results.append({
                "id": str(entry.id),
                "entity_key": entry.entity_key,
                "summary_text": entry.summary_text,
                "source_task_id": str(entry.source_task_id) if entry.source_task_id else None,
                "strength_score": entry.strength_score,
                "safety_critical": getattr(entry, "safety_critical", False),
                "computed_strength": round(item["strength"], 3),
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "last_accessed_at": entry.last_accessed_at.isoformat() if entry.last_accessed_at else None,
                "access_count": entry.access_count,
                "superseded_by": str(entry.superseded_by) if entry.superseded_by else None,
                "is_current": entry.superseded_by is None,
                "distance": round(item["distance"], 4),
                "similarity": round(item["similarity"], 3),
                "combined_score": round(item["combined_score"], 3),
                "explanation": explanation,
                "linked_memories": linked_memories
            })

        await db.commit()
        return formatted_results

async def get_memory_history(entity_key: str) -> Dict[str, Any]:
    """
    Returns the complete chronological memory evolution chain for a specific entity key.
    Shows all historical inspection records, which entries are superseded, and the current active state.
    """
    async with AsyncSessionLocal() as db:
        stmt = (
            select(MemoryEntry)
            .where(MemoryEntry.entity_key == entity_key)
            .order_by(asc(MemoryEntry.created_at))
        )
        res = await db.execute(stmt)
        entries = res.scalars().all()

        if not entries:
            return {
                "entity_key": entity_key,
                "total_memories": 0,
                "current_memory": None,
                "evolution_chain": []
            }

        evolution_chain = []
        current_entry_dict = None

        for entry in entries:
            strength = compute_strength(entry)

            # Get links for this entry
            link_stmt = select(MemoryLink).where(
                or_(MemoryLink.source_memory_id == entry.id, MemoryLink.target_memory_id == entry.id)
            )
            link_res = await db.execute(link_stmt)
            links = link_res.scalars().all()

            link_info = [
                {
                    "target_id": str(l.target_memory_id if l.source_memory_id == entry.id else l.source_memory_id),
                    "relation_type": l.relation_type
                }
                for l in links
            ]

            entry_dict = {
                "id": str(entry.id),
                "source_task_id": str(entry.source_task_id) if entry.source_task_id else None,
                "entity_key": entry.entity_key,
                "summary_text": entry.summary_text,
                "strength_score": entry.strength_score,
                "safety_critical": getattr(entry, "safety_critical", False),
                "computed_strength": round(strength, 3),
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "last_accessed_at": entry.last_accessed_at.isoformat() if entry.last_accessed_at else None,
                "access_count": entry.access_count,
                "superseded_by": str(entry.superseded_by) if entry.superseded_by else None,
                "is_current": entry.superseded_by is None,
                "links": link_info
            }
            evolution_chain.append(entry_dict)

            if entry.superseded_by is None:
                current_entry_dict = entry_dict

        return {
            "entity_key": entity_key,
            "total_memories": len(evolution_chain),
            "current_memory": current_entry_dict,
            "evolution_chain": evolution_chain
        }
