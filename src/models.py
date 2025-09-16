"""Data models and type definitions for the RAG AI Agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Document(BaseModel):
    """Document metadata model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    filename: str
    uploaded_at: datetime


class VectorChunk(BaseModel):
    """Vector chunk model with embedding and metadata."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    embeddings: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    """Chat message model for conversation history."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[UUID] = None
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class ConversionResult(BaseModel):
    """Result from document conversion process."""
    
    model_config = ConfigDict(from_attributes=True)
    
    doc_id: UUID
    filename: str
    chunks_created: int
    conversion_status: str
    error_message: Optional[str] = None


class QueryResult(BaseModel):
    """Result from vector search query."""
    
    model_config = ConfigDict(from_attributes=True)
    
    chunks: List[VectorChunk]
    query_embedding: List[float]
    similarity_scores: List[float]


class ChatResponse(BaseModel):
    """Response from chat generation."""
    
    model_config = ConfigDict(from_attributes=True)
    
    response: str
    sources: List[VectorChunk]
    session_id: str
    turn_index: int


# Type aliases for common data structures
DocumentDict = Dict[str, Union[str, datetime, UUID]]
VectorDict = Dict[str, Union[str, int, List[float], Dict[str, Any], UUID]]
ChatDict = Dict[str, Union[str, int, datetime, UUID]]
