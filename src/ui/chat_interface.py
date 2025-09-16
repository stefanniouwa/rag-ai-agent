"""
Chat interface components for Streamlit frontend.

This module provides the chat UI with message history, response display with citations,
real-time typing indicators, and session management.
"""

import streamlit as st
import logging
import uuid
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import time

from ..chat import ChatOrchestrator
from ..memory import ChatMemoryManager
from ..models import ChatMessage, VectorChunk
from ..config import settings

logger = logging.getLogger(__name__)


class ChatInterfaceManager:
    """Manages chat interface operations and state."""
    
    def __init__(self):
        """Initialize the chat interface manager."""
        self.chat_orchestrator = ChatOrchestrator()
        self.memory_manager = ChatMemoryManager()
    
    def ensure_session_id(self) -> str:
        """
        Ensure we have a valid session ID.
        
        Returns:
            Current or new session ID
        """
        if "session_id" not in st.session_state or st.session_state.session_id is None:
            st.session_state.session_id = str(uuid.uuid4())
            logger.info(f"Created new chat session: {st.session_state.session_id}")
        
        return st.session_state.session_id
    
    def get_chat_history(self, session_id: str, limit: int = 10) -> List[ChatMessage]:
        """
        Get chat history for the current session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of ChatMessage objects
        """
        try:
            # Use asyncio to run the async function
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.memory_manager.get_chat_memory(session_id, limit)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error retrieving chat history: {e}")
            return []
    
    async def generate_response(self, query: str, session_id: str) -> dict:
        """
        Generate AI response for user query.
        
        Args:
            query: User's question
            session_id: Chat session ID
            
        Returns:
            Dictionary with AI response and sources
        """
        try:
            response, sources = await self.chat_orchestrator.process_query(query, session_id)
            return {
                "response": response,
                "sources": sources,
                "session_id": session_id
            }
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": f"I apologize, but I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "session_id": session_id
            }
    
    def store_chat_turn(self, session_id: str, user_message: str, ai_response: str) -> bool:
        """
        Store a chat turn in memory.
        
        Args:
            session_id: Session ID
            user_message: User's message
            ai_response: AI's response
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.memory_manager.store_chat_turn(session_id, user_message, ai_response)
            return True
        except Exception as e:
            logger.error(f"Error storing chat turn: {e}")
            return False
    
    def start_new_session(self) -> str:
        """
        Start a new chat session.
        
        Returns:
            New session ID
        """
        new_session_id = str(uuid.uuid4())
        st.session_state.session_id = new_session_id
        
        # Clear chat history from session state
        if "chat_history" in st.session_state:
            del st.session_state.chat_history
        if "messages" in st.session_state:
            del st.session_state.messages
        
        logger.info(f"Started new chat session: {new_session_id}")
        return new_session_id




def render_chat_header(session_id: str, chat_manager: ChatInterfaceManager):
    """Render chat header with session info and controls."""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"**Session ID:** `{session_id[:8]}...`")
        message_count = len(st.session_state.get("messages", [])) // 2
        st.caption(f"💬 {message_count} messages in this conversation")
    
    with col2:
        if st.button("🆕 New Session", width="stretch"):
            new_session_id = chat_manager.start_new_session()
            st.success(f"Started new session: {new_session_id[:8]}...")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear Chat", width="stretch"):
            st.session_state.messages = []
            st.rerun()
    
    st.markdown("---")


def render_chat_messages():
    """Render chat message history."""
    
    # Container for chat messages
    chat_container = st.container()
    
    with chat_container:
        messages = st.session_state.get("messages", [])
        
        if not messages:
            st.info("👋 Welcome! Ask me anything about your uploaded documents.")
            st.markdown("""
            **Try asking questions like:**
            - "What are the main topics in my documents?"
            - "Summarize the key points from [document name]"
            - "Find information about [specific topic]"
            - "What did the document say about [subject]?"
            """)
            return
        
        # Display messages
        for i, message in enumerate(messages):
            render_message(message, i)


def render_message(message: Dict[str, Any], index: int):
    """
    Render a single chat message.
    
    Args:
        message: Message dictionary with role, content, and optional timestamp
        index: Message index for unique keys
    """
    is_user = message["role"] == "user"
    
    # Message container with styling
    if is_user:
        st.markdown(
            f'<div class="chat-message user-message">'
            f'<strong>You:</strong><br>{message["content"]}'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        # AI message with potential citations
        st.markdown(
            f'<div class="chat-message ai-message">'
            f'<strong>🤖 AI Assistant:</strong><br>'
            f'</div>',
            unsafe_allow_html=True
        )
        
        # Parse and display response with citations
        render_ai_response(message["content"], index)
    
    # Timestamp if available
    if "timestamp" in message:
        timestamp = message["timestamp"]
        if isinstance(timestamp, datetime):
            st.caption(f"⏰ {timestamp.strftime('%H:%M:%S')}")


def render_ai_response(content: str, index: int):
    """
    Render AI response with citation parsing and display.
    
    Args:
        content: AI response content
        index: Message index for unique keys
    """
    # Parse citations from the response
    citations = parse_citations(content)
    
    # Display main response content (without citation markers)
    clean_content = remove_citation_markers(content)
    st.markdown(clean_content)
    
    # Display citations if any
    if citations:
        with st.expander(f"📚 Sources ({len(citations)})", expanded=False):
            for i, citation in enumerate(citations):
                render_citation(citation, f"{index}_{i}")
    
    # Copy response button
    if st.button("📋 Copy Response", key=f"copy_{index}"):
        st.code(clean_content, language=None)


def parse_citations(content: str) -> List[Dict[str, Any]]:
    """
    Parse citation information from AI response.
    
    Args:
        content: AI response content with potential citations
        
    Returns:
        List of citation dictionaries
    """
    citations = []
    
    # Look for citation patterns like [1], [Doc: filename], etc.
    citation_pattern = r'\[([^\]]+)\]'
    matches = re.findall(citation_pattern, content)
    
    for match in matches:
        # Try to parse different citation formats
        if match.startswith('Doc:'):
            # Document reference format: [Doc: filename]
            doc_name = match[4:].strip()
            citations.append({
                'type': 'document',
                'reference': doc_name,
                'text': match
            })
        elif match.isdigit():
            # Numbered reference format: [1]
            citations.append({
                'type': 'numbered',
                'reference': match,
                'text': match
            })
        else:
            # Generic citation
            citations.append({
                'type': 'generic',
                'reference': match,
                'text': match
            })
    
    return citations


def remove_citation_markers(content: str) -> str:
    """
    Remove citation markers from content for display.
    
    Args:
        content: Content with citation markers
        
    Returns:
        Clean content without citation markers
    """
    # Remove citation markers but keep the content readable
    # This is a simple implementation - could be enhanced based on citation format
    cleaned = re.sub(r'\[\d+\]', '', content)
    cleaned = re.sub(r'\[Doc:[^\]]+\]', '', cleaned)
    
    # Clean up extra spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def render_citation(citation: Dict[str, Any], key: str):
    """
    Render a single citation.
    
    Args:
        citation: Citation dictionary
        key: Unique key for the citation widget
    """
    st.markdown(
        f'<div class="citation">'
        f'<strong>Reference:</strong> {citation["reference"]}<br>'
        f'<strong>Type:</strong> {citation["type"]}<br>'
        f'</div>',
        unsafe_allow_html=True
    )


def render_chat_input(chat_manager: ChatInterfaceManager, session_id: str):
    """
    Render chat input interface.
    
    Args:
        chat_manager: ChatInterfaceManager instance
        session_id: Current session ID
    """
    # Input form
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "Ask a question about your documents:",
                placeholder="Type your question here...",
                label_visibility="collapsed"
            )
        
        with col2:
            submit_button = st.form_submit_button("Send 📤", width="stretch")
        
        # Handle form submission
        if submit_button and user_input.strip():
            handle_user_input(user_input.strip(), chat_manager, session_id)


def handle_user_input(user_input: str, chat_manager: ChatInterfaceManager, session_id: str):
    """
    Handle user input and generate AI response.
    
    Args:
        user_input: User's question
        chat_manager: ChatInterfaceManager instance
        session_id: Current session ID
    """
    # Add user message to chat
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now()
    })
    
    # Show user message immediately
    st.rerun()
    
    # Generate AI response
    with st.spinner("🤔 Thinking..."):
        try:
            # Use asyncio to run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(
                chat_manager.generate_response(user_input, session_id)
            )
            loop.close()
            
            # Add AI response to chat
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["response"],
                "timestamp": datetime.now(),
                "sources": response["sources"]
            })
            
            # Store the conversation turn
            chat_manager.store_chat_turn(session_id, user_input, response["response"])
            
        except Exception as e:
            logger.error(f"Error handling user input: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I apologize, but I encountered an error: {str(e)}",
                "timestamp": datetime.now()
            })
    
    # Rerun to show the new messages
    st.rerun()


def render_chat_suggestions():
    """Render suggested questions to help users get started."""
    
    if not st.session_state.get("messages", []):
        st.markdown("#### 💡 Suggested Questions")
        
        suggestions = [
            "What are the main topics covered in my documents?",
            "Summarize the key findings from the uploaded documents",
            "Find information about specific topics or keywords",
            "Compare different documents in my collection",
            "What insights can you provide from my document library?"
        ]
        
        for suggestion in suggestions:
            if st.button(f"💬 {suggestion}", key=f"suggestion_{hash(suggestion)}"):
                # Add suggestion as user input
                st.session_state.messages.append({
                    "role": "user",
                    "content": suggestion,
                    "timestamp": datetime.now()
                })
                st.rerun()


def render_chat_stats(session_id: str):
    """
    Render chat session statistics.
    
    Args:
        session_id: Current session ID
    """
    with st.expander("📊 Session Statistics", expanded=False):
        messages = st.session_state.get("messages", [])
        user_messages = [m for m in messages if m["role"] == "user"]
        ai_messages = [m for m in messages if m["role"] == "assistant"]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("User Messages", len(user_messages))
        
        with col2:
            st.metric("AI Responses", len(ai_messages))
        
        with col3:
            total_chars = sum(len(m["content"]) for m in messages)
            st.metric("Total Characters", f"{total_chars:,}")
        
        # Session info
        st.markdown(f"**Session ID:** `{session_id}`")
        if messages:
            first_message_time = messages[0].get("timestamp")
            if first_message_time:
                st.markdown(f"**Started:** {first_message_time.strftime('%Y-%m-%d %H:%M:%S')}")


def render_chat_interface():
    """Main function to render the complete chat interface."""
    
    chat_manager = ChatInterfaceManager()
    session_id = chat_manager.ensure_session_id()
    
    # Initialize messages in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
        # Load existing chat history
        history = chat_manager.get_chat_history(session_id, limit=20)
        for msg in history:
            st.session_state.messages.extend([
                {"role": "user", "content": msg.user_message, "timestamp": msg.created_at},
                {"role": "assistant", "content": msg.ai_response, "timestamp": msg.created_at}
            ])
    
    # Chat header
    render_chat_header(session_id, chat_manager)
    
    # Main chat area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Messages display
        render_chat_messages()
        
        # Chat input
        render_chat_input(chat_manager, session_id)
    
    with col2:
        # Suggestions (only show if no messages)
        render_chat_suggestions()
        
        # Session statistics
        render_chat_stats(session_id)
        
        # Chat settings
        with st.expander("⚙️ Chat Settings", expanded=False):
            st.slider(
                "Response Length",
                min_value=50,
                max_value=500,
                value=200,
                help="Preferred length of AI responses"
            )
            
            st.selectbox(
                "Response Style",
                ["Detailed", "Concise", "Technical", "Simple"],
                index=0,
                help="AI response style preference"
            )
            
            st.checkbox(
                "Show Sources",
                value=True,
                help="Display source citations with responses"
            )
