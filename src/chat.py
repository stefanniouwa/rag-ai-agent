"""
Chat and LLM Orchestration Module

This module handles LLM response generation with retrieved context, citation
parsing and formatting, and orchestrates the complete query-response workflow
for the RAG AI Agent.

"""

from typing import List, Optional, Dict, Any, Tuple
import logging
import json
import re
from openai import OpenAI

from .models import VectorChunk, ChatMessage
from .config import get_settings
from .query import get_query_processor
from .memory import get_memory_manager

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Orchestrates LLM response generation with context and citations."""
    
    def __init__(self):
        """Initialize the chat orchestrator with OpenAI client."""
        self.config = get_settings()
        self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        self.query_processor = get_query_processor()
        self.memory_manager = get_memory_manager()
    
    async def generate_response(
        self,
        query: str,
        context_chunks: List[VectorChunk],
        chat_history: List[ChatMessage],
        model: str = "gpt-4o-mini",
        max_tokens: int = 1000
    ) -> str:
        """
        Generate LLM response with retrieved context and chat history.
        
        Args:
            query: User's question
            context_chunks: Retrieved document chunks for context
            chat_history: Previous conversation messages
            model: OpenAI model to use
            max_tokens: Maximum response length
            
        Returns:
            Generated response with citations
            
        Raises:
            Exception: If response generation fails
        """
        logger.info(f"Generating response for query: {query[:50]}...")
        
        try:
            # Build the context string from chunks
            context_text = self._build_context_string(context_chunks)
            
            # Create the conversation messages
            messages = self._build_conversation_messages(
                query, context_text, chat_history
            )
            
            # Generate response
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.1,  # Low temperature for factual responses
                stream=False
            )
            
            generated_text = response.choices[0].message.content
            
            if not generated_text or not generated_text.strip():
                raise Exception("Empty response from OpenAI")
            
            # Validate response structure
            if len(generated_text) < 10:
                logger.warning(f"Suspiciously short response: {generated_text}")
            
            if not any(keyword in generated_text.lower() for keyword in ['source', 'context', 'document', 'information']):
                logger.warning("Response may not be properly grounded in context")
            
            logger.info(f"Generated response with {len(generated_text)} characters")
            return generated_text
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise
    
    async def process_query(
        self,
        query: str,
        session_id: str,
        top_k: int = 4,
        similarity_threshold: float = 0.7
    ) -> Tuple[str, List[VectorChunk]]:
        """
        Complete query processing workflow: search, retrieve context, generate response.
        
        Args:
            query: User's question
            session_id: Chat session identifier
            top_k: Number of document chunks to retrieve
            similarity_threshold: Minimum similarity for retrieval
            
        Returns:
            Tuple of (generated_response, source_chunks)
            
        Raises:
            Exception: If query processing fails
        """
        logger.info(f"Processing query for session {session_id[:8]}...")
        
        try:
            # Step 1: Retrieve relevant document chunks
            context_chunks = await self.query_processor.search_documents(
                query, top_k=top_k, similarity_threshold=similarity_threshold
            )
            
            # Step 2: Get chat history for context
            chat_history = await self.memory_manager.get_chat_memory(session_id)
            
            # Step 3: Generate response with context
            if context_chunks:
                response = await self.generate_response(
                    query, context_chunks, chat_history
                )
            else:
                # Fallback response when no relevant documents found
                response = await self._generate_fallback_response(query, chat_history)
                logger.warning("No relevant documents found, using fallback response")
            
            # Step 4: Store the conversation turn
            await self.memory_manager.store_chat_turn(
                session_id=session_id,
                user_message=query,
                ai_response=response,
                metadata={
                    'retrieved_chunks': len(context_chunks),
                    'similarity_scores': [
                        chunk.metadata.get('similarity_score', 0.0) 
                        for chunk in context_chunks
                    ] if context_chunks else []
                }
            )
            
            logger.info(f"Successfully processed query for session {session_id[:8]}...")
            return response, context_chunks
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            raise
    
    def _build_context_string(self, chunks: List[VectorChunk]) -> str:
        """
        Build context string from retrieved chunks with source information.
        
        Args:
            chunks: Retrieved document chunks
            
        Returns:
            Formatted context string with sources
        """
        if not chunks:
            return "No relevant documents found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            # Get document filename from metadata or use doc_id
            source = chunk.metadata.get('filename', f"Document {chunk.doc_id}")
            similarity = chunk.metadata.get('similarity_score', 0.0)
            
            context_part = f"[Source {i}: {source} (Similarity: {similarity:.3f})]\n{chunk.content}\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _build_conversation_messages(
        self,
        query: str,
        context_text: str,
        chat_history: List[ChatMessage]
    ) -> List[Dict[str, str]]:
        """
        Build conversation messages for OpenAI API.
        
        Args:
            query: Current user query
            context_text: Retrieved context information
            chat_history: Previous conversation messages
            
        Returns:
            List of message dictionaries for OpenAI API
        """
        messages = []
        
        # System message with instructions
        system_prompt = self._get_system_prompt()
        messages.append({"role": "system", "content": system_prompt})
        
        # Add chat history (limited to recent messages)
        for msg in chat_history[-10:]:  # Keep last 10 messages for context
            # Add user message
            messages.append({
                "role": "user",
                "content": msg.user_message
            })
            # Add assistant response
            messages.append({
                "role": "assistant", 
                "content": msg.ai_response
            })
        
        # Add current query with context
        user_message = f"""Context Information:
{context_text}

User Question: {query}

Please provide a helpful answer based on the context information above. Include specific citations using [Source X] format when referencing information from the context."""
        
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are a helpful AI assistant that answers questions based on provided context documents. 

IMPORTANT INSTRUCTIONS:
1. Base your answers primarily on the provided context information
2. Always cite your sources using [Source X] format when referencing specific information
3. If the context doesn't contain enough information to fully answer the question, say so clearly
4. Be concise but comprehensive in your responses
5. If you're unsure about something, express that uncertainty
6. For questions not covered in the context, you may use your general knowledge but clearly distinguish this

CITATION FORMAT:
- Use [Source 1], [Source 2], etc. to reference the numbered sources in the context
- Place citations immediately after the relevant information
- Multiple sources can be cited like [Source 1, 2]

RESPONSE STRUCTURE:
- Provide a direct answer to the question
- Support your answer with relevant details from the context
- Include proper citations throughout
- End with a brief summary if the response is long"""
    
    async def _generate_fallback_response(
        self,
        query: str,
        chat_history: List[ChatMessage]
    ) -> str:
        """
        Generate fallback response when no relevant documents are found.
        
        Args:
            query: User's question
            chat_history: Previous conversation messages
            
        Returns:
            Fallback response
        """
        messages = []
        
        # System message for fallback
        fallback_prompt = """You are a helpful AI assistant. The user has asked a question but no relevant documents were found in the knowledge base. 

Provide a helpful response that:
1. Acknowledges that no specific documents were found for their question
2. Offers general guidance or information if appropriate
3. Suggests how they might rephrase their question or what related topics might be available
4. Remains helpful and encouraging"""
        
        messages.append({"role": "system", "content": fallback_prompt})
        
        # Add recent chat history for context
        for msg in chat_history[-5:]:
            # Add user message
            messages.append({
                "role": "user",
                "content": msg.user_message
            })
            # Add assistant response
            messages.append({
                "role": "assistant",
                "content": msg.ai_response
            })
        
        # Add current query
        messages.append({
            "role": "user", 
            "content": f"I couldn't find relevant documents for this question: {query}"
        })
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )
            
            fallback_response = response.choices[0].message.content
            
            if not fallback_response or not fallback_response.strip():
                return "I'm sorry, I couldn't generate a response."
            
            return fallback_response
            
        except Exception as e:
            logger.error(f"Failed to generate fallback response: {e}")
            return "I'm sorry, I couldn't find relevant information for your question and encountered an error generating a response."
    
    def parse_citations(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse citations from response text.
        
        Args:
            response_text: Generated response with citations
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        # Find all [Source X] patterns
        citation_pattern = r'\[Source\s+(\d+(?:,\s*\d+)*)\]'
        matches = re.finditer(citation_pattern, response_text, re.IGNORECASE)
        
        for match in matches:
            source_numbers = [int(x.strip()) for x in match.group(1).split(',')]
            citations.append({
                'text': match.group(0),
                'position': match.span(),
                'source_numbers': source_numbers
            })
        
        return citations
    
    def format_response_with_sources(
        self,
        response_text: str,
        source_chunks: List[VectorChunk]
    ) -> Dict[str, Any]:
        """
        Format response with source information and citations.
        
        Args:
            response_text: Generated response text
            source_chunks: Source document chunks
            
        Returns:
            Formatted response dictionary
        """
        citations = self.parse_citations(response_text)
        
        # Build source information
        sources = []
        for i, chunk in enumerate(source_chunks, 1):
            source_info = {
                'number': i,
                'filename': chunk.metadata.get('filename', f"Document {chunk.doc_id}"),
                'content_preview': chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                'similarity_score': chunk.metadata.get('similarity_score', 0.0),
                'chunk_id': chunk.chunk_id,
                'doc_id': str(chunk.doc_id)
            }
            sources.append(source_info)
        
        return {
            'response': response_text,
            'citations': citations,
            'sources': sources,
            'source_count': len(source_chunks)
        }


# Global chat orchestrator instance
_chat_orchestrator: Optional[ChatOrchestrator] = None


def get_chat_orchestrator() -> ChatOrchestrator:
    """Get or create global ChatOrchestrator instance."""
    global _chat_orchestrator
    if _chat_orchestrator is None:
        _chat_orchestrator = ChatOrchestrator()
    return _chat_orchestrator


# Convenience functions for backward compatibility
async def generate_response(
    query: str,
    context_chunks: List[VectorChunk],
    chat_history: List[ChatMessage]
) -> str:
    """Generate LLM response with context."""
    orchestrator = get_chat_orchestrator()
    return await orchestrator.generate_response(query, context_chunks, chat_history)


async def process_query(
    query: str,
    session_id: str,
    top_k: int = 4,
    similarity_threshold: float = 0.7
) -> Tuple[str, List[VectorChunk]]:
    """Process complete query workflow."""
    orchestrator = get_chat_orchestrator()
    return await orchestrator.process_query(query, session_id, top_k, similarity_threshold)
