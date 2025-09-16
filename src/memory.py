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
            limit: Maximum number of turns to retrieve (defaults to memory_limit)
            
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
            ).order("turn_index", desc=True).limit(limit).execute()
            
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
                        turn_index=record['turn_index'],
                        user_message=record['user_message'],
                        ai_response=record['ai_response'],
                        created_at=record['created_at']
                    )
                    messages.append(message)
                except Exception as e:
                    logger.warning(f"Failed to parse chat message: {e}")
                    continue
            
            logger.info(f"Retrieved {len(messages)} chat turns for session {session_id[:8]}...")
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
        
        try:
            # Get the next turn index
            turn_index = await self._get_next_turn_index(session_id)
            
            # Create the conversation turn record
            turn_record = {
                'id': str(uuid.uuid4()),
                'session_id': session_id,
                'turn_index': turn_index,
                'user_message': user_message,
                'ai_response': ai_response,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Insert the conversation turn
            response = self.supabase_client.client.table("chat_histories").insert(turn_record).execute()
            
            if not response.data:
                raise Exception("Failed to store conversation turn")
            
            logger.info(f"Successfully stored conversation turn {turn_index} for session {session_id[:8]}...")
            
            # Clean up old turns if we exceed the memory limit
            await self._cleanup_old_messages(session_id)
            
        except Exception as e:
            logger.error(f"Failed to store conversation turn: {e}")
            raise
    
    async def _get_next_turn_index(self, session_id: str) -> int:
        """
        Get the next turn index for a session.
        
        Args:
            session_id: Session to get next turn index for
            
        Returns:
            Next turn index (0-based)
        """
        try:
            response = self.supabase_client.client.table("chat_histories").select("turn_index").eq(
                "session_id", session_id
            ).order("turn_index", desc=True).limit(1).execute()
            
            if response.data:
                return response.data[0]['turn_index'] + 1
            else:
                return 0  # First turn
                
        except Exception as e:
            logger.warning(f"Failed to get next turn index, using 0: {e}")
            return 0
    
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
        Clean up old conversation turns beyond the memory limit.
        
        Args:
            session_id: Session to clean up
        """
        try:
            # Get all turns for the session
            response = self.supabase_client.client.table("chat_histories").select("id, turn_index").eq(
                "session_id", session_id
            ).order("turn_index", desc=True).execute()
            
            if not response.data or len(response.data) <= self.memory_limit:
                return  # No cleanup needed
            
            # Keep only the most recent turns
            old_turns = response.data[self.memory_limit:]
            
            if old_turns:
                old_ids = [turn['id'] for turn in old_turns]
                self.supabase_client.client.table("chat_histories").delete().in_(
                    "id", old_ids
                ).execute()
                
                logger.info(f"Cleaned up {len(old_ids)} old turns for session {session_id[:8]}...")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old turns: {e}")


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
