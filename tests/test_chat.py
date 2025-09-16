"""
Tests for Chat and LLM Orchestration Module

Tests the LLM response generation, citation parsing, and complete query
workflow orchestration for the RAG AI Agent.

Author: RAG AI Agent Team
Date: 2024-12-19
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from src.chat import (
    ChatOrchestrator, 
    generate_response, 
    process_query
)
from src.models import VectorChunk, ChatMessage


class TestChatOrchestrator:
    """Test suite for ChatOrchestrator class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock()
        config.openai_api_key = "test-api-key"
        return config

    @pytest.fixture
    def mock_query_processor(self):
        """Mock query processor."""
        processor = Mock()
        processor.search_documents = AsyncMock()
        return processor

    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory manager."""
        manager = Mock()
        manager.get_chat_memory = AsyncMock()
        manager.store_chat_turn = AsyncMock()
        return manager

    @pytest.fixture
    def chat_orchestrator(self, mock_config, mock_query_processor, mock_memory_manager):
        """Create ChatOrchestrator instance with mocked dependencies."""
        with patch('src.chat.get_settings', return_value=mock_config), \
             patch('src.chat.get_query_processor', return_value=mock_query_processor), \
             patch('src.chat.get_memory_manager', return_value=mock_memory_manager), \
             patch('src.chat.OpenAI') as mock_openai:
            
            orchestrator = ChatOrchestrator()
            orchestrator.openai_client = mock_openai.return_value
            orchestrator.query_processor = mock_query_processor
            orchestrator.memory_manager = mock_memory_manager
            return orchestrator

    @pytest.fixture
    def sample_chunks(self):
        """Sample vector chunks for testing."""
        import uuid
        return [
            VectorChunk(
                id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                chunk_id=0,
                content='Machine learning is a subset of artificial intelligence.',
                metadata={'filename': 'ml_guide.pdf', 'similarity_score': 0.85},
                embedding=[0.1] * 1536
            ),
            VectorChunk(
                id=uuid.uuid4(),
                doc_id=uuid.uuid4(),
                chunk_id=1,
                content='Deep learning uses neural networks with multiple layers.',
                metadata={'filename': 'ml_guide.pdf', 'similarity_score': 0.78},
                embedding=[0.2] * 1536
            )
        ]

    @pytest.fixture
    def sample_chat_history(self):
        """Sample chat history for testing."""
        import uuid
        return [
            ChatMessage(
                id=uuid.uuid4(),
                session_id='session-123',
                turn_index=0,
                user_message='What is AI?',
                ai_response='AI stands for Artificial Intelligence.'
            ),
            ChatMessage(
                id=uuid.uuid4(),
                session_id='session-123',
                turn_index=1,
                user_message='How does machine learning work?',
                ai_response='Machine learning uses algorithms to learn from data.'
            )
        ]

    @pytest.mark.asyncio
    async def test_generate_response_success(self, chat_orchestrator, sample_chunks, sample_chat_history):
        """Test successful response generation."""
        query = "What is machine learning?"
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Machine learning is a subset of AI [Source 1]. It involves training algorithms on data [Source 2]."
        chat_orchestrator.openai_client.chat.completions.create.return_value = mock_response

        result = await chat_orchestrator.generate_response(
            query, sample_chunks, sample_chat_history
        )

        assert "Machine learning is a subset of AI" in result
        assert "[Source 1]" in result
        
        # Verify OpenAI call
        chat_orchestrator.openai_client.chat.completions.create.assert_called_once()
        call_args = chat_orchestrator.openai_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4o-mini'
        assert call_args[1]['temperature'] == 0.1

    @pytest.mark.asyncio
    async def test_generate_response_empty_response(self, chat_orchestrator, sample_chunks, sample_chat_history):
        """Test handling of empty OpenAI response."""
        query = "What is machine learning?"
        
        # Mock empty OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        chat_orchestrator.openai_client.chat.completions.create.return_value = mock_response

        with pytest.raises(Exception, match="Empty response from OpenAI"):
            await chat_orchestrator.generate_response(query, sample_chunks, sample_chat_history)

    @pytest.mark.asyncio
    async def test_generate_response_api_failure(self, chat_orchestrator, sample_chunks, sample_chat_history):
        """Test handling of OpenAI API failure."""
        query = "What is machine learning?"
        chat_orchestrator.openai_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            await chat_orchestrator.generate_response(query, sample_chunks, sample_chat_history)

    @pytest.mark.asyncio
    async def test_process_query_with_context(self, chat_orchestrator, sample_chunks, sample_chat_history):
        """Test complete query processing with context."""
        query = "What is machine learning?"
        session_id = "session-123"
        
        # Mock dependencies
        chat_orchestrator.query_processor.search_documents.return_value = sample_chunks
        chat_orchestrator.memory_manager.get_chat_memory.return_value = sample_chat_history
        chat_orchestrator.generate_response = AsyncMock(return_value="ML is a subset of AI [Source 1].")

        response, context = await chat_orchestrator.process_query(query, session_id)

        assert response == "ML is a subset of AI [Source 1]."
        assert context == sample_chunks
        
        # Verify method calls
        chat_orchestrator.query_processor.search_documents.assert_called_once_with(
            query, top_k=4, similarity_threshold=0.7
        )
        chat_orchestrator.memory_manager.get_chat_memory.assert_called_once_with(session_id)
        chat_orchestrator.generate_response.assert_called_once_with(
            query, sample_chunks, sample_chat_history
        )
        chat_orchestrator.memory_manager.store_chat_turn.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_query_no_context(self, chat_orchestrator, sample_chat_history):
        """Test query processing with no relevant context."""
        query = "What is quantum computing?"
        session_id = "session-123"
        
        # Mock no search results
        chat_orchestrator.query_processor.search_documents.return_value = []
        chat_orchestrator.memory_manager.get_chat_memory.return_value = sample_chat_history
        chat_orchestrator._generate_fallback_response = AsyncMock(
            return_value="I couldn't find relevant documents for your question."
        )

        response, context = await chat_orchestrator.process_query(query, session_id)

        assert "couldn't find relevant documents" in response
        assert context == []
        
        # Verify fallback was called
        chat_orchestrator._generate_fallback_response.assert_called_once_with(
            query, sample_chat_history
        )

    def test_build_context_string_with_chunks(self, chat_orchestrator, sample_chunks):
        """Test context string building with chunks."""
        context_string = chat_orchestrator._build_context_string(sample_chunks)

        assert "[Source 1: ml_guide.pdf (Similarity: 0.850)]" in context_string
        assert "[Source 2: ml_guide.pdf (Similarity: 0.780)]" in context_string
        assert "Machine learning is a subset of artificial intelligence." in context_string
        assert "Deep learning uses neural networks" in context_string

    def test_build_context_string_empty(self, chat_orchestrator):
        """Test context string building with no chunks."""
        context_string = chat_orchestrator._build_context_string([])
        assert context_string == "No relevant documents found."

    def test_build_conversation_messages(self, chat_orchestrator, sample_chat_history):
        """Test conversation message building."""
        query = "What is deep learning?"
        context_text = "[Source 1: doc.pdf] Deep learning content..."
        
        messages = chat_orchestrator._build_conversation_messages(
            query, context_text, sample_chat_history
        )

        assert len(messages) >= 3  # System + history + current query
        assert messages[0]['role'] == 'system'
        assert any('What is AI?' in msg['content'] for msg in messages if msg['role'] == 'user')
        assert messages[-1]['role'] == 'user'
        assert context_text in messages[-1]['content']
        assert query in messages[-1]['content']

    def test_parse_citations_single(self, chat_orchestrator):
        """Test citation parsing with single sources."""
        text = "Machine learning is important [Source 1]. Deep learning is a subset [Source 2]."
        citations = chat_orchestrator.parse_citations(text)

        assert len(citations) == 2
        assert citations[0]['source_numbers'] == [1]
        assert citations[1]['source_numbers'] == [2]

    def test_parse_citations_multiple(self, chat_orchestrator):
        """Test citation parsing with multiple sources."""
        text = "This is supported by multiple studies [Source 1, 2, 3]."
        citations = chat_orchestrator.parse_citations(text)

        assert len(citations) == 1
        assert citations[0]['source_numbers'] == [1, 2, 3]

    def test_parse_citations_none(self, chat_orchestrator):
        """Test citation parsing with no citations."""
        text = "This text has no citations."
        citations = chat_orchestrator.parse_citations(text)

        assert citations == []

    def test_format_response_with_sources(self, chat_orchestrator, sample_chunks):
        """Test response formatting with sources."""
        response_text = "Machine learning is important [Source 1]. Deep learning uses neural networks [Source 2]."
        
        formatted = chat_orchestrator.format_response_with_sources(response_text, sample_chunks)

        assert formatted['response'] == response_text
        assert len(formatted['citations']) == 2
        assert len(formatted['sources']) == 2
        assert formatted['source_count'] == 2
        assert formatted['sources'][0]['filename'] == 'ml_guide.pdf'
        assert formatted['sources'][0]['number'] == 1

    @pytest.mark.asyncio
    async def test_generate_fallback_response(self, chat_orchestrator, sample_chat_history):
        """Test fallback response generation."""
        query = "What is quantum computing?"
        
        # Mock OpenAI response for fallback
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "I couldn't find specific documents about quantum computing."
        chat_orchestrator.openai_client.chat.completions.create.return_value = mock_response

        result = await chat_orchestrator._generate_fallback_response(query, sample_chat_history)

        assert "couldn't find specific documents" in result
        
        # Verify OpenAI was called with fallback prompt
        chat_orchestrator.openai_client.chat.completions.create.assert_called_once()
        call_args = chat_orchestrator.openai_client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.3


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    @patch('src.chat.get_chat_orchestrator')
    async def test_generate_response_function(self, mock_get_orchestrator):
        """Test generate_response convenience function."""
        mock_orchestrator = Mock()
        mock_orchestrator.generate_response = AsyncMock(return_value="Generated response")
        mock_get_orchestrator.return_value = mock_orchestrator

        chunks = [Mock()]
        history = [Mock()]
        result = await generate_response("test query", chunks, history)

        assert result == "Generated response"
        mock_orchestrator.generate_response.assert_called_once_with(
            "test query", chunks, history
        )

    @pytest.mark.asyncio
    @patch('src.chat.get_chat_orchestrator')
    async def test_process_query_function(self, mock_get_orchestrator):
        """Test process_query convenience function."""
        mock_orchestrator = Mock()
        mock_response = ("Generated response", [Mock()])
        mock_orchestrator.process_query = AsyncMock(return_value=mock_response)
        mock_get_orchestrator.return_value = mock_orchestrator

        result = await process_query("test query", "session-123", top_k=4, similarity_threshold=0.7)

        assert result == mock_response
        mock_orchestrator.process_query.assert_called_once_with(
            "test query", "session-123", 4, 0.7
        )
