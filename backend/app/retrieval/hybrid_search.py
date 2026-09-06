"""
MRPL Sovereign Workbench — Hybrid Dense + Sparse Retrieval Engine
Combines BM25Okapi sparse keyword search with dense vector embeddings
via Reciprocal Rank Fusion (RRF). Ideal for equipment tag IDs, part numbers, and SOP codes.
"""

import re
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

class HybridSearchEngine:
    """
    Hybrid Search Engine combining BM25Okapi sparse token matching
    with dense vector similarity using Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k
        self.doc_ids: List[str] = []
        self.corpus_texts: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.metadatas: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.dense_vectors: Optional[np.ndarray] = None

    def _tokenize(self, text: str) -> List[str]:
        """Tokenizes text into lowercase words, retaining hyphenated equipment tags (e.g., TRB-1105)."""
        tokens = re.findall(r'[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*', text.lower())
        return tokens

    def add_documents(
        self,
        doc_ids: List[str],
        documents: List[str],
        dense_vectors: Optional[np.ndarray] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Indexes a collection of documents for both BM25 and dense vector retrieval.
        """
        if not doc_ids:
            return

        self.doc_ids.extend(doc_ids)
        self.corpus_texts.extend(documents)
        
        # Tokenize for BM25
        new_tokenized = [self._tokenize(doc) for doc in documents]
        self.tokenized_corpus.extend(new_tokenized)
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # Dense vectors
        if dense_vectors is not None:
            vec_arr = np.asarray(dense_vectors, dtype=np.float32)
            if self.dense_vectors is None:
                self.dense_vectors = vec_arr
            else:
                self.dense_vectors = np.vstack([self.dense_vectors, vec_arr])

        if metadatas:
            self.metadatas.extend(metadatas)
        else:
            self.metadatas.extend([{} for _ in doc_ids])

    def search_sparse_bm25(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Performs BM25 keyword search."""
        if not self.bm25 or not self.doc_ids:
            return []
        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        
        # If corpus is small (e.g. <= 3 docs) or scores are all 0 due to IDF log(1)=0,
        # compute term frequency overlap boost
        if not np.any(scores > 0):
            tf_scores = np.zeros(len(self.doc_ids), dtype=np.float32)
            for t in tokens:
                for idx, doc_tokens in enumerate(self.tokenized_corpus):
                    if t in doc_tokens:
                        tf_scores[idx] += float(doc_tokens.count(t))
            if np.any(tf_scores > 0):
                scores = tf_scores

        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] > 0:
                results.append({
                    "doc_id": self.doc_ids[idx],
                    "text": self.corpus_texts[idx],
                    "bm25_score": float(scores[idx]),
                    "sparse_rank": rank + 1,
                    "metadata": self.metadatas[idx] if idx < len(self.metadatas) else {}
                })
        return results

    def search_dense(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """Performs dense vector cosine search."""
        if self.dense_vectors is None or len(self.doc_ids) == 0:
            return []
        
        q_vec = np.asarray(query_vector, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        norms = np.linalg.norm(self.dense_vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        norm_matrix = self.dense_vectors / norms

        scores = np.dot(norm_matrix, q_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            results.append({
                "doc_id": self.doc_ids[idx],
                "text": self.corpus_texts[idx],
                "dense_score": float(scores[idx]),
                "dense_rank": rank + 1,
                "metadata": self.metadatas[idx] if idx < len(self.metadatas) else {}
            })
        return results

    def search_hybrid_rrf(
        self,
        query: str,
        query_vector: Optional[np.ndarray] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Executes dense + sparse search and merges results via Reciprocal Rank Fusion (RRF):
        RRF(d) = 1/(K + rank_dense) + 1/(K + rank_sparse)
        """
        sparse_hits = self.search_sparse_bm25(query, top_k=top_k * 2)
        dense_hits = self.search_dense(query_vector, top_k=top_k * 2) if query_vector is not None else []

        rrf_scores: Dict[str, float] = {}
        doc_info: Dict[str, Dict[str, Any]] = {}

        # 1. Score Sparse Ranks
        for item in sparse_hits:
            d_id = item["doc_id"]
            rank = item["sparse_rank"]
            rrf_scores[d_id] = rrf_scores.get(d_id, 0.0) + (1.0 / (self.rrf_k + rank))
            doc_info[d_id] = item

        # 2. Score Dense Ranks
        for item in dense_hits:
            d_id = item["doc_id"]
            rank = item["dense_rank"]
            rrf_scores[d_id] = rrf_scores.get(d_id, 0.0) + (1.0 / (self.rrf_k + rank))
            if d_id not in doc_info:
                doc_info[d_id] = item

        # Sort by merged RRF score
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for rank, (doc_id, score) in enumerate(sorted_docs):
            info = doc_info[doc_id]
            results.append({
                "doc_id": doc_id,
                "rrf_score": round(score, 6),
                "rank": rank + 1,
                "text": info.get("text", ""),
                "metadata": info.get("metadata", {})
            })
        return results
