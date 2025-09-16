"""
Chat Memory Management Module

This module handles chat memory storage and retrieval for multi-turn conversations.
It maintains a rolling window of recent conversation turns to provide context
for coherent multi-turn conversations.

"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
import uuid

from .models import ChatMessage
from .config import get_settings
from .db import get_db_client

logger = logging.getLogger(__name__)


class ChatMemoryManager:
    """Manages chat memory storage and retrieval for conversations."""
    
    def __init__(self, memory_limit: int = 5):
        """
        Initialize the chat memory manager.
        
        Args:
            memory_limit: Maximum number of conversation turns to remember
        """
        self.config = get_settings()
        self.supabase_client = get_db_client()
        self.memory_limit = memory_limit
    
    async def get_chat_memory(
        self, 
        session_id: str, 
        limit: Optional[int] = None
    ) -> List[ChatMessage]:
        """
        Retrieve chat history for a session with rolling window.
        
        Args:
            session_id: Unique session identifier
            limit: Maximum number of messages to retrieve (defaults to memory_limit)
            
        Returns:
            List of ChatMessage objects in chronological order
            
        Raises:
            Exception: If memory retrieval fails
        """
        if limit is None:
            limit = self.memory_limit
            
        logger.info(f"Retrieving chat memory for session {session_id[:8]}... (limit: {limit})")
        
        try:
            response = self.supabase_client.client.table("chat_histories").select("*").eq(
                "session_id", session_id
            ).order("created_at", desc=True).limit(limit * 2).execute()  # Get more to account for user/ai pairs
            
            if not response.data:
                logger.info(f"No chat history found for session {session_id[:8]}...")
                return []
            
            # Convert to ChatMessage objects
            messages = []
            for record in reversed(response.data):  # Reverse to get chronological order
                try:
                    message = ChatMessage(
                        id=record['id'],
                        session_id=record['session_id'],
                        role=record['role'],
                        content=record['content'],
                        metadata=record.get('metadata', {}),
                        created_at=record['created_at']
                    )
                    messages.append(message)
                except Exception as e:
                    logger.warning(f"Failed to parse chat message: {e}")
                    continue
            
            # Ensure we don't exceed the limit (count by message pairs)
            if len(messages) > limit:
                messages = messages[-limit:]
            
            logger.info(f"Retrieved {len(messages)} chat messages for session {session_id[:8]}...")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat memory: {e}")
            raise
    
    async def store_chat_turn(
        self,
        session_id: str,
        user_message: str,
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a complete conversation turn (user message + AI response).
        
        Args:
            session_id: Unique session identifier
            user_message: User's input message
            ai_response: AI's response message
            metadata: Additional metadata for the conversation turn
            
        Raises:
            Exception: If storage fails
        """
        logger.info(f"Storing conversation turn for session {session_id[:8]}...")
        
        if metadata is None:
            metadata = {}
        
        try:
            # Add timestamp to metadata
            turn_timestamp = datetime.now(timezone.utc).isoformat()
            metadata['turn_timestamp'] = turn_timestamp
            
            # Store user message
            user_record = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'role': 'user',
                'content': user_message,
                'metadata': metadata,
                'created_at': turn_timestamp
            }
            
            # Store AI response
            ai_record = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'role': 'assistant',
                'content': ai_response,
                'metadata': metadata,
                'created_at': turn_timestamp
            }
            
            # Insert both messages
            response = self.supabase_client.client.table("chat_histories").insert([
                user_record, ai_record
            ]).execute()
            
            if not response.data or len(response.data) != 2:
                raise Exception("Failed to store both messages")
            
            logger.info(f"Successfully stored conversation turn for session {session_id[:8]}...")
            
            # Clean up old messages if we exceed the memory limit
            await self._cleanup_old_messages(session_id)
            
        except Exception as e:
            logger.error(f"Failed to store conversation turn: {e}")
            raise
    
    async def store_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a user message and return its ID.
        
        Args:
            session_id: Unique session identifier
            content: Message content
            metadata: Additional metadata
            
        Returns:
            The ID of the stored message
            
        Raises:
            Exception: If storage fails
        """
        logger.info(f"Storing user message for session {session_id[:8]}...")
        
        if metadata is None:
            metadata = {}
        
        try:
            message_id = str(uuid.uuid4())
            record = {
                'id': message_id,
                'session_id': session_id,
                'role': 'user',
                'content': content,
                'metadata': metadata,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.supabase_client.client.table("chat_histories").insert(record).execute()
            
            if not response.data:
                raise Exception("Failed to store user message")
            
            logger.info(f"Successfully stored user message {message_id[:8]}...")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to store user message: {e}")
            raise
    
    async def store_ai_response(
        self,
        session_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store an AI response and return its ID.
        
        Args:
            session_id: Unique session identifier
            content: Response content
            metadata: Additional metadata (e.g., citations, model info)
            
        Returns:
            The ID of the stored response
            
        Raises:
            Exception: If storage fails
        """
        logger.info(f"Storing AI response for session {session_id[:8]}...")
        
        if metadata is None:
            metadata = {}
        
        try:
            response_id = str(uuid.uuid4())
            record = {
                'id': response_id,
                'session_id': session_id,
                'role': 'assistant',
                'content': content,
                'metadata': metadata,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = self.supabase_client.client.table("chat_histories").insert(record).execute()
            
            if not response.data:
                raise Exception("Failed to store AI response")
            
            logger.info(f"Successfully stored AI response {response_id[:8]}...")
            
            # Clean up old messages after storing new response
            await self._cleanup_old_messages(session_id)
            
            return response_id
            
        except Exception as e:
            logger.error(f"Failed to store AI response: {e}")
            raise
    
    async def clear_session_memory(self, session_id: str) -> None:
        """
        Clear all chat history for a session.
        
        Args:
            session_id: Session to clear
            
        Raises:
            Exception: If clearing fails
        """
        logger.info(f"Clearing chat memory for session {session_id[:8]}...")
        
        try:
            response = self.supabase_client.client.table("chat_histories").delete().eq(
                "session_id", session_id
            ).execute()
            
            logger.info(f"Cleared chat memory for session {session_id[:8]}...")
            
        except Exception as e:
            logger.error(f"Failed to clear session memory: {e}")
            raise
    
    async def _cleanup_old_messages(self, session_id: str) -> None:
        """
        Clean up old messages beyond the memory limit.
        
        Args:
            session_id: Session to clean up
        """
        try:
            # Get all messages for the session
            response = self.supabase_client.client.table("chat_histories").select("id, created_at").eq(
                "session_id", session_id
            ).order("created_at", desc=True).execute()
            
            if not response.data or len(response.data) <= self.memory_limit * 2:
                return  # No cleanup needed
            
            # Keep only the most recent messages (memory_limit * 2 for user/ai pairs)
            messages_to_keep = self.memory_limit * 2
            old_messages = response.data[messages_to_keep:]
            
            if old_messages:
                old_ids = [msg['id'] for msg in old_messages]
                self.supabase_client.client.table("chat_histories").delete().in_(
                    "id", old_ids
                ).execute()
                
                logger.info(f"Cleaned up {len(old_ids)} old messages for session {session_id[:8]}...")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old messages: {e}")


# Global memory manager instance
_memory_manager: Optional[ChatMemoryManager] = None


def get_memory_manager() -> ChatMemoryManager:
    """Get or create global ChatMemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ChatMemoryManager()
    return _memory_manager


# Convenience functions for backward compatibility
async def get_chat_memory(session_id: str, limit: int = 5) -> List[ChatMessage]:
    """Retrieve chat history for a session."""
    manager = get_memory_manager()
    return await manager.get_chat_memory(session_id, limit)


async def store_chat_turn(
    session_id: str,
    user_message: str,
    ai_response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """Store a complete conversation turn."""
    manager = get_memory_manager()
    return await manager.store_chat_turn(session_id, user_message, ai_response, metadata)


async def clear_session_memory(session_id: str) -> None:
    """Clear all chat history for a session."""
    manager = get_memory_manager()
    return await manager.clear_session_memory(session_id)
