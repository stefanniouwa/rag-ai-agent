"""Data models and type definitions for the RAG AI Agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class Document(BaseModel):
    """Document metadata model."""
    
    id: UUID
    filename: str
    uploaded_at: datetime
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class VectorChunk(BaseModel):
    """Vector chunk model with embedding and metadata."""
    
    id: UUID
    doc_id: UUID
    chunk_id: int
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ChatMessage(BaseModel):
    """Chat message model for conversation history."""
    
    id: Optional[UUID] = None
    session_id: str
    turn_index: int
    user_message: str
    ai_response: str
    created_at: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ConversionResult(BaseModel):
    """Result from document conversion process."""
    
    doc_id: UUID
    filename: str
    chunks_created: int
    conversion_status: str
    error_message: Optional[str] = None
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class QueryResult(BaseModel):
    """Result from vector search query."""
    
    chunks: List[VectorChunk]
    query_embedding: List[float]
    similarity_scores: List[float]
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class ChatResponse(BaseModel):
    """Response from chat generation."""
    
    response: str
    sources: List[VectorChunk]
    session_id: str
    turn_index: int
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


# Type aliases for common data structures
DocumentDict = Dict[str, Union[str, datetime, UUID]]
VectorDict = Dict[str, Union[str, int, List[float], Dict[str, Any], UUID]]
ChatDict = Dict[str, Union[str, int, datetime, UUID]]
