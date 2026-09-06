"""
MRPL Sovereign Workbench — Hardened Semantic Response Cache
Enforces strict cosine similarity threshold (>= 0.92) and equipment tag isolation to prevent cache pollution.
Maintains live telemetry for hits, misses, and near-misses.
"""

import os
import re
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from app.rag.client import get_chroma_client, get_embedding_function

CACHE_COLLECTION_NAME = "task_semantic_cache"
SEMANTIC_CACHE_SIMILARITY_THRESHOLD = 0.92
NEAR_MISS_LOWER_BOUND = 0.75
CACHE_TTL_HOURS = 24.0

logger = logging.getLogger("semantic_cache")

# Live in-memory cache telemetry counters
_CACHE_STATS = {
    "hits": 0,
    "misses": 0,
    "near_misses": 0,
    "total_lookups": 0
}

def extract_equipment_tags(text: str) -> list[str]:
    """Extracts standard industrial equipment tags (e.g., TRB-1105, PMP-201A, B-101, VLV-404)."""
    return re.findall(r'\b[A-Z]{1,4}-\d{2,4}[A-Z]?\b', text.upper())

def get_cache_stats() -> Dict[str, Any]:
    """Returns current telemetry metrics for semantic cache hits, misses, and near misses."""
    total = _CACHE_STATS["total_lookups"]
    hit_rate = (_CACHE_STATS["hits"] / total * 100.0) if total > 0 else 0.0
    return {
        "hits": _CACHE_STATS["hits"],
        "misses": _CACHE_STATS["misses"],
        "near_misses": _CACHE_STATS["near_misses"],
        "total_lookups": total,
        "hit_rate_pct": round(hit_rate, 2),
        "threshold": SEMANTIC_CACHE_SIMILARITY_THRESHOLD
    }

def get_cache_collection():
    """
    Returns dedicated ChromaDB collection for semantic response caching.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return client.get_or_create_collection(
        name=CACHE_COLLECTION_NAME,
        embedding_function=embedding_fn
    )

def lookup_semantic_cache(
    prompt_text: str,
    task_type: str = "doc_gen",
    similarity_threshold: float = SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
    ttl_hours: float = CACHE_TTL_HOURS
) -> Optional[Dict[str, Any]]:
    """
    Checks if a semantically equivalent query has already been executed & approved within TTL.
    Enforces strict cosine similarity threshold and equipment tag exact matching.
    """
    global _CACHE_STATS
    if not prompt_text or len(prompt_text.strip()) < 10:
        return None

    _CACHE_STATS["total_lookups"] += 1
    query_tags = set(extract_equipment_tags(prompt_text))

    try:
        collection = get_cache_collection()
        results = collection.query(
            query_texts=[prompt_text.strip()],
            n_results=1,
            where={"task_type": str(task_type)}
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            _CACHE_STATS["misses"] += 1
            return None

        # Chroma distance -> Cosine similarity
        distance = results["distances"][0][0]
        similarity = max(0.0, 1.0 - float(distance))
        matched_prompt = results["documents"][0][0]
        cached_tags = set(extract_equipment_tags(matched_prompt))

        # Check equipment tag boundary isolation (prevent cross-equipment cache pollution)
        if query_tags and cached_tags and query_tags != cached_tags:
            _CACHE_STATS["misses"] += 1
            logger.info(f"Cache miss due to equipment tag mismatch: query tags {query_tags} vs cached {cached_tags}")
            return None

        # Near-miss vs Hit evaluation
        if similarity < similarity_threshold:
            if similarity >= NEAR_MISS_LOWER_BOUND:
                _CACHE_STATS["near_misses"] += 1
                logger.info(f"Semantic cache near-miss (similarity {similarity:.3f} < threshold {similarity_threshold})")
            else:
                _CACHE_STATS["misses"] += 1
            return None

        metadata = results["metadatas"][0][0]
        timestamp = float(metadata.get("timestamp", 0))
        age_hours = (time.time() - timestamp) / 3600.0

        if age_hours > ttl_hours:
            _CACHE_STATS["misses"] += 1
            return None

        _CACHE_STATS["hits"] += 1
        return {
            "cached_task_id": metadata.get("task_id"),
            "similarity": round(similarity, 3),
            "output_text": metadata.get("output_text"),
            "confidence_score": float(metadata.get("confidence_score", 95.0)),
            "age_hours": round(age_hours, 1),
            "matched_prompt": matched_prompt
        }

    except Exception as e:
        _CACHE_STATS["misses"] += 1
        logger.warning(f"Semantic cache lookup notice: {e}")
        return None

def store_semantic_cache(
    task_id: UUID,
    prompt_text: str,
    output_text: str,
    task_type: str = "doc_gen",
    confidence_score: float = 95.0
):
    """
    Stores completed approved task prompt embedding and response in the semantic cache.
    """
    if not prompt_text or not output_text:
        return

    try:
        collection = get_cache_collection()
        cache_id = f"cache_{str(task_id)}"

        collection.upsert(
            ids=[cache_id],
            documents=[prompt_text.strip()],
            metadatas=[{
                "task_id": str(task_id),
                "task_type": str(task_type),
                "confidence_score": float(confidence_score),
                "output_text": output_text[:4000],
                "timestamp": time.time(),
                "created_at_iso": datetime.now(timezone.utc).isoformat()
            }]
        )
    except Exception as e:
        logger.warning(f"Semantic cache store notice: {e}")
