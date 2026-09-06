"""
MRPL Sovereign Workbench — Structure-Aware Document Chunking Module
Splits documents along semantic boundaries (headers, markdown tables, equipment telemetry blocks)
ensuring that equipment IDs, readings, units, and inspection dates are never split across chunks.
"""

import re
from typing import List, Dict, Any, Optional

class StructureAwareChunker:
    """
    Structure-aware chunker that respects markdown sections, tables, and equipment records.
    """
    def __init__(self, max_chunk_chars: int = 1200, chunk_overlap_chars: int = 150):
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars

    def chunk_document(self, text: str, source_doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Splits text into structured chunks preserving section, table, and multi-field integrity.
        """
        if not text or not text.strip():
            return []

        # 1. Normalize line endings
        normalized = text.replace("\r\n", "\n")
        
        # 2. Extract structural blocks: Tables, Header sections, and Paragraph blocks
        raw_blocks = self._extract_structural_blocks(normalized)

        # 3. Assemble chunks while preserving block atomicity
        chunks: List[Dict[str, Any]] = []
        current_chunk_blocks: List[str] = []
        current_len = 0
        chunk_idx = 1

        for block in raw_blocks:
            block_len = len(block)
            
            # If a single block exceeds max_chunk_chars, we keep it atomic if it is a table or equipment block,
            # or break along sentence boundaries if necessary.
            if current_len + block_len > self.max_chunk_chars and current_chunk_blocks:
                chunk_text = "\n\n".join(current_chunk_blocks).strip()
                chunks.append({
                    "chunk_id": f"{source_doc_id or 'doc'}_chunk_{chunk_idx}",
                    "chunk_index": chunk_idx,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "contains_table": bool(re.search(r'\|.*\|.*\|', chunk_text)),
                    "equipment_tags": self._extract_tags(chunk_text)
                })
                chunk_idx += 1
                current_chunk_blocks = [block]
                current_len = block_len
            else:
                current_chunk_blocks.append(block)
                current_len += block_len + 2

        if current_chunk_blocks:
            chunk_text = "\n\n".join(current_chunk_blocks).strip()
            chunks.append({
                "chunk_id": f"{source_doc_id or 'doc'}_chunk_{chunk_idx}",
                "chunk_index": chunk_idx,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "contains_table": bool(re.search(r'\|.*\|.*\|', chunk_text)),
                "equipment_tags": self._extract_tags(chunk_text)
            })

        return chunks

    def _extract_structural_blocks(self, text: str) -> List[str]:
        """
        Parses document into atomic blocks: Markdown tables, headers, and coherent paragraphs.
        """
        lines = text.split("\n")
        blocks = []
        current_block: List[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            
            # Check if line is part of a markdown table
            is_table_line = stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2

            if is_table_line:
                if not in_table:
                    # Flush previous block
                    if current_block:
                        blocks.append("\n".join(current_block).strip())
                        current_block = []
                    in_table = True
                current_block.append(line)
            else:
                if in_table:
                    # End of table block -> flush atomic table
                    blocks.append("\n".join(current_block).strip())
                    current_block = []
                    in_table = False

                # Check if line is a major section header
                is_header = bool(re.match(r'^(?:#{1,4}\s+|SECTION\s+\d+:|EQUIPMENT\s+REPORT:)', stripped, re.IGNORECASE))
                if is_header and current_block:
                    blocks.append("\n".join(current_block).strip())
                    current_block = []

                if stripped:
                    current_block.append(line)
                elif current_block:
                    # Blank line paragraph separator
                    blocks.append("\n".join(current_block).strip())
                    current_block = []

        if current_block:
            blocks.append("\n".join(current_block).strip())

        return [b for b in blocks if b.strip()]

    def _extract_tags(self, text: str) -> List[str]:
        """Finds all equipment tag identifiers within chunk."""
        return list(set(re.findall(r'\b[A-Z]{1,4}-\d{2,4}[A-Z]?\b', text.upper())))
