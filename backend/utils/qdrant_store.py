"""
Qdrant vector database storage module.

Handles all Qdrant operations including:
- Collection creation and management
- Document chunk storage with embeddings
- Similarity search
"""

import os
from pathlib import Path
import hashlib
import logging
import uuid
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
# Defer importing heavy ML packages until needed to avoid import-time
# failures when the system Python env has incompatible versions.

logger = logging.getLogger(__name__)


class QdrantStore:
    """Manages Qdrant vector database operations for document chunks."""
    
    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        collection_name: str = "learnix_documents",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize Qdrant client and embedding model.
        
        Args:
            url: Qdrant server URL
            api_key: Qdrant API key (optional for local deployment)
            collection_name: Name of the Qdrant collection
            embedding_model_name: Name of the SentenceTransformer model
        """
        self.collection_name = collection_name
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2
        
        # Initialize Qdrant client
        logger.info(f"Connecting to Qdrant at {url}")
        self.client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=60
        )
        
        # Defer loading the embedding model until first use to avoid heavy downloads at startup
        logger.info(f"Deferring embedding model load for: {embedding_model_name}")
        os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(Path.home() / ".cache" / "sentence_transformers"))
        self.embedding_model = None
        self.embedding_model_name = embedding_model_name
        
        # Ensure collection exists
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Create the Qdrant collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name in collection_names:
                logger.info(f"✅ Collection '{self.collection_name}' already exists")
            else:
                # Create collection with proper configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a text string.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.embedding_dim
        
        # Lazy-load the embedding model if needed
        if self.embedding_model is None:
            try:
                logger.info(f"Loading embedding model now: {self.embedding_model_name}")
                # Import locally to avoid import-time dependency problems
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(self.embedding_model_name, device='cpu')
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise RuntimeError(f"Embedding model load failed: {e}")

        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def generate_chunk_id(self, filename: str, chunk_index: int) -> str:
        """
        Generate a unique ID for a chunk.
        
        Args:
            filename: Original filename
            chunk_index: Index of the chunk
            
        Returns:
            Unique chunk ID as UUID string
        """
        # Create a deterministic UUID based on filename and chunk index
        content = f"{filename}_{chunk_index}"
        # Use UUID5 with a namespace for deterministic generation
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # ISO OID namespace
        return str(uuid.uuid5(namespace, content))
    
    def upsert_chunks(
        self,
        chunks: List[str],
        filename: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Store document chunks with embeddings in Qdrant.
        
        Args:
            chunks: List of text chunks
            filename: Original filename
            metadata: Optional additional metadata
            
        Returns:
            Dictionary with status and count
        """
        if not chunks:
            return {"status": "error", "message": "No chunks provided", "count": 0}
        
        try:
            points = []
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.generate_embedding(chunk)
                
                # Create point ID
                point_id = self.generate_chunk_id(filename, i)
                
                # Create payload
                payload = {
                    "text": chunk,
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                # Add any additional metadata
                if metadata:
                    payload.update(metadata)
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            # Upsert all points to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"✅ Upserted {len(points)} chunks from {filename} to Qdrant")
            return {
                "status": "success",
                "message": f"Stored {len(points)} chunks",
                "count": len(points)
            }
        
        except Exception as e:
            logger.error(f"Error upserting chunks to Qdrant: {e}")
            return {
                "status": "error",
                "message": str(e),
                "count": 0
            }
    
    def search_similar_chunks(
        self,
        query: str,
        top_k: int = 5,
        filename_filter: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for similar chunks using semantic similarity.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filename_filter: Optional filename to filter results
            
        Returns:
            List of dictionaries with chunk text and metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Prepare filter if filename is specified
            query_filter = None
            if filename_filter:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="filename",
                            match=MatchValue(value=filename_filter)
                        )
                    ]
                )
            
            # Search Qdrant
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter
            )
            
            # Format results
            results = []
            for hit in search_results:
                results.append({
                    "text": hit.payload.get("text", ""),
                    "filename": hit.payload.get("filename", ""),
                    "chunk_index": hit.payload.get("chunk_index", 0),
                    "score": float(hit.score)
                })
            
            logger.info(f"Found {len(results)} similar chunks for query")
            return results
        
        except Exception as e:
            logger.error(f"Error searching Qdrant: {e}")
            return []
    
    def delete_document_chunks(self, filename: str) -> bool:
        """
        Delete all chunks for a specific document.
        
        Args:
            filename: Name of the file to delete chunks for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete points by filtering on filename
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="filename",
                            match=MatchValue(value=filename)
                        )
                    ]
                )
            )
            logger.info(f"✅ Deleted all chunks for {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document chunks: {e}")
            return False
    
    def get_collection_info(self) -> Dict:
        """
        Get information about the Qdrant collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "status": collection_info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"error": str(e)}
    
    def list_documents(self) -> List[str]:
        """
        Get list of unique filenames stored in the collection.
        
        Returns:
            List of unique filenames
        """
        try:
            # Scroll through all points to get unique filenames
            # This is a simple implementation; for large collections,
            # consider using aggregations or maintaining a separate index
            offset = None
            filenames = set()
            
            while True:
                records, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=["filename"],
                    with_vectors=False
                )
                
                for record in records:
                    if "filename" in record.payload:
                        filenames.add(record.payload["filename"])
                
                if next_offset is None:
                    break
                offset = next_offset
            
            return sorted(list(filenames))
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []


def create_qdrant_store() -> Optional[QdrantStore]:
    """
    Factory function to create QdrantStore from environment variables.
    
    Returns:
        QdrantStore instance or None if configuration is missing
    """
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION", "learnix_documents")
    embedding_model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    if not url:
        logger.error("QDRANT_URL not set in environment variables")
        return None
    
    try:
        store = QdrantStore(
            url=url,
            api_key=api_key,
            collection_name=collection_name,
            embedding_model_name=embedding_model
        )
        return store
    except Exception as e:
        logger.error(f"Failed to create QdrantStore: {e}", exc_info=True)
        return None
        return None
