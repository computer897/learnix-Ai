"""
Embeddings helper module.

Uses sentence-transformers for generating embeddings with all-MiniLM-L6-v2 model.
"""

import os
import numpy as np
import logging

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

_embedding_model = None


def _load_model():
    """Load the sentence-transformers model (lazy initialization)."""
    global _embedding_model
    
    if _embedding_model is not None:
        return _embedding_model
    
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("✅ Successfully loaded sentence-transformers model")
        return _embedding_model
    except Exception as e:
        logger.error(f"Error loading embedding model: {e}")
        raise RuntimeError(f"Failed to load embedding model: {e}")


def get_embedding(text: str) -> np.ndarray:
    """
    Generate embedding for a text document.
    
    Args:
        text: Input text to embed
        
    Returns:
        Numpy array of embedding vector (384 dimensions)
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return np.zeros(384, dtype=np.float32)
    
    model = _load_model()
    embedding = model.encode([text])[0].astype(np.float32)
    return embedding


def embed_query(text: str) -> np.ndarray:
    """
    Generate embedding for a query.
    
    Same as get_embedding but kept as separate function for clarity
    and potential future query-specific optimizations.
    
    Args:
        text: Query text to embed
        
    Returns:
        Numpy array of embedding vector (384 dimensions)
    """
    return get_embedding(text)


def get_embedding_dimension() -> int:
    """Get the dimensionality of embeddings."""
    model = _load_model()
    if model:
        # Get actual model dimension
        return model.get_sentence_embedding_dimension()
    else:
        # Mock dimension
        return 384
