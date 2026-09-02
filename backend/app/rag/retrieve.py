from typing import List, Dict, Any
from app.rag.client import get_collection

def search_kb(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Embeds query using local sentence-transformers, searches local Chroma collection 'sops',
    and returns the top_k matching chunks.
    """
    if not query:
        return []
        
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    formatted = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else [{}] * len(docs)
        distances = results.get("distances", [[]])[0] if results.get("distances") else [0.0] * len(docs)
        ids = results.get("ids", [[]])[0] if results.get("ids") else [""] * len(docs)
        
        for i, doc in enumerate(docs):
            formatted.append({
                "id": ids[i] if i < len(ids) else "",
                "text": doc,
                "source": metas[i].get("source", "unknown") if i < len(metas) and metas[i] else "unknown",
                "doc_id": metas[i].get("doc_id", "") if i < len(metas) and metas[i] else "",
                "chunk_index": metas[i].get("chunk_index", 0) if i < len(metas) and metas[i] else 0,
                "distance": distances[i] if i < len(distances) else None
            })
            
    return formatted
