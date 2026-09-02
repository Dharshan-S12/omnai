from typing import List
from app.rag.client import get_collection, get_chroma_client, get_embedding_function

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Splits text into fixed-size chunks (~500 chars with 100 char overlap).
    """
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_len:
            break
        start += (chunk_size - overlap)
    return chunks

def ingest_document(text: str, source: str, doc_id: str) -> int:
    """
    Chunks, embeds using local sentence-transformers, and stores in local ChromaDB collection 'sops'.
    """
    collection = get_collection()
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    if not chunks:
        return 0

    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": source, "doc_id": doc_id, "chunk_index": i}
        for i in range(len(chunks))
    ]
    
    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas
    )
    return len(chunks)
