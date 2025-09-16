"""
Tests for Chat Memory Management Module

Tests the chat memory storage and retrieval functionality for multi-turn
conversations in the RAG AI Agent.

Author: RAG AI Agent Team
Date: 2024-12-19
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
import uuid

from src.memory import (
    ChatMemoryManager, 
    get_chat_memory, 
    store_chat_turn, 
    clear_session_memory
)
from src.models import ChatMessage


class TestChatMemoryManager:
    """Test suite for ChatMemoryManager class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return Mock()

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client for testing."""
        client = Mock()
        client.client = Mock()
        client.client.table.return_value = Mock()
        return client

    @pytest.fixture
    def memory_manager(self, mock_config, mock_supabase_client):
        """Create ChatMemoryManager instance with mocked dependencies."""
        with patch('src.memory.get_config', return_value=mock_config), \
             patch('src.memory.get_supabase_client', return_value=mock_supabase_client):
            return ChatMemoryManager(memory_limit=5)

    @pytest.mark.asyncio
    async def test_get_chat_memory_success(self, memory_manager, mock_supabase_client):
        """Test successful chat memory retrieval."""
        session_id = "test-session-123"
        
        # Mock database response
        mock_response = Mock()
        mock_response.data = [
            {
                'id': 'msg-2',
                'session_id': session_id,
                'role': 'assistant',
                'content': 'AI response',
                'metadata': {},
                'created_at': '2024-01-02T00:00:00Z'
            },
            {
                'id': 'msg-1',
                'session_id': session_id,
                'role': 'user',
                'content': 'User question',
                'metadata': {},
                'created_at': '2024-01-01T00:00:00Z'
            }
        ]
        
        # Setup mock chain
        table_mock = mock_supabase_client.client.table.return_value
        select_mock = table_mock.select.return_value
        eq_mock = select_mock.eq.return_value
        order_mock = eq_mock.order.return_value
        limit_mock = order_mock.limit.return_value
        limit_mock.execute.return_value = mock_response

        result = await memory_manager.get_chat_memory(session_id, limit=5)

        assert len(result) == 2
        assert all(isinstance(msg, ChatMessage) for msg in result)
        assert result[0].content == 'User question'  # Chronological order
        assert result[1].content == 'AI response'
        
        # Verify database call
        mock_supabase_client.client.table.assert_called_with("chat_histories")
        select_mock.eq.assert_called_with("session_id", session_id)
        order_mock.limit.assert_called_with(10)  # limit * 2

    @pytest.mark.asyncio
    async def test_get_chat_memory_no_history(self, memory_manager, mock_supabase_client):
        """Test chat memory retrieval with no history."""
        session_id = "new-session-123"
        
        mock_response = Mock()
        mock_response.data = []
        
        table_mock = mock_supabase_client.client.table.return_value
        table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = await memory_manager.get_chat_memory(session_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_store_chat_turn_success(self, memory_manager, mock_supabase_client):
        """Test successful conversation turn storage."""
        session_id = "test-session-123"
        user_message = "What is Python?"
        ai_response = "Python is a programming language."
        
        # Mock successful insert response
        mock_response = Mock()
        mock_response.data = [{'id': 'user-msg'}, {'id': 'ai-msg'}]
        
        table_mock = mock_supabase_client.client.table.return_value
        table_mock.insert.return_value.execute.return_value = mock_response
        
        # Mock cleanup method
        memory_manager._cleanup_old_messages = AsyncMock()

        await memory_manager.store_chat_turn(session_id, user_message, ai_response)

        # Verify database insert was called
        table_mock.insert.assert_called_once()
        insert_args = table_mock.insert.call_args[0][0]
        
        assert len(insert_args) == 2  # User message + AI response
        assert insert_args[0]['role'] == 'user'
        assert insert_args[0]['content'] == user_message
        assert insert_args[1]['role'] == 'assistant'
        assert insert_args[1]['content'] == ai_response
        
        # Verify cleanup was called
        memory_manager._cleanup_old_messages.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_store_chat_turn_failure(self, memory_manager, mock_supabase_client):
        """Test conversation turn storage failure."""
        session_id = "test-session-123"
        
        # Mock insert failure
        mock_response = Mock()
        mock_response.data = []  # Empty response indicates failure
        
        table_mock = mock_supabase_client.client.table.return_value
        table_mock.insert.return_value.execute.return_value = mock_response

        with pytest.raises(Exception, match="Failed to store both messages"):
            await memory_manager.store_chat_turn(session_id, "user msg", "ai msg")

    @pytest.mark.asyncio
    async def test_store_user_message_success(self, memory_manager, mock_supabase_client):
        """Test successful user message storage."""
        session_id = "test-session-123"
        content = "What is machine learning?"
        metadata = {"timestamp": "2024-01-01"}
        
        # Mock successful insert
        mock_response = Mock()
        mock_response.data = [{'id': 'user-msg-123'}]
        
        table_mock = mock_supabase_client.client.table.return_value
        table_mock.insert.return_value.execute.return_value = mock_response

        result = await memory_manager.store_user_message(session_id, content, metadata)

        assert isinstance(result, str)  # Returns message ID
        
        # Verify insert call
        table_mock.insert.assert_called_once()
        insert_args = table_mock.insert.call_args[0][0]
        assert insert_args['role'] == 'user'
        assert insert_args['content'] == content
        assert insert_args['metadata'] == metadata

    @pytest.mark.asyncio
    async def test_store_ai_response_success(self, memory_manager, mock_supabase_client):
        """Test successful AI response storage."""
        session_id = "test-session-123"
        content = "Machine learning is a subset of AI."
        metadata = {"model": "gpt-4", "citations": ["source1"]}
        
        # Mock successful insert
        mock_response = Mock()
        mock_response.data = [{'id': 'ai-msg-123'}]
        
        table_mock = mock_supabase_client.client.table.return_value
        table_mock.insert.return_value.execute.return_value = mock_response
        
        # Mock cleanup
        memory_manager._cleanup_old_messages = AsyncMock()

        result = await memory_manager.store_ai_response(session_id, content, metadata)

        assert isinstance(result, str)  # Returns message ID
        
        # Verify insert and cleanup
        table_mock.insert.assert_called_once()
        memory_manager._cleanup_old_messages.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_clear_session_memory_success(self, memory_manager, mock_supabase_client):
        """Test successful session memory clearing."""
        session_id = "test-session-123"
        
        table_mock = mock_supabase_client.client.table.return_value
        delete_mock = table_mock.delete.return_value
        eq_mock = delete_mock.eq.return_value
        eq_mock.execute.return_value = Mock()

        await memory_manager.clear_session_memory(session_id)

        # Verify delete call
        table_mock.delete.assert_called_once()
        delete_mock.eq.assert_called_once_with("session_id", session_id)

    @pytest.mark.asyncio
    async def test_cleanup_old_messages_success(self, memory_manager, mock_supabase_client):
        """Test successful cleanup of old messages."""
        session_id = "test-session-123"
        memory_manager.memory_limit = 2  # Keep only 2 turns (4 messages)
        
        # Mock messages beyond limit
        mock_response = Mock()
        mock_response.data = [
            {'id': 'msg-5', 'created_at': '2024-01-05T00:00:00Z'},
            {'id': 'msg-4', 'created_at': '2024-01-04T00:00:00Z'},
            {'id': 'msg-3', 'created_at': '2024-01-03T00:00:00Z'},
            {'id': 'msg-2', 'created_at': '2024-01-02T00:00:00Z'},
            {'id': 'msg-1', 'created_at': '2024-01-01T00:00:00Z'},  # Should be deleted
        ]
        
        table_mock = mock_supabase_client.client.table.return_value
        
        # Mock select query
        select_mock = table_mock.select.return_value
        eq_mock = select_mock.eq.return_value
        order_mock = eq_mock.order.return_value
        order_mock.execute.return_value = mock_response
        
        # Mock delete query
        delete_mock = table_mock.delete.return_value
        in_mock = delete_mock.in_.return_value
        in_mock.execute.return_value = Mock()

        await memory_manager._cleanup_old_messages(session_id)

        # Verify cleanup deleted old message
        delete_mock.in_.assert_called_once_with("id", ['msg-1'])

    @pytest.mark.asyncio
    async def test_cleanup_old_messages_no_cleanup_needed(self, memory_manager, mock_supabase_client):
        """Test cleanup when no cleanup is needed."""
        session_id = "test-session-123"
        memory_manager.memory_limit = 5
        
        # Mock fewer messages than limit
        mock_response = Mock()
        mock_response.data = [
            {'id': 'msg-2', 'created_at': '2024-01-02T00:00:00Z'},
            {'id': 'msg-1', 'created_at': '2024-01-01T00:00:00Z'},
        ]
        
        table_mock = mock_supabase_client.client.table.return_value
        table_mock.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

        await memory_manager._cleanup_old_messages(session_id)

        # Verify no delete was called
        table_mock.delete.assert_not_called()


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    @patch('src.memory.get_memory_manager')
    async def test_get_chat_memory_function(self, mock_get_manager):
        """Test get_chat_memory convenience function."""
        mock_manager = Mock()
        mock_messages = [Mock()]
        mock_manager.get_chat_memory = AsyncMock(return_value=mock_messages)
        mock_get_manager.return_value = mock_manager

        result = await get_chat_memory("session-123", limit=5)

        assert result == mock_messages
        mock_manager.get_chat_memory.assert_called_once_with("session-123", 5)

    @pytest.mark.asyncio
    @patch('src.memory.get_memory_manager')
    async def test_store_chat_turn_function(self, mock_get_manager):
        """Test store_chat_turn convenience function."""
        mock_manager = Mock()
        mock_manager.store_chat_turn = AsyncMock()
        mock_get_manager.return_value = mock_manager

        await store_chat_turn("session-123", "user msg", "ai response", {"key": "value"})

        mock_manager.store_chat_turn.assert_called_once_with(
            "session-123", "user msg", "ai response", {"key": "value"}
        )

    @pytest.mark.asyncio
    @patch('src.memory.get_memory_manager')
    async def test_clear_session_memory_function(self, mock_get_manager):
        """Test clear_session_memory convenience function."""
        mock_manager = Mock()
        mock_manager.clear_session_memory = AsyncMock()
        mock_get_manager.return_value = mock_manager

        await clear_session_memory("session-123")

        mock_manager.clear_session_memory.assert_called_once_with("session-123")
