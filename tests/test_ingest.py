"""Unit tests for document ingestion pipeline."""

import pytest
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import Mock, patch, MagicMock

from src.ingest import DocumentIngestionPipeline, ingest_document, validate_document_file
from src.models import ConversionResult, Document, VectorChunk


class TestDocumentIngestionPipeline:
    """Test cases for DocumentIngestionPipeline."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock components for testing."""
        with patch('src.ingest.DoclingConverterWrapper') as mock_converter:
            with patch('src.ingest.DoclingChunkerWrapper') as mock_chunker:
                with patch('src.ingest.EmbeddingGenerator') as mock_embedder:
                    with patch('src.ingest.get_db_client') as mock_db:
                        yield {
                            'converter': mock_converter.return_value,
                            'chunker': mock_chunker.return_value,
                            'embedder': mock_embedder.return_value,
                            'db': mock_db.return_value
                        }
    
    @pytest.fixture
    def mock_docling_document(self):
        """Create a mock DoclingDocument."""
        mock_doc = Mock()
        mock_doc.pages = [Mock()]
        return mock_doc
    
    @pytest.fixture
    def mock_docling_chunks(self):
        """Create mock DoclingChunk objects."""
        chunks = []
        for i in range(3):
            chunk = Mock()
            chunk.text = f"This is chunk {i} with sufficient content for testing."
            chunk.meta = Mock()
            chunk.meta.export_json_dict.return_value = {
                'page_number': 1,
                'section': f'section_{i}'
            }
            chunks.append(chunk)
        return chunks
    
    @pytest.fixture
    def mock_document_record(self):
        """Create a mock Document record."""
        return Document(
            id=uuid4(),
            filename="test.pdf",
            uploaded_at="2024-01-01T00:00:00Z"
        )
    
    def test_initialization_default(self, mock_components):
        """Test pipeline initialization with default parameters."""
        pipeline = DocumentIngestionPipeline()
        
        assert pipeline.tokenizer_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert pipeline.embedding_model == "text-embedding-3-small"
        assert pipeline.batch_size == 10
        assert pipeline.converter is not None
        assert pipeline.chunker is not None
        assert pipeline.embedder is not None
        assert pipeline.db is not None
    
    def test_initialization_custom(self, mock_components):
        """Test pipeline initialization with custom parameters."""
        pipeline = DocumentIngestionPipeline(
            tokenizer_model="custom-tokenizer",
            embedding_model="custom-embedder",
            max_tokens=256,
            batch_size=5
        )
        
        assert pipeline.tokenizer_model == "custom-tokenizer"
        assert pipeline.embedding_model == "custom-embedder"
        assert pipeline.max_tokens == 256
        assert pipeline.batch_size == 5
    
    def test_ingest_document_success(
        self, 
        mock_components, 
        mock_docling_document, 
        mock_docling_chunks, 
        mock_document_record
    ):
        """Test successful document ingestion workflow."""
        # Setup mocks
        mock_components['converter'].convert_document.return_value = mock_docling_document
        mock_components['converter'].validate_document.return_value = True
        mock_components['chunker'].chunk_document.return_value = mock_docling_chunks
        mock_components['chunker'].contextualize_chunk.side_effect = lambda chunk: chunk.text
        mock_components['chunker'].get_chunk_metadata.return_value = {'test': 'metadata'}
        mock_components['embedder'].generate_embeddings.return_value = [[0.1] * 1536] * 3
        mock_components['db'].create_document.return_value = mock_document_record
        mock_components['db'].insert_vectors.return_value = True
        
        # Create temporary test file
        test_file = "test.pdf"
        
        with patch('os.path.exists', return_value=True):
            with patch('pathlib.Path.name', "test.pdf"):
                pipeline = DocumentIngestionPipeline()
                result = pipeline.ingest_document(test_file)
        
        assert isinstance(result, ConversionResult)
        assert result.conversion_status == "success"
        assert result.chunks_created == 3
        assert result.filename == "test.pdf"
        
        # Verify all components were called
        mock_components['converter'].convert_document.assert_called_once()
        mock_components['chunker'].chunk_document.assert_called_once()
        mock_components['embedder'].generate_embeddings.assert_called_once()
        mock_components['db'].create_document.assert_called_once()
        mock_components['db'].insert_vectors.assert_called_once()
    
    def test_ingest_document_file_not_exists(self, mock_components):
        """Test ingestion with non-existent file."""
        pipeline = DocumentIngestionPipeline()
        
        with patch('os.path.exists', return_value=False):
            result = pipeline.ingest_document("nonexistent.pdf")
        
        assert result.conversion_status == "failed"
        assert "does not exist" in result.error_message
        assert result.chunks_created == 0
    
    def test_ingest_document_conversion_failure(self, mock_components):
        """Test ingestion with document conversion failure."""
        mock_components['converter'].convert_document.return_value = None
        
        with patch('os.path.exists', return_value=True):
            pipeline = DocumentIngestionPipeline()
            result = pipeline.ingest_document("test.pdf")
        
        assert result.conversion_status == "failed"
        assert "conversion failed" in result.error_message.lower()
    
    def test_ingest_document_validation_failure(self, mock_components, mock_docling_document):
        """Test ingestion with document validation failure."""
        mock_components['converter'].convert_document.return_value = mock_docling_document
        mock_components['converter'].validate_document.return_value = False
        
        with patch('os.path.exists', return_value=True):
            pipeline = DocumentIngestionPipeline()
            result = pipeline.ingest_document("test.pdf")
        
        assert result.conversion_status == "failed"
        assert "validation failed" in result.error_message.lower()
    
    def test_ingest_document_chunking_failure(
        self, 
        mock_components, 
        mock_docling_document, 
        mock_document_record
    ):
        """Test ingestion with chunking failure and cleanup."""
        mock_components['converter'].convert_document.return_value = mock_docling_document
        mock_components['converter'].validate_document.return_value = True
        mock_components['db'].create_document.return_value = mock_document_record
        mock_components['chunker'].chunk_document.return_value = []  # No chunks produced
        
        with patch('os.path.exists', return_value=True):
            pipeline = DocumentIngestionPipeline()
            result = pipeline.ingest_document("test.pdf")
        
        assert result.conversion_status == "failed"
        assert "no chunks" in result.error_message.lower()
        
        # Verify cleanup was attempted
        mock_components['db'].delete_document.assert_called_once_with(mock_document_record.id)
    
    def test_process_and_store_chunks_success(
        self, 
        mock_components, 
        mock_docling_chunks, 
        mock_document_record
    ):
        """Test successful chunk processing and storage."""
        mock_components['chunker'].contextualize_chunk.side_effect = lambda chunk: chunk.text
        mock_components['chunker'].get_chunk_metadata.return_value = {'test': 'metadata'}
        mock_components['embedder'].generate_embeddings.return_value = [[0.1] * 1536] * 3
        mock_components['db'].insert_vectors.return_value = True
        
        pipeline = DocumentIngestionPipeline()
        stored_count = pipeline._process_and_store_chunks(mock_document_record.id, mock_docling_chunks)
        
        assert stored_count == 3
        mock_components['embedder'].generate_embeddings.assert_called_once()
        mock_components['db'].insert_vectors.assert_called_once()
    
    def test_process_and_store_chunks_batch_processing(
        self, 
        mock_components, 
        mock_document_record
    ):
        """Test chunk processing with multiple batches."""
        # Create 25 chunks to test batch processing (batch_size=10)
        large_chunk_list = []
        for i in range(25):
            chunk = Mock()
            chunk.text = f"Chunk {i} content"
            large_chunk_list.append(chunk)
        
        mock_components['chunker'].contextualize_chunk.side_effect = lambda chunk: chunk.text
        mock_components['chunker'].get_chunk_metadata.return_value = {'test': 'metadata'}
        mock_components['embedder'].generate_embeddings.side_effect = [
            [[0.1] * 1536] * 10,  # Batch 1: 10 chunks
            [[0.2] * 1536] * 10,  # Batch 2: 10 chunks
            [[0.3] * 1536] * 5,   # Batch 3: 5 chunks
        ]
        mock_components['db'].insert_vectors.return_value = True
        
        pipeline = DocumentIngestionPipeline(batch_size=10)
        stored_count = pipeline._process_and_store_chunks(mock_document_record.id, large_chunk_list)
        
        assert stored_count == 25
        assert mock_components['embedder'].generate_embeddings.call_count == 3
        assert mock_components['db'].insert_vectors.call_count == 3
    
    def test_process_and_store_chunks_batch_failure_continues(
        self, 
        mock_components, 
        mock_docling_chunks, 
        mock_document_record
    ):
        """Test that batch failure doesn't stop processing of other batches."""
        mock_components['chunker'].contextualize_chunk.side_effect = lambda chunk: chunk.text
        mock_components['chunker'].get_chunk_metadata.return_value = {'test': 'metadata'}
        # First batch fails, second succeeds
        mock_components['embedder'].generate_embeddings.side_effect = [
            Exception("Embedding failed"),
            [[0.1] * 1536] * 2
        ]
        mock_components['db'].insert_vectors.return_value = True
        
        # Use small batch size to create multiple batches
        pipeline = DocumentIngestionPipeline(batch_size=2)
        stored_count = pipeline._process_and_store_chunks(mock_document_record.id, mock_docling_chunks)
        
        # Should have processed second batch successfully (1 chunk after first batch failed)
        assert stored_count == 1
        assert mock_components['embedder'].generate_embeddings.call_count == 2
        assert mock_components['db'].insert_vectors.call_count == 1
    
    def test_validate_file_success(self, mock_components):
        """Test successful file validation."""
        pipeline = DocumentIngestionPipeline()
        mock_components['converter'].get_supported_formats.return_value = ['.pdf', '.docx']
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                with patch('pathlib.Path.suffix', new_callable=lambda: '.pdf'):
                    with patch('builtins.open', mock_open=True):
                        mock_stat.return_value.st_size = 1024 * 1024  # 1MB
                        
                        is_valid, error = pipeline.validate_file("test.pdf")
        
        assert is_valid is True
        assert error is None
    
    def test_validate_file_not_exists(self, mock_components):
        """Test file validation with non-existent file."""
        pipeline = DocumentIngestionPipeline()
        
        with patch('pathlib.Path.exists', return_value=False):
            is_valid, error = pipeline.validate_file("nonexistent.pdf")
        
        assert is_valid is False
        assert "does not exist" in error
    
    def test_validate_file_too_large(self, mock_components):
        """Test file validation with oversized file."""
        pipeline = DocumentIngestionPipeline()
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB (exceeds default 50MB limit)
                
                is_valid, error = pipeline.validate_file("large.pdf")
        
        assert is_valid is False
        assert "exceeds limit" in error
    
    def test_validate_file_unsupported_format(self, mock_components):
        """Test file validation with unsupported format."""
        pipeline = DocumentIngestionPipeline()
        mock_components['converter'].get_supported_formats.return_value = ['.pdf', '.docx']
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                with patch('pathlib.Path.suffix', '.xyz'):
                    mock_stat.return_value.st_size = 1024
                    
                    is_valid, error = pipeline.validate_file("test.xyz")
        
        assert is_valid is False
        assert "Unsupported file format" in error
    
    def test_validate_file_permission_denied(self, mock_components):
        """Test file validation with permission denied."""
        pipeline = DocumentIngestionPipeline()
        mock_components['converter'].get_supported_formats.return_value = ['.pdf', '.docx']
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.stat') as mock_stat:
                with patch('pathlib.Path.suffix', new_callable=lambda: '.pdf'):
                    with patch('builtins.open', side_effect=PermissionError("Access denied")):
                        mock_stat.return_value.st_size = 1024
                        
                        is_valid, error = pipeline.validate_file("restricted.pdf")
        
        assert is_valid is False
        assert "Permission denied" in error
    
    def test_get_pipeline_info(self, mock_components):
        """Test getting pipeline information."""
        mock_components['converter'].get_supported_formats.return_value = ['.pdf', '.docx']
        mock_components['embedder'].get_embedding_dimension.return_value = 1536
        mock_components['chunker'].get_chunker_config.return_value = {'test': 'config'}
        
        pipeline = DocumentIngestionPipeline(
            tokenizer_model="test-tokenizer",
            embedding_model="test-embedder",
            max_tokens=256,
            batch_size=5
        )
        
        info = pipeline.get_pipeline_info()
        
        assert info['tokenizer_model'] == "test-tokenizer"
        assert info['embedding_model'] == "test-embedder"
        assert info['max_tokens'] == 256
        assert info['batch_size'] == 5
        assert info['supported_formats'] == ['.pdf', '.docx']
        assert info['embedding_dimension'] == 1536
        assert info['chunker_config'] == {'test': 'config'}
    
    def test_test_pipeline_all_pass(self, mock_components):
        """Test pipeline testing with all components passing."""
        mock_components['db'].test_connection.return_value = True
        mock_components['embedder'].generate_embedding.return_value = [0.1] * 1536
        mock_components['embedder'].validate_embedding.return_value = True
        mock_components['chunker'].get_chunker_config.return_value = {'tokenizer_model': 'test'}
        mock_components['converter'].get_supported_formats.return_value = ['.pdf']
        
        pipeline = DocumentIngestionPipeline()
        results = pipeline.test_pipeline()
        
        assert results['database'] is True
        assert results['embeddings'] is True
        assert results['chunker'] is True
        assert results['converter'] is True
    
    def test_test_pipeline_some_fail(self, mock_components):
        """Test pipeline testing with some components failing."""
        mock_components['db'].test_connection.return_value = False
        mock_components['embedder'].generate_embedding.side_effect = Exception("Embedding error")
        mock_components['chunker'].get_chunker_config.return_value = {'tokenizer_model': 'test'}
        mock_components['converter'].get_supported_formats.return_value = ['.pdf']
        
        pipeline = DocumentIngestionPipeline()
        results = pipeline.test_pipeline()
        
        assert results['database'] is False
        assert results['embeddings'] is False
        assert results['chunker'] is True
        assert results['converter'] is True


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('src.ingest.DocumentIngestionPipeline')
    def test_ingest_document_function(self, mock_pipeline_class):
        """Test ingest_document convenience function."""
        mock_pipeline = Mock()
        mock_result = ConversionResult(
            doc_id=uuid4(),
            filename="test.pdf",
            chunks_created=5,
            conversion_status="success"
        )
        mock_pipeline.ingest_document.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline
        
        result = ingest_document("test.pdf", "custom_name.pdf")
        
        assert result == mock_result
        mock_pipeline.ingest_document.assert_called_once_with("test.pdf", "custom_name.pdf")
    
    @patch('src.ingest.DocumentIngestionPipeline')
    def test_validate_document_file_function(self, mock_pipeline_class):
        """Test validate_document_file convenience function."""
        mock_pipeline = Mock()
        mock_pipeline.validate_file.return_value = (True, None)
        mock_pipeline_class.return_value = mock_pipeline
        
        is_valid, error = validate_document_file("test.pdf")
        
        assert is_valid is True
        assert error is None
        mock_pipeline.validate_file.assert_called_once_with("test.pdf")


@pytest.mark.integration
class TestDocumentIngestionIntegration:
    """Integration tests for DocumentIngestionPipeline."""
    
    def test_full_pipeline_integration(self):
        """Test full pipeline with real components."""
        pytest.skip("Integration test - requires all dependencies installed")
    
    def test_real_document_ingestion(self):
        """Test ingestion with real document files."""
        pytest.skip("Integration test - requires test documents and database")
    
    def test_pipeline_performance(self):
        """Test pipeline performance with large documents."""
        pytest.skip("Integration test - requires performance testing setup")
    
    def test_database_integration(self):
        """Test integration with real Supabase database."""
        pytest.skip("Integration test - requires database credentials")
