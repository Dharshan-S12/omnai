import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.rag import ingest_document, search_kb

router = APIRouter(prefix="/kb", tags=["knowledge_base"])

class KBIngestRequest(BaseModel):
    text: str
    source: str
    doc_id: Optional[str] = None

class KBIngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    doc_id: str
    source: str

class KBSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3

@router.post("/ingest", response_model=KBIngestResponse)
async def ingest_kb_document(req: KBIngestRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty")
    
    doc_id = req.doc_id or str(uuid.uuid4())
    try:
        count = ingest_document(text=req.text, source=req.source, doc_id=doc_id)
        return KBIngestResponse(
            status="success",
            chunks_ingested=count,
            doc_id=doc_id,
            source=req.source
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest document into knowledge base: {str(e)}")

@router.post("/search")
async def search_kb_documents(req: KBSearchRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    try:
        results = search_kb(query=req.query, top_k=req.top_k or 3)
        return {"query": req.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search knowledge base: {str(e)}")
