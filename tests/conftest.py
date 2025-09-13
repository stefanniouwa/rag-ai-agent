"""Pytest configuration and fixtures for RAG AI Agent tests."""

import os
import pytest
from typing import Generator
from unittest.mock import Mock, patch
from uuid import uuid4

# Set test environment variables before importing our modules
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ENVIRONMENT", "test")

from src.config import settings
from src.db import SupabaseClient
from src.models import Document, VectorChunk, ChatMessage


@pytest.fixture(scope="session")
def test_settings():
    """Test settings fixture."""
    return settings


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    mock_client = Mock()
    mock_admin_client = Mock()
    
    # Mock successful responses
    mock_response = Mock()
    mock_response.data = []
    mock_response.error = None
    
    mock_client.table.return_value.select.return_value.execute.return_value = mock_response
    mock_client.table.return_value.insert.return_value.execute.return_value = mock_response
    mock_client.table.return_value.update.return_value.execute.return_value = mock_response
    mock_client.table.return_value.delete.return_value.execute.return_value = mock_response
    mock_client.rpc.return_value.execute.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_db_client(mock_supabase_client):
    """Mock database client fixture."""
    with patch('src.db.create_client', return_value=mock_supabase_client):
        db_client = SupabaseClient()
        db_client.client = mock_supabase_client
        db_client.admin_client = mock_supabase_client
        yield db_client


@pytest.fixture
def sample_document():
    """Sample document fixture."""
    return Document(
        id=uuid4(),
        filename="test_document.pdf",
        uploaded_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_vector_chunk():
    """Sample vector chunk fixture."""
    return VectorChunk(
        id=uuid4(),
        doc_id=uuid4(),
        chunk_id=0,
        content="This is a test chunk of text content.",
        embedding=[0.1, 0.2, 0.3] * 512,  # Mock 1536-dim embedding
        metadata={"page": 1, "section": "introduction"}
    )


@pytest.fixture
def sample_chat_message():
    """Sample chat message fixture."""
    return ChatMessage(
        id=uuid4(),
        session_id="test-session-123",
        turn_index=1,
        user_message="What is this document about?",
        ai_response="This document appears to be about testing.",
        created_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_vectors_list(sample_vector_chunk):
    """Sample list of vector chunks."""
    vectors = []
    for i in range(3):
        vector = VectorChunk(
            id=uuid4(),
            doc_id=sample_vector_chunk.doc_id,
            chunk_id=i,
            content=f"Test chunk {i} content",
            embedding=[0.1 * (i + 1), 0.2 * (i + 1), 0.3 * (i + 1)] * 512,
            metadata={"page": i + 1, "chunk": i}
        )
        vectors.append(vector)
    return vectors


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    
    # Mock embedding response
    mock_embedding_response = Mock()
    mock_embedding_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]
    mock_client.embeddings.create.return_value = mock_embedding_response
    
    # Mock chat completion response
    mock_chat_response = Mock()
    mock_chat_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_client.chat.completions.create.return_value = mock_chat_response
    
    return mock_client


@pytest.fixture
def mock_docling_converter():
    """Mock Docling converter for testing."""
    mock_converter = Mock()
    mock_document = Mock()
    mock_document.export_to_markdown.return_value = "# Test Document\n\nTest content"
    
    mock_result = Mock()
    mock_result.document = mock_document
    
    mock_converter.convert.return_value = mock_result
    return mock_converter


@pytest.fixture
def mock_docling_chunker():
    """Mock Docling chunker for testing."""
    mock_chunker = Mock()
    
    # Mock chunk objects
    mock_chunks = []
    for i in range(3):
        mock_chunk = Mock()
        mock_chunk.text = f"Test chunk {i} content"
        mock_chunk.meta = {"page": i + 1, "chunk": i}
        mock_chunks.append(mock_chunk)
    
    mock_chunker.chunk.return_value = iter(mock_chunks)
    return mock_chunker


@pytest.fixture(autouse=True)
def reset_db_client():
    """Reset global database client between tests."""
    import src.db
    src.db._db_client = None
    yield
    src.db._db_client = None


# Test data fixtures
@pytest.fixture
def test_file_content():
    """Sample file content for testing."""
    return "This is a test document with multiple sentences. It contains various information for testing purposes. The content should be long enough to create multiple chunks during processing."


@pytest.fixture
def test_query_embedding():
    """Sample query embedding for testing."""
    return [0.1, 0.2, 0.3] * 512  # Mock 1536-dimensional embedding


@pytest.fixture
def test_session_id():
    """Test session ID."""
    return "test-session-123"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that require database or API connections"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests that test complete workflows"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that may take a long time to run"
    )


# Skip integration tests if no database connection
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle environment-specific tests."""
    skip_integration = pytest.mark.skip(reason="Database connection not available")
    
    for item in items:
        if "integration" in item.keywords:
            # Check if we should skip integration tests
            if os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true":
                item.add_marker(skip_integration)
