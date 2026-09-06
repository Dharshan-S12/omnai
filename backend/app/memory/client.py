import os
import chromadb
from app.rag.client import get_chroma_client, get_embedding_function

MEMORY_COLLECTION_NAME = "memory_entries"

def get_memory_collection():
    """
    Returns the dedicated ChromaDB collection for structured long-term memory entries,
    configured with the local sentence-transformers embedding function.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return client.get_or_create_collection(
        name=MEMORY_COLLECTION_NAME,
        embedding_function=embedding_fn
    )
