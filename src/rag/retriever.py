"""
Vector search retriever for ParkSight RAG chatbot.
Uses Actian VectorAI DB (CortexClient) instead of FAISS.
"""

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from cortex import CortexClient

DIMENSION = 384
COLLECTION_NAME = "parksight_knowledge"
ACTIAN_HOST = "localhost:50051"

_model = None


def get_model():
    """Get or load the embedding model (singleton)."""
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


def retrieve(query: str, top_k: int = 5) -> List[str]:
    """
    Retrieve top-k most relevant documents for a query.

    Args:
        query: User's question or search query
        top_k: Number of results to return

    Returns:
        List of relevant text chunks
    """
    model = get_model()

    # Embed and normalize query for cosine similarity
    query_embedding = model.encode(query)
    query_normalized = (query_embedding / np.linalg.norm(query_embedding)).tolist()

    with CortexClient(ACTIAN_HOST) as client:
        results = client.search(COLLECTION_NAME, query=query_normalized, top_k=top_k, with_payload=True)

    return [r.payload['text'] for r in results]


def health_check() -> bool:
    """Check if Actian VectorAI DB is accessible and collection exists."""
    try:
        with CortexClient(ACTIAN_HOST) as client:
            client.health_check()
            return client.has_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
