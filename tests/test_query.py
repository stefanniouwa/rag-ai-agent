"""
Tests for Query and Vector Search Module

Tests the query embedding generation and vector similarity search functionality
for the RAG AI Agent.

Author: RAG AI Agent Team
Date: 2024-12-19
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from src.query import QueryProcessor, embed_query, vector_search, search_documents
from src.models import VectorChunk


class TestQueryProcessor:
    """Test suite for QueryProcessor class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.openai_api_key = "test-api-key"
        return config

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        client = Mock()
        client.client = Mock()
        return client

    @pytest.fixture
    def query_processor(self, mock_config, mock_supabase_client):
        """Create QueryProcessor instance with mocked dependencies."""
        with patch('src.query.get_settings', return_value=mock_config), \
             patch('src.query.get_db_client', return_value=mock_supabase_client), \
             patch('src.query.OpenAI') as mock_openai:
            
            processor = QueryProcessor()
            processor.openai_client = mock_openai.return_value
            return processor

    @pytest.mark.asyncio
    async def test_embed_query_success(self, query_processor):
        """Test successful query embedding generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536 dimensions
        query_processor.openai_client.embeddings.create.return_value = mock_response

        query = "What is machine learning?"
        result = await query_processor.embed_query(query)

        assert len(result) == 1536
        assert result == [0.1, 0.2, 0.3] * 512
        query_processor.openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=query,
            dimensions=1536
        )

    @pytest.mark.asyncio
    async def test_embed_query_caching(self, query_processor):
        """Test that query embeddings are cached."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]
        query_processor.openai_client.embeddings.create.return_value = mock_response

        query = "What is machine learning?"
        
        # First call
        result1 = await query_processor.embed_query(query)
        
        # Second call (should use cache)
        result2 = await query_processor.embed_query(query)

        assert result1 == result2
        # OpenAI should only be called once due to caching
        query_processor.openai_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_query_failure(self, query_processor):
        """Test handling of embedding generation failure."""
        query_processor.openai_client.embeddings.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            await query_processor.embed_query("test query")

    @pytest.mark.asyncio
    async def test_vector_search_success(self, query_processor):
        """Test successful vector similarity search."""
        # Mock Supabase response
        mock_response = Mock()
        import uuid
        mock_response.data = [
            {
                'id': str(uuid.uuid4()),
                'document_id': str(uuid.uuid4()),
                'chunk_index': 0,
                'content': 'Test content 1',
                'metadata': {'filename': 'test.pdf'},
                'embeddings': [0.1] * 1536,
                'similarity': 0.85
            },
            {
                'id': str(uuid.uuid4()),
                'document_id': str(uuid.uuid4()),
                'chunk_index': 1,
                'content': 'Test content 2',
                'metadata': {'filename': 'test.pdf'},
                'embeddings': [0.2] * 1536,
                'similarity': 0.75
            }
        ]
        query_processor.supabase_client.client.rpc.return_value.execute.return_value = mock_response

        query_embedding = [0.1] * 1536
        results = await query_processor.vector_search(query_embedding, top_k=2, similarity_threshold=0.7)

        assert len(results) == 2
        assert all(isinstance(chunk, VectorChunk) for chunk in results)
        assert results[0].content == 'Test content 1'
        assert results[0].metadata['similarity_score'] == 0.85
        assert results[1].content == 'Test content 2'
        assert results[1].metadata['similarity_score'] == 0.75

        # Verify RPC call
        query_processor.supabase_client.client.rpc.assert_called_once_with(
            "search_similar_vectors",
            {
                "query_embedding": query_embedding,
                "match_threshold": 0.7,
                "match_count": 2
            }
        )

    @pytest.mark.asyncio
    async def test_vector_search_no_results(self, query_processor):
        """Test vector search with no results."""
        mock_response = Mock()
        mock_response.data = []
        query_processor.supabase_client.client.rpc.return_value.execute.return_value = mock_response

        query_embedding = [0.1] * 1536
        results = await query_processor.vector_search(query_embedding)

        assert results == []

    @pytest.mark.asyncio
    async def test_vector_search_failure(self, query_processor):
        """Test handling of vector search failure."""
        query_processor.supabase_client.client.rpc.side_effect = Exception("Database Error")

        with pytest.raises(Exception, match="Database Error"):
            await query_processor.vector_search([0.1] * 1536)

    @pytest.mark.asyncio
    async def test_search_documents_success(self, query_processor):
        """Test complete document search workflow."""
        # Mock embedding generation
        mock_embedding = [0.1] * 1536
        query_processor.embed_query = AsyncMock(return_value=mock_embedding)

        # Mock vector search
        import uuid
        mock_chunks = [
            VectorChunk(
                id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                chunk_index=0,
                content='Test content',
                metadata={'filename': 'test.pdf', 'similarity_score': 0.85},
                embeddings=mock_embedding
            )
        ]
        query_processor.vector_search = AsyncMock(return_value=mock_chunks)

        query = "What is machine learning?"
        results = await query_processor.search_documents(query, top_k=4, similarity_threshold=0.7)

        assert len(results) == 1
        assert results[0].content == 'Test content'
        
        # Verify calls
        query_processor.embed_query.assert_called_once_with(query)
        query_processor.vector_search.assert_called_once_with(
            mock_embedding, top_k=4, similarity_threshold=0.7
        )

    @pytest.mark.asyncio
    async def test_search_documents_embedding_failure(self, query_processor):
        """Test document search with embedding failure."""
        query_processor.embed_query = AsyncMock(side_effect=Exception("Embedding Error"))

        with pytest.raises(Exception, match="Embedding Error"):
            await query_processor.search_documents("test query")


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    @patch('src.query.get_query_processor')
    async def test_embed_query_function(self, mock_get_processor):
        """Test embed_query convenience function."""
        mock_processor = Mock()
        mock_processor.embed_query = AsyncMock(return_value=[0.1] * 1536)
        mock_get_processor.return_value = mock_processor

        result = await embed_query("test query")

        assert result == [0.1] * 1536
        mock_processor.embed_query.assert_called_once_with("test query")

    @pytest.mark.asyncio
    @patch('src.query.get_query_processor')
    async def test_vector_search_function(self, mock_get_processor):
        """Test vector_search convenience function."""
        mock_processor = Mock()
        mock_chunks = [Mock()]
        mock_processor.vector_search = AsyncMock(return_value=mock_chunks)
        mock_get_processor.return_value = mock_processor

        embedding = [0.1] * 1536
        result = await vector_search(embedding, top_k=4)

        assert result == mock_chunks
        mock_processor.vector_search.assert_called_once_with(embedding, 4)

    @pytest.mark.asyncio
    @patch('src.query.get_query_processor')
    async def test_search_documents_function(self, mock_get_processor):
        """Test search_documents convenience function."""
        mock_processor = Mock()
        mock_chunks = [Mock()]
        mock_processor.search_documents = AsyncMock(return_value=mock_chunks)
        mock_get_processor.return_value = mock_processor

        result = await search_documents("test query", top_k=4, similarity_threshold=0.7)

        assert result == mock_chunks
        mock_processor.search_documents.assert_called_once_with(
            "test query", 4, 0.7
        )
