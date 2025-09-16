#!/usr/bin/env python3
"""
Phase 2B: Query and Retrieval System Demo

This script demonstrates the complete query processing and retrieval system
for the RAG AI Agent, showcasing vector search, LLM response generation,
and chat memory management.

Usage:
    python phase2b_demo.py

Author: RAG AI Agent Team
Date: 2024-12-19
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.chat import get_chat_orchestrator
from src.query import get_query_processor  
from src.memory import get_memory_manager
from src.config import get_settings


async def demo_query_processing():
    """Demonstrate the complete query processing workflow."""
    print("🚀 Phase 2B: Query and Retrieval System Demo")
    print("=" * 60)
    
    try:
        # Initialize components
        config = get_settings()
        chat_orchestrator = get_chat_orchestrator()
        query_processor = get_query_processor()
        memory_manager = get_memory_manager()
        
        print("✅ Initialized all Phase 2B components")
        print(f"📋 Configuration loaded: OpenAI API key {'✓' if config.openai_api_key else '✗'}")
        print()
        
        # Generate a unique session ID for this demo
        session_id = f"demo-session-{uuid.uuid4().hex[:8]}"
        print(f"🔑 Demo session ID: {session_id}")
        print()
        
        # Demo queries to test the system
        demo_queries = [
            "What is machine learning and how does it work?",
            "Can you explain the difference between supervised and unsupervised learning?",
            "What are some practical applications of AI in healthcare?",
            "How do neural networks process information?"
        ]
        
        print("📝 Demo Queries:")
        for i, query in enumerate(demo_queries, 1):
            print(f"  {i}. {query}")
        print()
        
        # Process each query
        for i, query in enumerate(demo_queries, 1):
            print(f"🔍 Processing Query {i}: {query}")
            print("-" * 50)
            
            try:
                # Process the complete query workflow
                response, context_chunks = await chat_orchestrator.process_query(
                    query=query,
                    session_id=session_id,
                    top_k=4,
                    similarity_threshold=0.7
                )
                
                print(f"📊 Retrieved {len(context_chunks)} relevant document chunks")
                
                if context_chunks:
                    print("📄 Source Documents:")
                    for j, chunk in enumerate(context_chunks, 1):
                        filename = chunk.metadata.get('filename', 'Unknown')
                        similarity = chunk.metadata.get('similarity_score', 0.0)
                        preview = chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content
                        print(f"  [{j}] {filename} (similarity: {similarity:.3f})")
                        print(f"      Preview: {preview}")
                    print()
                
                print("🤖 AI Response:")
                print(response)
                print()
                
                # Format response with sources for display
                formatted = chat_orchestrator.format_response_with_sources(response, context_chunks)
                
                if formatted['citations']:
                    print("📚 Citations Found:")
                    for citation in formatted['citations']:
                        print(f"  - {citation['text']} (sources: {citation['source_numbers']})")
                    print()
                
            except Exception as e:
                print(f"❌ Error processing query: {e}")
                print()
                continue
            
            print("=" * 60)
            print()
        
        # Demonstrate chat memory
        print("💾 Chat Memory Demonstration")
        print("-" * 30)
        
        try:
            chat_history = await memory_manager.get_chat_memory(session_id)
            print(f"📋 Retrieved {len(chat_history)} messages from chat history")
            
            print("💬 Conversation History:")
            for msg in chat_history[-6:]:  # Show last 6 messages
                role_emoji = "👤" if msg.role == "user" else "🤖"
                content_preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                print(f"  {role_emoji} {msg.role}: {content_preview}")
            print()
            
        except Exception as e:
            print(f"❌ Error retrieving chat memory: {e}")
            print()
        
        # Test vector search directly
        print("🔍 Direct Vector Search Demonstration")
        print("-" * 40)
        
        try:
            test_query = "artificial intelligence applications"
            print(f"🔍 Searching for: '{test_query}'")
            
            # Generate embedding
            embedding = await query_processor.embed_query(test_query)
            print(f"✅ Generated embedding: {len(embedding)} dimensions")
            
            # Perform vector search
            search_results = await query_processor.vector_search(
                embedding, top_k=3, similarity_threshold=0.6
            )
            
            print(f"📊 Vector search results: {len(search_results)} chunks found")
            for i, chunk in enumerate(search_results, 1):
                similarity = chunk.metadata.get('similarity_score', 0.0)
                filename = chunk.metadata.get('filename', 'Unknown')
                print(f"  [{i}] {filename} - Similarity: {similarity:.3f}")
            print()
            
        except Exception as e:
            print(f"❌ Error in vector search: {e}")
            print()
        
        print("🏁 Phase 2B Demo Completed Successfully!")
        print("=" * 60)
        
        # Cleanup demo session
        try:
            await memory_manager.clear_session_memory(session_id)
            print(f"🧹 Cleaned up demo session: {session_id}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up session: {e}")
            
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


async def demo_individual_components():
    """Demonstrate individual Phase 2B components."""
    print("\n🧪 Individual Component Testing")
    print("=" * 40)
    
    # Test Query Processor
    print("1️⃣ Testing Query Processor...")
    try:
        query_processor = get_query_processor()
        test_embedding = await query_processor.embed_query("test query")
        print(f"   ✅ Embedding generation: {len(test_embedding)} dimensions")
    except Exception as e:
        print(f"   ❌ Query processor error: {e}")
    
    # Test Memory Manager
    print("2️⃣ Testing Memory Manager...")
    try:
        memory_manager = get_memory_manager()
        test_session = "test-session-123"
        await memory_manager.store_user_message(test_session, "Test message", {})
        await memory_manager.store_ai_response(test_session, "Test response", {})
        history = await memory_manager.get_chat_memory(test_session)
        print(f"   ✅ Memory operations: {len(history)} messages stored/retrieved")
        await memory_manager.clear_session_memory(test_session)
        print("   ✅ Session cleanup successful")
    except Exception as e:
        print(f"   ❌ Memory manager error: {e}")
    
    # Test Chat Orchestrator
    print("3️⃣ Testing Chat Orchestrator...")
    try:
        chat_orchestrator = get_chat_orchestrator()
        citations = chat_orchestrator.parse_citations("Test [Source 1] and [Source 2, 3].")
        print(f"   ✅ Citation parsing: {len(citations)} citations found")
        
        context_string = chat_orchestrator._build_context_string([])
        print(f"   ✅ Context building: '{context_string[:50]}...'")
    except Exception as e:
        print(f"   ❌ Chat orchestrator error: {e}")
    
    print("\n🎯 Component testing completed!")


def print_phase2b_info():
    """Print information about Phase 2B implementation."""
    print("\n📋 Phase 2B: Query and Retrieval System")
    print("=" * 50)
    print("🎯 Features Implemented:")
    print("  • Query embedding generation with OpenAI")
    print("  • Vector similarity search in Supabase")
    print("  • LLM response generation with context")
    print("  • Citation parsing and formatting")
    print("  • Rolling chat memory management")
    print("  • Complete query-to-response workflow")
    print()
    print("🏗️ Architecture:")
    print("  • src/query.py - Vector search and retrieval")
    print("  • src/chat.py - LLM orchestration and formatting")
    print("  • src/memory.py - Chat memory management")
    print("  • Comprehensive test suite with mocks")
    print()
    print("🔧 Key Components:")
    print("  • QueryProcessor - Handles embeddings and search")
    print("  • ChatOrchestrator - Manages LLM interactions") 
    print("  • ChatMemoryManager - Stores conversation history")
    print()


def main():
    """Main demo function."""
    print_phase2b_info()
    
    # Check if we have environment configuration
    try:
        config = get_settings()
        if not config.openai_api_key:
            print("⚠️ Warning: OPENAI_API_KEY not found in environment")
            print("   Set up your .env file with API credentials to run the full demo")
            print()
    except Exception as e:
        print(f"⚠️ Configuration error: {e}")
        print("   Make sure your .env file is properly configured")
        print()
    
    # Run the demos
    asyncio.run(demo_individual_components())
    
    try:
        asyncio.run(demo_query_processing())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")


if __name__ == "__main__":
    main()
