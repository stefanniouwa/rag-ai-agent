"""Tests for database client and operations."""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from src.db import SupabaseClient, get_db_client, init_db_client
from src.models import Document, VectorChunk, ChatMessage


class TestSupabaseClient:
    """Test cases for SupabaseClient."""
    
    def test_init_client(self, mock_supabase_client):
        """Test client initialization."""
        with patch('src.db.create_client', return_value=mock_supabase_client):
            client = SupabaseClient()
            assert client.client is not None
            assert client.admin_client is not None
    
    def test_test_connection_success(self, mock_db_client):
        """Test successful database connection."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = []
        mock_db_client.client.table.return_value.select.return_value.execute.return_value = mock_response
        
        result = mock_db_client.test_connection()
        assert result is True
    
    def test_test_connection_failure(self, mock_db_client):
        """Test failed database connection."""
        # Mock exception
        mock_db_client.client.table.return_value.select.return_value.execute.side_effect = Exception("Connection failed")
        
        result = mock_db_client.test_connection()
        assert result is False


class TestDocumentOperations:
    """Test cases for document CRUD operations."""
    
    def test_create_document(self, mock_db_client, sample_document):
        """Test document creation."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_document.id),
            "filename": sample_document.filename,
            "uploaded_at": sample_document.uploaded_at
        }]
        mock_db_client.client.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = mock_db_client.create_document(sample_document.filename)
        
        assert isinstance(result, Document)
        assert result.filename == sample_document.filename
        mock_db_client.client.table.assert_called_with("documents")
    
    def test_get_document(self, mock_db_client, sample_document):
        """Test document retrieval."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_document.id),
            "filename": sample_document.filename,
            "uploaded_at": sample_document.uploaded_at
        }]
        mock_db_client.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = mock_db_client.get_document(sample_document.id)
        
        assert isinstance(result, Document)
        assert result.id == sample_document.id
        assert result.filename == sample_document.filename
    
    def test_get_document_not_found(self, mock_db_client):
        """Test document retrieval when document doesn't exist."""
        # Mock empty response
        mock_response = Mock()
        mock_response.data = []
        mock_db_client.client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = mock_db_client.get_document(uuid4())
        assert result is None
    
    def test_list_documents(self, mock_db_client, sample_document):
        """Test listing all documents."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_document.id),
            "filename": sample_document.filename,
            "uploaded_at": sample_document.uploaded_at
        }]
        mock_db_client.client.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response
        
        result = mock_db_client.list_documents()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], Document)
        assert result[0].filename == sample_document.filename
    
    def test_delete_document(self, mock_db_client, sample_document):
        """Test document deletion."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = []
        mock_db_client.client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        
        result = mock_db_client.delete_document(sample_document.id)
        assert result is True
        mock_db_client.client.table.assert_called_with("documents")


class TestVectorOperations:
    """Test cases for vector operations."""
    
    def test_insert_vectors(self, mock_db_client, sample_vectors_list):
        """Test vector insertion."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = []
        mock_db_client.client.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = mock_db_client.insert_vectors(sample_vectors_list)
        assert result is True
        mock_db_client.client.table.assert_called_with("vectors")
    
    def test_vector_search(self, mock_db_client, sample_vector_chunk, test_query_embedding):
        """Test vector similarity search."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_vector_chunk.id),
            "doc_id": str(sample_vector_chunk.doc_id),
            "chunk_id": sample_vector_chunk.chunk_id,
            "content": sample_vector_chunk.content,
            "embedding": sample_vector_chunk.embedding,
            "metadata": sample_vector_chunk.metadata
        }]
        mock_db_client.client.rpc.return_value.execute.return_value = mock_response
        
        result = mock_db_client.vector_search(test_query_embedding, top_k=4)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], VectorChunk)
        assert result[0].content == sample_vector_chunk.content
        mock_db_client.client.rpc.assert_called_with("vector_search", {
            "query_embedding": test_query_embedding,
            "match_count": 4
        })
    
    def test_get_document_vectors(self, mock_db_client, sample_vector_chunk):
        """Test getting vectors for a specific document."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_vector_chunk.id),
            "doc_id": str(sample_vector_chunk.doc_id),
            "chunk_id": sample_vector_chunk.chunk_id,
            "content": sample_vector_chunk.content,
            "embedding": sample_vector_chunk.embedding,
            "metadata": sample_vector_chunk.metadata
        }]
        mock_db_client.client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
        
        result = mock_db_client.get_document_vectors(sample_vector_chunk.doc_id)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], VectorChunk)
        assert result[0].doc_id == sample_vector_chunk.doc_id


class TestChatOperations:
    """Test cases for chat history operations."""
    
    def test_store_chat_message(self, mock_db_client, sample_chat_message):
        """Test storing a chat message."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_chat_message.id),
            "session_id": sample_chat_message.session_id,
            "turn_index": sample_chat_message.turn_index,
            "user_message": sample_chat_message.user_message,
            "ai_response": sample_chat_message.ai_response,
            "created_at": sample_chat_message.created_at
        }]
        mock_db_client.client.table.return_value.insert.return_value.execute.return_value = mock_response
        
        result = mock_db_client.store_chat_message(sample_chat_message)
        
        assert isinstance(result, ChatMessage)
        assert result.session_id == sample_chat_message.session_id
        assert result.user_message == sample_chat_message.user_message
        mock_db_client.client.table.assert_called_with("chat_histories")
    
    def test_get_chat_history(self, mock_db_client, sample_chat_message):
        """Test retrieving chat history."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = [{
            "id": str(sample_chat_message.id),
            "session_id": sample_chat_message.session_id,
            "turn_index": sample_chat_message.turn_index,
            "user_message": sample_chat_message.user_message,
            "ai_response": sample_chat_message.ai_response,
            "created_at": sample_chat_message.created_at
        }]
        mock_db_client.client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        
        result = mock_db_client.get_chat_history(sample_chat_message.session_id, limit=5)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ChatMessage)
        assert result[0].session_id == sample_chat_message.session_id
    
    def test_clear_chat_history(self, mock_db_client, test_session_id):
        """Test clearing chat history."""
        # Mock successful response
        mock_response = Mock()
        mock_response.data = []
        mock_db_client.client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_response
        
        result = mock_db_client.clear_chat_history(test_session_id)
        assert result is True
        mock_db_client.client.table.assert_called_with("chat_histories")


class TestGlobalClientFunctions:
    """Test cases for global client management functions."""
    
    def test_get_db_client(self):
        """Test getting global database client."""
        with patch('src.db.SupabaseClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            client1 = get_db_client()
            client2 = get_db_client()
            
            # Should return the same instance
            assert client1 is client2
            # Should only create one instance
            assert mock_client_class.call_count == 1
    
    def test_init_db_client_success(self, mock_supabase_client):
        """Test successful database client initialization."""
        with patch('src.db.create_client', return_value=mock_supabase_client):
            with patch('src.db.SupabaseClient.test_connection', return_value=True):
                client = init_db_client()
                assert client is not None
    
    def test_init_db_client_failure(self, mock_supabase_client):
        """Test failed database client initialization."""
        with patch('src.db.create_client', return_value=mock_supabase_client):
            with patch('src.db.SupabaseClient.test_connection', return_value=False):
                with pytest.raises(ConnectionError):
                    init_db_client()


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations.
    
    Note: These tests require a real database connection and should be
    run with appropriate test database configuration.
    """
    
    @pytest.mark.integration
    def test_real_database_connection(self):
        """Test actual database connection (requires real credentials)."""
        from src.db import SupabaseClient
        
        client = SupabaseClient()
        
        # Test connection
        assert client.test_connection() == True
        
        # Test basic table access
        result = client.client.table("documents").select("*").limit(1).execute()
        assert result is not None
    
    @pytest.mark.integration 
    def test_full_document_workflow(self):
        """Test complete document workflow with real database."""
        from src.db import SupabaseClient
        from src.models import VectorChunk
        import uuid
        
        client = SupabaseClient()
        
        # 1. Create document
        doc = client.create_document("test_integration_doc.pdf")
        assert doc is not None
        assert doc.filename == "test_integration_doc.pdf"
        
        try:
            # 2. Insert vectors
            vector_data = VectorChunk(
                id=uuid.uuid4(),  # Will be ignored by database
                doc_id=doc.id,
                chunk_id=0,
                content="This is test content for integration testing",
                embedding=[0.1] * 1536,  # Mock embedding of correct dimension
                metadata={"test": True}
            )
            success = client.insert_vectors([vector_data])
            assert success == True
            
            # 3. Search vectors
            search_results = client.vector_search([0.1] * 1536, top_k=5)
            assert len(search_results) >= 1
            found_our_vector = any(v.content == "This is test content for integration testing" 
                                 for v in search_results)
            assert found_our_vector
            
            # 4. Get document vectors
            doc_vectors = client.get_document_vectors(doc.id)
            assert len(doc_vectors) >= 1
            assert doc_vectors[0].content == "This is test content for integration testing"
            
        finally:
            # Clean up: Delete document (should cascade to vectors)
            success = client.delete_document(doc.id)
            assert success == True


class TestErrorHandling:
    """Test error handling in database operations."""

    def test_create_document_no_data_returned(self, mock_supabase_client):
        """Test create_document when no data is returned."""
        # Mock empty result
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        
        client = SupabaseClient()
        client.client = mock_supabase_client  # Replace the real client with mock
        
        with pytest.raises(ValueError, match="Failed to create document: no data returned"):
            client.create_document("test.pdf")

    def test_store_chat_message_no_data_returned(self, mock_supabase_client):
        """Test store_chat_message when no data is returned."""
        from src.models import ChatMessage
        
        # Mock empty result  
        mock_response = Mock()
        mock_response.data = []
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_response
        
        client = SupabaseClient()
        client.client = mock_supabase_client  # Replace the real client with mock
        
        message = ChatMessage(
            session_id="test",
            turn_index=0,
            user_message="test user",
            ai_response="test ai"
        )
        
        with pytest.raises(ValueError, match="Failed to store chat message: no data returned"):
            client.store_chat_message(message)

    def test_create_document_exception(self, mock_supabase_client):
        """Test create_document exception handling."""
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.create_document("test.pdf")

    def test_get_document_exception(self, mock_supabase_client):
        """Test get_document exception handling."""
        from uuid import uuid4
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.get_document(uuid4())

    def test_list_documents_exception(self, mock_supabase_client):
        """Test list_documents exception handling."""
        mock_supabase_client.table.return_value.select.return_value.order.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.list_documents()

    def test_delete_document_exception(self, mock_supabase_client):
        """Test delete_document exception handling."""
        from uuid import uuid4
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.delete_document(uuid4())

    def test_insert_vectors_exception(self, mock_supabase_client):
        """Test insert_vectors exception handling."""
        from src.models import VectorChunk
        from uuid import uuid4
        
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        vector = VectorChunk(
            id=uuid4(),
            doc_id=uuid4(),
            chunk_id=0,
            content="test",
            embedding=[0.1] * 1536
        )
        
        with pytest.raises(Exception, match="Database error"):
            client.insert_vectors([vector])

    def test_vector_search_exception(self, mock_supabase_client):
        """Test vector_search exception handling."""
        mock_supabase_client.rpc.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.vector_search([0.1] * 1536)

    def test_get_document_vectors_exception(self, mock_supabase_client):
        """Test get_document_vectors exception handling."""
        from uuid import uuid4
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.get_document_vectors(uuid4())

    def test_store_chat_message_exception(self, mock_supabase_client):
        """Test store_chat_message exception handling."""
        from src.models import ChatMessage
        
        mock_supabase_client.table.return_value.insert.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        message = ChatMessage(
            session_id="test",
            turn_index=0,
            user_message="test user",
            ai_response="test ai"
        )
        
        with pytest.raises(Exception, match="Database error"):
            client.store_chat_message(message)

    def test_get_chat_history_exception(self, mock_supabase_client):
        """Test get_chat_history exception handling."""
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.get_chat_history("test_session")

    def test_clear_chat_history_exception(self, mock_supabase_client):
        """Test clear_chat_history exception handling."""
        mock_supabase_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("Database error")
        
        client = SupabaseClient()
        
        with pytest.raises(Exception, match="Database error"):
            client.clear_chat_history("test_session")
