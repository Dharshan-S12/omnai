"""
MRPL Sovereign Workbench — Local High-Performance Vector Index
Provides scalable vector indexing with normalized matrix projection,
incremental document insertion, and fast top-k nearest neighbor retrieval.
Fully local, air-gapped, zero external dependencies.
"""

import os
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

class LocalVectorIndex:
    """
    High-performance vector index supporting incremental inserts and fast batch similarity queries.
    Uses L2-normalized inner products for maximum query throughput.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.doc_ids: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.vectors: Optional[np.ndarray] = None  # Shape (N, D), float32 or float16
        self.is_normalized: bool = True

    def add_documents(
        self,
        doc_ids: List[str],
        vectors: np.ndarray,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Incrementally adds documents and vectors to the index.
        """
        if len(doc_ids) == 0:
            return

        vec_arr = np.asarray(vectors, dtype=np.float32)
        if len(vec_arr.shape) == 1:
            vec_arr = vec_arr.reshape(1, -1)

        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vec_arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vecs = vec_arr / norms

        if self.vectors is None or len(self.vectors) == 0:
            self.vectors = normalized_vecs
        else:
            self.vectors = np.vstack([self.vectors, normalized_vecs])

        self.doc_ids.extend(doc_ids)
        if metadatas:
            self.metadatas.extend(metadatas)
        else:
            self.metadatas.extend([{} for _ in doc_ids])

    def query(
        self,
        query_vector: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs vectorized cosine search against all indexed items.
        Returns sorted list of matches: [{doc_id, score, metadata, rank}].
        """
        if self.vectors is None or len(self.doc_ids) == 0:
            return []

        q_vec = np.asarray(query_vector, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        # Matrix-vector dot product for all N documents simultaneously
        scores = np.dot(self.vectors, q_vec)
        
        # Fast top-k partition / argpartition
        k = min(top_k, len(scores))
        if k <= 0:
            return []

        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for rank, idx in enumerate(top_indices):
            results.append({
                "doc_id": self.doc_ids[idx],
                "score": float(scores[idx]),
                "metadata": self.metadatas[idx] if idx < len(self.metadatas) else {},
                "rank": rank + 1
            })
        return results

    def size(self) -> int:
        """Returns number of indexed vectors."""
        return len(self.doc_ids)

    def clear(self):
        """Resets the vector index."""
        self.doc_ids = []
        self.metadatas = []
        self.vectors = None
