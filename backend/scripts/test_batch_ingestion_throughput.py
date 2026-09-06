"""
Test Suite: B6. Batch Embedding & Async Ingestion Throughput Verification
Proves that:
1. Async batch ingestion processes chunks in parallel/vectorized batches.
2. Demonstrates significant throughput improvement over naive one-at-a-time processing.
3. Successfully populates vector index with all chunks and searchable metadata.
"""

import os
import sys
import time
import asyncio
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.retrieval.batch_ingest import BatchIngestionPipeline

async def mock_async_batch_embed(texts: list[str]) -> np.ndarray:
    """Simulates async model embedding call with small fixed batch latency overhead."""
    # Batch call has fixed overhead + tiny per-item cost
    await asyncio.sleep(0.01 + 0.001 * len(texts))
    dim = 384
    return np.random.randn(len(texts), dim).astype(np.float32)

async def test_batch_ingestion_throughput_suite():
    print("================================================================================")
    print("TEST SUITE: B6 — Batch Embedding & Async Ingestion Throughput")
    print("================================================================================")

    # 1. Create Synthetic Documents
    num_docs = 20
    sample_docs = []
    for i in range(num_docs):
        sample_docs.append({
            "doc_id": f"DOC_INGEST_{i:03d}",
            "content": f"""
            # MRPL Equipment Inspection Survey - Unit {i}
            ## Section 1: Overview
            Routine predictive monitoring conducted for booster pump PMP-{200 + i}.
            
            ## Section 2: Sensor Telemetry
            | Equipment Tag | Parameter | Value | Status |
            |---|---|---|---|
            | PMP-{200 + i} | Vibration RMS | {1.5 + (i * 0.2):.1f} mm/s | Normal |
            | PMP-{200 + i} | Temperature | {60.0 + i:.1f} °C | Normal |
            
            ## Section 3: Engineering Signoff
            Field inspection completed by Technician Team #{i % 5}.
            """
        })

    # 2. Sequential Baseline Ingestion (Batch size = 1)
    pipeline_seq = BatchIngestionPipeline(batch_size=1)
    t0 = time.perf_counter()
    res_seq = await pipeline_seq.ingest_documents_async(sample_docs, mock_async_batch_embed)
    t1 = time.perf_counter()
    dur_seq = t1 - t0

    print(f"\n[1] Sequential Baseline (Batch Size = 1):")
    print(f"  -> Total Chunks: {res_seq['total_chunks']}")
    print(f"  -> Duration:     {dur_seq:.3f} s ({res_seq['throughput_chunks_per_sec']} chunks/sec)")

    # 3. Batched Async Ingestion (Batch size = 16)
    pipeline_batch = BatchIngestionPipeline(batch_size=16)
    t2 = time.perf_counter()
    res_batch = await pipeline_batch.ingest_documents_async(sample_docs, mock_async_batch_embed)
    t3 = time.perf_counter()
    dur_batch = t3 - t2

    speedup = dur_seq / max(1e-6, dur_batch)

    print(f"\n[2] Batched Async Pipeline (Batch Size = 16):")
    print(f"  -> Total Chunks: {res_batch['total_chunks']}")
    print(f"  -> Duration:     {dur_batch:.3f} s ({res_batch['throughput_chunks_per_sec']} chunks/sec)")
    print(f"  -> Throughput Speedup: {speedup:.2f}x")

    assert res_batch["total_chunks"] == res_seq["total_chunks"]
    assert pipeline_batch.vector_index.size() == res_batch["total_chunks"]
    assert speedup >= 1.5, f"Expected at least 1.5x throughput improvement, got {speedup:.2f}x"
    print("  [PASS] Async batched ingestion achieved marked throughput speedup over sequential baseline")

    # 4. Search Indexed Content
    q_vec = np.random.randn(384).astype(np.float32)
    search_hits = pipeline_batch.vector_index.query(q_vec, top_k=3)
    assert len(search_hits) == 3
    print(f"  [PASS] Vector index populated with {pipeline_batch.vector_index.size()} searchable chunks")

    print("\n>>> ALL B6 BATCH INGESTION THROUGHPUT TESTS PASSED (3/3)\n")

if __name__ == "__main__":
    asyncio.run(test_batch_ingestion_throughput_suite())
