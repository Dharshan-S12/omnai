"""
Test Suite: B2. Embedding Quantization & Storage Optimization Verification
Proves that:
1. float16 quantization achieves exactly 50% memory footprint reduction vs float32 baseline.
2. int8 calibrated quantization achieves ~75% memory footprint reduction.
3. Top-k retrieval accuracy preservation is >= 95% top-5 agreement across random queries.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.retrieval.embedding_store import QuantizedEmbeddingStore

def test_embedding_quantization_suite():
    print("================================================================================")
    print("TEST SUITE: B2 — Embedding Quantization (float16 / int8 vs float32 Baseline)")
    print("================================================================================")

    N = 1000
    D = 384
    np.random.seed(42)

    # Generate synthetic float32 embeddings
    raw_f32 = np.random.randn(N, D).astype(np.float32)
    doc_ids = [f"doc_{i}" for i in range(N)]

    # 1. Initialize stores
    store_f32 = QuantizedEmbeddingStore(precision="float32")
    store_f16 = QuantizedEmbeddingStore(precision="float16")
    store_i8 = QuantizedEmbeddingStore(precision="int8")

    store_f32.add_embeddings(doc_ids, raw_f32)
    store_f16.add_embeddings(doc_ids, raw_f32)
    store_i8.add_embeddings(doc_ids, raw_f32)

    # 2. Measure Storage Footprint
    bytes_f32 = store_f32.get_byte_size()
    bytes_f16 = store_f16.get_byte_size()
    bytes_i8 = store_i8.get_byte_size()

    reduction_f16 = (1.0 - bytes_f16 / bytes_f32) * 100.0
    reduction_i8 = (1.0 - bytes_i8 / bytes_f32) * 100.0

    print(f"\n[1] Storage Footprint Metrics for {N} vectors ({D}-dim):")
    print(f"  -> float32 Baseline: {bytes_f32:,} bytes")
    print(f"  -> float16 Store:    {bytes_f16:,} bytes ({reduction_f16:.1f}% reduction)")
    print(f"  -> int8 Store:       {bytes_i8:,} bytes ({reduction_i8:.1f}% reduction)")

    assert abs(reduction_f16 - 50.0) < 0.1, f"Expected 50.0% reduction for float16, got {reduction_f16:.1f}%"
    assert reduction_i8 >= 74.0, f"Expected >= 74.0% reduction for int8, got {reduction_i8:.1f}%"
    print("  [PASS] Storage footprint reduction verified")

    # 3. Test Retrieval Quality (Top-5 Overlap)
    num_test_queries = 50
    f16_agreements = []
    i8_agreements = []

    for _ in range(num_test_queries):
        q = np.random.randn(D).astype(np.float32)
        
        top_f32 = [doc_id for doc_id, _ in store_f32.query(q, top_k=5)]
        top_f16 = [doc_id for doc_id, _ in store_f16.query(q, top_k=5)]
        top_i8 = [doc_id for doc_id, _ in store_i8.query(q, top_k=5)]

        overlap_f16 = len(set(top_f32).intersection(set(top_f16))) / 5.0
        overlap_i8 = len(set(top_f32).intersection(set(top_i8))) / 5.0

        f16_agreements.append(overlap_f16)
        i8_agreements.append(overlap_i8)

    avg_f16_overlap = np.mean(f16_agreements) * 100.0
    avg_i8_overlap = np.mean(i8_agreements) * 100.0

    print(f"\n[2] Retrieval Accuracy Overlap vs float32 Baseline (across {num_test_queries} queries):")
    print(f"  -> float16 Top-5 Overlap: {avg_f16_overlap:.2f}% (Target: >= 98%)")
    print(f"  -> int8 Top-5 Overlap:    {avg_i8_overlap:.2f}% (Target: >= 95%)")

    assert avg_f16_overlap >= 98.0, f"float16 agreement {avg_f16_overlap:.2f}% was below 98%"
    assert avg_i8_overlap >= 95.0, f"int8 agreement {avg_i8_overlap:.2f}% was below 95%"
    print("  [PASS] Quantized retrieval quality preserved within industrial tolerance")

    print("\n>>> ALL B2 EMBEDDING QUANTIZATION TESTS PASSED (3/3)\n")

if __name__ == "__main__":
    test_embedding_quantization_suite()
