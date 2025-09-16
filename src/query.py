"""
Query and Vector Search Module

This module handles query embedding generation and vector similarity search
for the RAG AI Agent. It provides functions to embed user queries and retrieve
the most relevant document chunks from the vector database.

"""

from typing import List, Optional, Dict, Any
import logging
import asyncio
from openai import OpenAI

from .models import VectorChunk
from .config import get_settings
from .db import get_db_client

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Handles query embedding and vector search operations."""
    
    def __init__(self):
        """Initialize the query processor with OpenAI and Supabase clients."""
        self.config = get_settings()
        self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        self.supabase_client = get_db_client()
        self._embedding_cache: Dict[str, List[float]] = {}
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for user query using OpenAI API.
        
        Args:
            query: User's question or search query
            
        Returns:
            List of float values representing the query embedding
            
        Raises:
            Exception: If embedding generation fails
        """
        logger.info(f"Generating embedding for query: {query[:50]}...")
        
        # Check cache first
        if query in self._embedding_cache:
            logger.debug("Using cached embedding for query")
            return self._embedding_cache[query]
        
        try:
            # Generate embedding using OpenAI
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
                dimensions=1536
            )
            
            embedding = response.data[0].embedding
            
            # Cache the result
            self._embedding_cache[query] = embedding
            
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for query: {e}")
            raise
    
    async def vector_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 4,
        similarity_threshold: float = 0.7
    ) -> List[VectorChunk]:
        """
        Perform vector similarity search in Supabase.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of most relevant VectorChunk objects
            
        Raises:
            Exception: If vector search fails
        """
        logger.info(f"Performing vector search with top_k={top_k}, threshold={similarity_threshold}")
        
        try:
            # Use the RPC function for vector similarity search
            response = self.supabase_client.client.rpc(
                "vector_search",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k
                }
            ).execute()
            
            if not response.data:
                logger.warning("No similar vectors found")
                return []
            
            # Convert results to VectorChunk objects and filter by similarity threshold
            chunks = []
            for result in response.data:
                try:
                    # Extract similarity score from the result
                    similarity = result.get('similarity', 0.0)
                    
                    # Skip chunks below similarity threshold
                    if similarity < similarity_threshold:
                        continue
                    
                    chunk = VectorChunk(
                        id=result['id'],
                        doc_id=result['doc_id'],
                        chunk_id=result['chunk_id'],
                        content=result['content'],
                        metadata=result.get('metadata', {}),
                        embedding=result['embedding']
                    )
                    
                    # Add similarity score to metadata for reference
                    chunk.metadata['similarity_score'] = similarity
                    chunks.append(chunk)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse vector result: {e}")
                    continue
            
            logger.info(f"Found {len(chunks)} relevant chunks (threshold: {similarity_threshold})")
            return chunks
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise
    
    async def search_documents(
        self, 
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.7
    ) -> List[VectorChunk]:
        """
        End-to-end document search: embed query and search vectors.
        
        Args:
            query: User's search query
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of most relevant VectorChunk objects
        """
        logger.info(f"Searching documents for query: {query[:50]}...")
        
        try:
            # Step 1: Generate query embedding
            query_embedding = await self.embed_query(query)
            
            # Step 2: Perform vector search
            results = await self.vector_search(
                query_embedding, 
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            logger.info(f"Document search completed: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            raise


# Global query processor instance
_query_processor: Optional[QueryProcessor] = None


def get_query_processor() -> QueryProcessor:
    """Get or create global QueryProcessor instance."""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor


# Convenience functions for backward compatibility
async def embed_query(query: str) -> List[float]:
    """Generate embedding for user query."""
    processor = get_query_processor()
    return await processor.embed_query(query)


async def vector_search(
    query_embedding: List[float], 
    top_k: int = 4
) -> List[VectorChunk]:
    """Perform vector similarity search."""
    processor = get_query_processor()
    return await processor.vector_search(query_embedding, top_k)


async def search_documents(
    query: str,
    top_k: int = 4,
    similarity_threshold: float = 0.7
) -> List[VectorChunk]:
    """Search documents for relevant chunks."""
    processor = get_query_processor()
    return await processor.search_documents(query, top_k, similarity_threshold)
