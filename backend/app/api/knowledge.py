"""
Knowledge Base API Endpoints

Allows businesses to:
- Upload documents
- Add FAQs
- Search their knowledge base
- View stats
- Delete documents
"""
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.knowledge.kb_manager import (
    add_document,
    add_documents_batch,
    search_knowledge,
    delete_document,
    clear_knowledge_base,
    get_knowledge_stats,
    seed_sample_knowledge
)

router = APIRouter()


# ── Request / Response Models ─────────────────────────────────────────────────

class AddDocumentRequest(BaseModel):
    tenant_id: str
    content: str
    metadata: Optional[dict] = None


class AddDocumentsRequest(BaseModel):
    tenant_id: str
    documents: List[dict]  # Each dict has: content, metadata


class SearchRequest(BaseModel):
    tenant_id: str
    query: str
    top_k: int = 3


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/add")
async def add_single_document(request: AddDocumentRequest):
    """Add a single document to the knowledge base."""
    doc_id = str(uuid.uuid4())
    
    success = add_document(
        tenant_id=request.tenant_id,
        doc_id=doc_id,
        content=request.content,
        metadata=request.metadata
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add document")
    
    return {
        "message": "Document added successfully",
        "doc_id": doc_id,
        "tenant_id": request.tenant_id
    }


@router.post("/add-batch")
async def add_multiple_documents(request: AddDocumentsRequest):
    """Add multiple documents at once (more efficient)."""
    
    # Generate IDs for each document
    documents = []
    for doc in request.documents:
        documents.append({
            "id": str(uuid.uuid4()),
            "content": doc["content"],
            "metadata": doc.get("metadata", {})
        })
    
    count = add_documents_batch(request.tenant_id, documents)
    
    return {
        "message": f"Added {count} documents",
        "tenant_id": request.tenant_id,
        "count": count
    }


@router.post("/search")
async def search_documents(request: SearchRequest):
    """Search the knowledge base for relevant documents."""
    
    results = search_knowledge(
        tenant_id=request.tenant_id,
        query=request.query,
        top_k=request.top_k
    )
    
    return {
        "query": request.query,
        "tenant_id": request.tenant_id,
        "results": results,
        "count": len(results)
    }


@router.get("/stats/{tenant_id}")
async def get_stats(tenant_id: str):
    """Get statistics about a tenant's knowledge base."""
    stats = get_knowledge_stats(tenant_id)
    return stats


@router.delete("/clear/{tenant_id}")
async def clear_tenant_knowledge(tenant_id: str):
    """Clear all knowledge for a specific tenant."""
    success = clear_knowledge_base(tenant_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear knowledge base")
    
    return {
        "message": f"Knowledge base cleared for tenant: {tenant_id}",
        "tenant_id": tenant_id
    }


@router.post("/seed/{tenant_id}")
async def seed_demo_data(tenant_id: str):
    """Load sample FAQs for testing (useful for demo purposes)."""
    count = seed_sample_knowledge(tenant_id)
    
    return {
        "message": f"Seeded {count} sample FAQs",
        "tenant_id": tenant_id,
        "count": count
    }


@router.post("/upload")
async def upload_document(
    tenant_id: str,
    file: UploadFile = File(...),
    category: Optional[str] = None
):
    """
    Upload a document file (txt, pdf, etc.) and add it to knowledge base.
    For Phase 3, we'll just handle .txt files.
    PDF support can be added in Phase 4.
    """
    
    # Read file content
    content = await file.read()
    
    # For now, only handle text files
    if not file.filename.endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files supported in Phase 3. PDF support coming in Phase 4."
        )
    
    # Decode content
    try:
        text_content = content.decode('utf-8')
    except:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")
    
    # Add to knowledge base
    doc_id = str(uuid.uuid4())
    metadata = {
        "filename": file.filename,
        "category": category or "uploaded",
        "type": "file"
    }
    
    success = add_document(
        tenant_id=tenant_id,
        doc_id=doc_id,
        content=text_content,
        metadata=metadata
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process file")
    
    return {
        "message": "File uploaded and added to knowledge base",
        "filename": file.filename,
        "doc_id": doc_id,
        "tenant_id": tenant_id
    }