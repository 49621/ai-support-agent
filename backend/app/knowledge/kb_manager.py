"""
Knowledge Base Manager — RAG (Retrieval Augmented Generation)

This module:
- Stores business FAQs, policies, and documents in a vector database (ChromaDB)
- Converts documents to embeddings
- Retrieves relevant information when a customer asks a question
- Supports per-tenant isolation (each business has its own knowledge)
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict
from dotenv import load_dotenv
from google import genai

load_dotenv("../.env")

# Initialize Gemini for embeddings
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
EMBEDDING_MODEL = "models/text-embedding-004"

# Initialize ChromaDB
CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
os.makedirs(CHROMA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH,
    settings=Settings(anonymized_telemetry=False)
)


# ── Helper Functions ──────────────────────────────────────────────────────────

def get_embedding(text: str) -> List[float]:
    """Generate embedding vector for a piece of text using Gemini."""
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            content=text
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        # Return a zero vector as fallback
        return [0.0] * 768


def get_or_create_collection(tenant_id: str):
    """Get or create a ChromaDB collection for a specific tenant."""
    collection_name = f"knowledge_{tenant_id}"
    try:
        return chroma_client.get_collection(name=collection_name)
    except:
        return chroma_client.create_collection(
            name=collection_name,
            metadata={"tenant_id": tenant_id}
        )


# ── Main Knowledge Base Functions ─────────────────────────────────────────────

def add_document(tenant_id: str, doc_id: str, content: str, metadata: Dict = None) -> bool:
    """
    Add a document to the knowledge base.
    
    Args:
        tenant_id: Which business this belongs to
        doc_id: Unique identifier for this document
        content: The actual text content
        metadata: Optional metadata (e.g., {"type": "faq", "category": "shipping"})
    
    Returns:
        True if successful
    """
    try:
        collection = get_or_create_collection(tenant_id)
        
        # Generate embedding
        embedding = get_embedding(content)
        
        # Store in ChromaDB
        collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata or {}]
        )
        
        print(f"✅ Added document: {doc_id} to tenant: {tenant_id}")
        return True
    
    except Exception as e:
        print(f"❌ Error adding document: {e}")
        return False


def add_documents_batch(tenant_id: str, documents: List[Dict]) -> int:
    """
    Add multiple documents at once (more efficient).
    
    Args:
        tenant_id: Which business
        documents: List of dicts with keys: id, content, metadata
    
    Returns:
        Number of documents successfully added
    """
    try:
        collection = get_or_create_collection(tenant_id)
        
        ids = [doc["id"] for doc in documents]
        contents = [doc["content"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        
        # Generate all embeddings
        embeddings = [get_embedding(content) for content in contents]
        
        # Store all at once
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        
        print(f"✅ Added {len(documents)} documents to tenant: {tenant_id}")
        return len(documents)
    
    except Exception as e:
        print(f"❌ Error adding batch: {e}")
        return 0


def search_knowledge(tenant_id: str, query: str, top_k: int = 3) -> List[Dict]:
    """
    Search the knowledge base for relevant information.
    
    Args:
        tenant_id: Which business to search in
        query: The customer's question
        top_k: How many relevant documents to return
    
    Returns:
        List of relevant documents with content and metadata
    """
    try:
        collection = get_or_create_collection(tenant_id)
        
        # Check if collection is empty
        if collection.count() == 0:
            print(f"⚠️ Knowledge base empty for tenant: {tenant_id}")
            return []
        
        # Generate embedding for the query
        query_embedding = get_embedding(query)
        
        # Search for similar documents
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Format results
        documents = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                documents.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        print(f"🔍 Found {len(documents)} relevant documents for query: '{query[:50]}...'")
        return documents
    
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []


def delete_document(tenant_id: str, doc_id: str) -> bool:
    """Delete a document from the knowledge base."""
    try:
        collection = get_or_create_collection(tenant_id)
        collection.delete(ids=[doc_id])
        print(f"🗑️ Deleted document: {doc_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting: {e}")
        return False


def clear_knowledge_base(tenant_id: str) -> bool:
    """Clear all knowledge for a specific tenant."""
    try:
        collection_name = f"knowledge_{tenant_id}"
        chroma_client.delete_collection(name=collection_name)
        print(f"🗑️ Cleared knowledge base for tenant: {tenant_id}")
        return True
    except Exception as e:
        print(f"❌ Error clearing: {e}")
        return False


def get_knowledge_stats(tenant_id: str) -> Dict:
    """Get statistics about a tenant's knowledge base."""
    try:
        collection = get_or_create_collection(tenant_id)
        return {
            "tenant_id": tenant_id,
            "document_count": collection.count(),
            "collection_name": f"knowledge_{tenant_id}"
        }
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return {"tenant_id": tenant_id, "document_count": 0, "error": str(e)}


# ── Sample FAQs for Testing ───────────────────────────────────────────────────

SAMPLE_FAQS = [
    {
        "id": "faq_shipping_01",
        "content": "We offer free shipping on all orders over $50. Standard shipping takes 3-5 business days. Express shipping (1-2 days) is available for $15.",
        "metadata": {"category": "shipping", "type": "faq"}
    },
    {
        "id": "faq_returns_01",
        "content": "You can return any item within 30 days of purchase for a full refund. Items must be unused and in original packaging. Return shipping is free.",
        "metadata": {"category": "returns", "type": "faq"}
    },
    {
        "id": "faq_payment_01",
        "content": "We accept Visa, Mastercard, American Express, PayPal, and Apple Pay. All payments are processed securely through Stripe.",
        "metadata": {"category": "payment", "type": "faq"}
    },
    {
        "id": "faq_hours_01",
        "content": "Our customer support is available Monday-Friday 9am-6pm EST. You can also email us anytime at support@example.com and we'll respond within 24 hours.",
        "metadata": {"category": "support", "type": "faq"}
    },
    {
        "id": "faq_tracking_01",
        "content": "Once your order ships, you'll receive a tracking number via email. You can also track your order by logging into your account and viewing order history.",
        "metadata": {"category": "shipping", "type": "faq"}
    }
]


def seed_sample_knowledge(tenant_id: str = "demo-shop"):
    """Load sample FAQs into the knowledge base for testing."""
    print(f"🌱 Seeding sample knowledge for tenant: {tenant_id}")
    count = add_documents_batch(tenant_id, SAMPLE_FAQS)
    print(f"✅ Seeded {count} sample FAQs")
    return count