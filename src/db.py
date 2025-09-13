"""Supabase client and database helpers for the RAG AI Agent."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from .config import settings
from .models import Document, VectorChunk, ChatMessage


logger = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper for Supabase client with RAG-specific operations."""
    
    def __init__(self) -> None:
        """Initialize Supabase client."""
        # Configure client options for better performance and error handling
        options = ClientOptions(
            postgrest_client_timeout=settings.supabase_timeout_seconds,
            storage_client_timeout=settings.supabase_timeout_seconds,
        )
        
        self.client: Client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_anon_key,
            options=options
        )
        
        # Admin client for operations requiring elevated privileges
        self.admin_client: Client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
            options=options
        )
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            # Simple query to test connection
            result = self.client.table("documents").select("count", count="exact").execute()
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    # Document operations
    def create_document(self, filename: str) -> Document:
        """Create a new document record."""
        try:
            result = self.client.table("documents").insert({
                "filename": filename
            }).execute()
            
            if result.data:
                doc_data = result.data[0]
                return Document(
                    id=UUID(doc_data["id"]),
                    filename=doc_data["filename"],
                    uploaded_at=doc_data["uploaded_at"]
                )
            else:
                raise ValueError("Failed to create document: no data returned")
                
        except Exception as e:
            logger.error(f"Error creating document {filename}: {e}")
            raise
    
    def get_document(self, doc_id: UUID) -> Optional[Document]:
        """Get document by ID."""
        try:
            result = self.client.table("documents").select("*").eq("id", str(doc_id)).execute()
            
            if result.data:
                doc_data = result.data[0]
                return Document(
                    id=UUID(doc_data["id"]),
                    filename=doc_data["filename"],
                    uploaded_at=doc_data["uploaded_at"]
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            raise
    
    def list_documents(self) -> List[Document]:
        """List all documents."""
        try:
            result = self.client.table("documents").select("*").order("uploaded_at", desc=True).execute()
            
            documents = []
            for doc_data in result.data:
                documents.append(Document(
                    id=UUID(doc_data["id"]),
                    filename=doc_data["filename"],
                    uploaded_at=doc_data["uploaded_at"]
                ))
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise
    
    def delete_document(self, doc_id: UUID) -> bool:
        """Delete document and all associated vectors (cascade delete)."""
        try:
            result = self.client.table("documents").delete().eq("id", str(doc_id)).execute()
            logger.info(f"Document {doc_id} and associated vectors deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            raise
    
    # Vector operations
    def insert_vectors(self, vectors: List[VectorChunk]) -> bool:
        """Insert multiple vector chunks."""
        try:
            # Convert VectorChunk objects to dictionaries for insertion
            vector_data = []
            for vector in vectors:
                vector_data.append({
                    "doc_id": str(vector.doc_id),
                    "chunk_id": vector.chunk_id,
                    "content": vector.content,
                    "embedding": vector.embedding,
                    "metadata": vector.metadata or {}
                })
            
            result = self.client.table("vectors").insert(vector_data).execute()
            logger.info(f"Inserted {len(vectors)} vectors")
            return True
            
        except Exception as e:
            logger.error(f"Error inserting vectors: {e}")
            raise
    
    def vector_search(self, query_embedding: List[float], top_k: int = 4) -> List[VectorChunk]:
        """Perform vector similarity search using pgvector."""
        try:
            # Use RPC function for vector similarity search
            result = self.client.rpc(
                "vector_search",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k
                }
            ).execute()
            
            vectors = []
            for vector_data in result.data:
                vectors.append(VectorChunk(
                    id=UUID(vector_data["id"]),
                    doc_id=UUID(vector_data["doc_id"]),
                    chunk_id=vector_data["chunk_id"],
                    content=vector_data["content"],
                    embedding=vector_data["embedding"],
                    metadata=vector_data["metadata"]
                ))
            
            return vectors
            
        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            raise
    
    def get_document_vectors(self, doc_id: UUID) -> List[VectorChunk]:
        """Get all vectors for a specific document."""
        try:
            result = self.client.table("vectors").select("*").eq("doc_id", str(doc_id)).order("chunk_id").execute()
            
            vectors = []
            for vector_data in result.data:
                vectors.append(VectorChunk(
                    id=UUID(vector_data["id"]),
                    doc_id=UUID(vector_data["doc_id"]),
                    chunk_id=vector_data["chunk_id"],
                    content=vector_data["content"],
                    embedding=vector_data["embedding"],
                    metadata=vector_data["metadata"]
                ))
            
            return vectors
            
        except Exception as e:
            logger.error(f"Error getting vectors for document {doc_id}: {e}")
            raise
    
    # Chat history operations
    def store_chat_message(self, message: ChatMessage) -> ChatMessage:
        """Store a chat message."""
        try:
            result = self.client.table("chat_histories").insert({
                "session_id": message.session_id,
                "turn_index": message.turn_index,
                "user_message": message.user_message,
                "ai_response": message.ai_response
            }).execute()
            
            if result.data:
                chat_data = result.data[0]
                return ChatMessage(
                    id=UUID(chat_data["id"]),
                    session_id=chat_data["session_id"],
                    turn_index=chat_data["turn_index"],
                    user_message=chat_data["user_message"],
                    ai_response=chat_data["ai_response"],
                    created_at=chat_data["created_at"]
                )
            else:
                raise ValueError("Failed to store chat message: no data returned")
                
        except Exception as e:
            logger.error(f"Error storing chat message: {e}")
            raise
    
    def get_chat_history(self, session_id: str, limit: int = 5) -> List[ChatMessage]:
        """Get recent chat history for a session."""
        try:
            result = (
                self.client.table("chat_histories")
                .select("*")
                .eq("session_id", session_id)
                .order("turn_index", desc=True)
                .limit(limit)
                .execute()
            )
            
            messages = []
            for chat_data in reversed(result.data):  # Reverse to get chronological order
                messages.append(ChatMessage(
                    id=UUID(chat_data["id"]),
                    session_id=chat_data["session_id"],
                    turn_index=chat_data["turn_index"],
                    user_message=chat_data["user_message"],
                    ai_response=chat_data["ai_response"],
                    created_at=chat_data["created_at"]
                ))
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting chat history for session {session_id}: {e}")
            raise
    
    def clear_chat_history(self, session_id: str) -> bool:
        """Clear chat history for a session."""
        try:
            result = self.client.table("chat_histories").delete().eq("session_id", session_id).execute()
            logger.info(f"Chat history cleared for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing chat history for session {session_id}: {e}")
            raise


# Global database client instance
_db_client: Optional[SupabaseClient] = None


def get_db_client() -> SupabaseClient:
    """Get or create global database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = SupabaseClient()
    return _db_client


def init_db_client() -> SupabaseClient:
    """Initialize and test database client."""
    client = get_db_client()
    if not client.test_connection():
        raise ConnectionError("Failed to connect to Supabase database")
    return client
