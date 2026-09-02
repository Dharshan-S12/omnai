import os
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Enforce offline operation defensively
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

CHROMA_PATH = os.environ.get("CHROMA_PATH", "./storage/chroma")
COLLECTION_NAME = "sops"

_chroma_client = None
_embedding_fn = None

def get_chroma_client() -> chromadb.PersistentClient:
    """
    Returns a shared ChromaDB PersistentClient instance with anonymous telemetry explicitly disabled.
    """
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
    return _chroma_client

def get_embedding_function():
    """
    Returns local CPU/GPU sentence-transformer embedding function.
    Requires the embedding model to already be cached locally.
    """
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    return _embedding_fn

def get_collection():
    """
    Returns the shared ChromaDB collection configured with the local embedding function.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn
    )
