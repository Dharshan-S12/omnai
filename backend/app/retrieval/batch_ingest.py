"""
MRPL Sovereign Workbench — Batch Embedding & Async Ingestion Pipeline
Batches document chunks for parallel vectorized embedding generation and async ingestion,
maximizing throughput over naive one-at-a-time processing.
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Optional, Awaitable
import numpy as np

from app.retrieval.chunking import StructureAwareChunker
from app.retrieval.vector_index import LocalVectorIndex

class BatchIngestionPipeline:
    """
    Async batch ingestion pipeline that segments documents using structure-aware chunking,
    batches embedding computations, and indexes chunks into the local vector index.
    """
    def __init__(
        self,
        batch_size: int = 16,
        chunker: Optional[StructureAwareChunker] = None,
        vector_index: Optional[LocalVectorIndex] = None
    ):
        self.batch_size = batch_size
        self.chunker = chunker or StructureAwareChunker()
        self.vector_index = vector_index or LocalVectorIndex()

    async def ingest_documents_async(
        self,
        documents: List[Dict[str, str]], # [{"doc_id": "...", "content": "..."}]
        embedding_fn: Callable[[List[str]], Awaitable[np.ndarray]]
    ) -> Dict[str, Any]:
        """
        Asynchronously chunks and batch-embeds a collection of documents.
        """
        start_time = time.perf_counter()
        
        # 1. Structure-aware chunking across all documents
        all_chunks = []
        for doc in documents:
            doc_id = doc.get("doc_id", "doc")
            content = doc.get("content", "")
            chunks = self.chunker.chunk_document(content, source_doc_id=doc_id)
            all_chunks.extend(chunks)

        total_chunks = len(all_chunks)
        if total_chunks == 0:
            return {"total_documents": len(documents), "total_chunks": 0, "duration_ms": 0.0, "throughput_chunks_per_sec": 0.0}

        # 2. Batch Embedding Execution
        chunk_texts = [c["text"] for c in all_chunks]
        chunk_ids = [c["chunk_id"] for c in all_chunks]
        
        all_embeddings = []
        for i in range(0, total_chunks, self.batch_size):
            batch_slice = chunk_texts[i:i + self.batch_size]
            # Call batched async embedding function
            batch_vectors = await embedding_fn(batch_slice)
            all_embeddings.append(batch_vectors)

        stacked_embeddings = np.vstack(all_embeddings)

        # 3. Batch insert into Vector Index
        self.vector_index.add_documents(
            doc_ids=chunk_ids,
            vectors=stacked_embeddings,
            metadatas=all_chunks
        )

        elapsed = time.perf_counter() - start_time
        throughput = total_chunks / max(1e-6, elapsed)

        return {
            "total_documents": len(documents),
            "total_chunks": total_chunks,
            "batches_processed": (total_chunks + self.batch_size - 1) // self.batch_size,
            "duration_ms": round(elapsed * 1000.0, 2),
            "throughput_chunks_per_sec": round(throughput, 2)
        }
