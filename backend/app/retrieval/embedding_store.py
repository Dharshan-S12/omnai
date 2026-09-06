"""
MRPL Sovereign Workbench — Quantized Embedding Storage Module
Stores high-dimensional embedding vectors as float16 (50% memory reduction)
or calibrated int8 (75% memory reduction) while preserving top-k retrieval accuracy.
"""

import numpy as np
from typing import Tuple, List, Dict, Any, Union

class QuantizedEmbeddingStore:
    """
    Compact vector store supporting float16 and calibrated int8 quantization.
    """
    def __init__(self, precision: str = "float16"):
        assert precision in ["float16", "int8", "float32"], "Supported precisions: float16, int8, float32"
        self.precision = precision
        self.doc_ids: List[str] = []
        self.quantized_matrix: Optional[np.ndarray] = None
        self.scale_factors: Optional[np.ndarray] = None  # Used for int8 calibration

    def quantize(self, matrix_f32: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Quantizes a float32 matrix into float16 or calibrated int8.
        """
        arr = np.asarray(matrix_f32, dtype=np.float32)
        if self.precision == "float16":
            return arr.astype(np.float16), None
        elif self.precision == "int8":
            # Per-row absolute max scaling factor
            max_abs = np.max(np.abs(arr), axis=1, keepdims=True)
            max_abs[max_abs == 0] = 1.0
            scale = max_abs / 127.0
            quantized = np.clip(np.round(arr / scale), -127, 127).astype(np.int8)
            return quantized, scale.flatten()
        else:
            return arr, None

    def dequantize(self, quantized_data: np.ndarray, scales: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Restores quantized matrix back to float32 for computation.
        """
        if self.precision == "float16":
            return quantized_data.astype(np.float32)
        elif self.precision == "int8":
            assert scales is not None, "int8 dequantization requires scale factors"
            return quantized_data.astype(np.float32) * scales.reshape(-1, 1)
        else:
            return quantized_data.astype(np.float32)

    def add_embeddings(self, doc_ids: List[str], embeddings_f32: np.ndarray):
        """
        Adds float32 embeddings after quantizing to configured precision.
        """
        q_data, scales = self.quantize(embeddings_f32)
        if self.quantized_matrix is None:
            self.quantized_matrix = q_data
            self.scale_factors = scales
        else:
            self.quantized_matrix = np.vstack([self.quantized_matrix, q_data])
            if self.precision == "int8":
                self.scale_factors = np.concatenate([self.scale_factors, scales])
        self.doc_ids.extend(doc_ids)

    def get_byte_size(self) -> int:
        """Returns byte size of stored quantized embeddings."""
        if self.quantized_matrix is None:
            return 0
        total_bytes = self.quantized_matrix.nbytes
        if self.scale_factors is not None:
            total_bytes += self.scale_factors.nbytes
        return total_bytes

    def query(self, query_f32: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Queries the quantized embedding store using normalized cosine similarity.
        """
        if self.quantized_matrix is None or len(self.doc_ids) == 0:
            return []

        # Dequantize or compute directly
        stored_f32 = self.dequantize(self.quantized_matrix, self.scale_factors)
        
        # Normalize
        q_vec = np.asarray(query_f32, dtype=np.float32).flatten()
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        norms = np.linalg.norm(stored_f32, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        norm_stored = stored_f32 / norms

        scores = np.dot(norm_stored, q_vec)
        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:k]

        return [(self.doc_ids[i], float(scores[i])) for i in top_indices]
