import os
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from ..rag.vector_store import policy_store
from ..rag.retrieval import retrieve_policy_knowledge
from ..database.database import SessionLocal
from ..database.models import KnowledgeDocument

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3

class DocumentCreate(BaseModel):
    title: str
    category: str
    filename: str
    content: str

@router.get("")
def list_knowledge_documents():
    db = SessionLocal()
    try:
        docs = db.query(KnowledgeDocument).all()
        return {
            "documents": [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "category": d.category,
                    "filename": d.filename,
                    "chunk_count": d.chunk_count,
                    "last_indexed_at": d.last_indexed_at.isoformat() if d.last_indexed_at else None
                }
                for d in docs
            ],
            "total_chunks": len(policy_store.chunks)
        }
    finally:
        db.close()

@router.post("/reindex")
def trigger_reindex():
    policy_store.index_documents()
    return {
        "success": True,
        "message": f"Successfully re-indexed {len(policy_store.chunks)} policy chunks.",
        "chunk_count": len(policy_store.chunks)
    }

@router.post("/search")
def search_knowledge(req: SearchRequest):
    return retrieve_policy_knowledge(query=req.query, top_k=req.top_k or 3)

@router.post("/create")
def create_document(doc: DocumentCreate):
    kb_dir = "knowledge_base"
    os.makedirs(kb_dir, exist_ok=True)
    filepath = os.path.join(kb_dir, doc.filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(doc.content)

    policy_store.index_documents()
    return {"success": True, "message": f"Document {doc.filename} created and indexed."}
