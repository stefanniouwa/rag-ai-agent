"""Unit tests for Docling HybridChunker wrapper."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.docling_chunker import DoclingChunkerWrapper


class TestDoclingChunkerWrapper:
    """Test cases for DoclingChunkerWrapper."""
    
    @pytest.fixture
    def mock_tokenizer(self):
        """Create a mock tokenizer for testing."""
        mock_tokenizer = Mock()
        mock_tokenizer.count_tokens.return_value = 100
        return mock_tokenizer
    
    @pytest.fixture
    def mock_chunker(self):
        """Create a mock HybridChunker for testing."""
        mock_chunker = Mock()
        return mock_chunker
    
    @pytest.fixture
    def mock_docling_chunk(self):
        """Create a mock DoclingChunk for testing."""
        mock_chunk = Mock()
        mock_chunk.text = "This is a test chunk with sufficient content for validation."
        mock_chunk.meta = Mock()
        mock_chunk.meta.export_json_dict.return_value = {
            'page_number': 1,
            'section': 'introduction'
        }
        return mock_chunk
    
    @pytest.fixture
    def mock_docling_document(self):
        """Create a mock DoclingDocument for testing."""
        mock_doc = Mock()
        mock_doc.pages = [Mock()]
        return mock_doc
    
    @patch('src.docling_chunker.AutoTokenizer')
    @patch('src.docling_chunker.HuggingFaceTokenizer')
    @patch('src.docling_chunker.HybridChunker')
    def test_initialization_success(self, mock_hybrid_chunker, mock_hf_tokenizer, mock_auto_tokenizer):
        """Test successful initialization."""
        mock_auto_tokenizer.from_pretrained.return_value = Mock()
        mock_hf_tokenizer.return_value = Mock()
        mock_hybrid_chunker.return_value = Mock()
        
        chunker = DoclingChunkerWrapper(
            tokenizer_model="test-model",
            max_tokens=256,
            merge_peers=False
        )
        
        assert chunker.tokenizer_model == "test-model"
        assert chunker.max_tokens == 256
        assert chunker.merge_peers is False
        assert chunker.tokenizer is not None
        assert chunker.chunker is not None
    
    @patch('src.docling_chunker.AutoTokenizer')
    def test_initialization_tokenizer_failure_with_fallback(self, mock_auto_tokenizer):
        """Test initialization with tokenizer failure and successful fallback."""
        # First call fails, second call (fallback) succeeds
        mock_auto_tokenizer.from_pretrained.side_effect = [
            Exception("Model not found"),
            Mock()  # Fallback succeeds
        ]
        
        with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
            with patch('src.docling_chunker.HybridChunker') as mock_hybrid_chunker:
                mock_hf_tokenizer.return_value = Mock()
                mock_hybrid_chunker.return_value = Mock()
                
                chunker = DoclingChunkerWrapper(tokenizer_model="invalid-model")
                
                # Should have fallen back to default model
                assert chunker.tokenizer is not None
                assert chunker.chunker is not None
    
    @patch('src.docling_chunker.AutoTokenizer')
    def test_initialization_complete_failure(self, mock_auto_tokenizer):
        """Test initialization failure when both primary and fallback tokenizers fail."""
        mock_auto_tokenizer.from_pretrained.side_effect = Exception("All models failed")
        
        with pytest.raises(RuntimeError, match="Failed to initialize any tokenizer"):
            DoclingChunkerWrapper(tokenizer_model="invalid-model")
    
    def test_chunk_document_success(self, mock_docling_document, mock_docling_chunk):
        """Test successful document chunking."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker') as mock_hybrid_chunker:
                    # Setup mocks
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.return_value = 50
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    mock_chunker_instance = Mock()
                    mock_chunker_instance.chunk.return_value = [mock_docling_chunk]
                    mock_hybrid_chunker.return_value = mock_chunker_instance
                    
                    chunker = DoclingChunkerWrapper()
                    chunks = chunker.chunk_document(mock_docling_document)
                    
                    assert len(chunks) == 1
                    assert chunks[0] == mock_docling_chunk
    
    def test_chunk_document_none_input(self):
        """Test chunking with None document input."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker'):
                    chunker = DoclingChunkerWrapper()
                    
                    with pytest.raises(RuntimeError, match="Document chunking failed"):
                        chunker.chunk_document(None)
    
    def test_chunk_document_no_pages(self):
        """Test chunking with document that has no pages."""
        mock_doc = Mock()
        mock_doc.pages = []
        
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker'):
                    chunker = DoclingChunkerWrapper()
                    
                    with pytest.raises(RuntimeError, match="Document chunking failed"):
                        chunker.chunk_document(mock_doc)
    
    def test_chunk_document_chunking_failure(self, mock_docling_document):
        """Test handling of chunking failure."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker') as mock_hybrid_chunker:
                    mock_chunker_instance = Mock()
                    mock_chunker_instance.chunk.side_effect = Exception("Chunking failed")
                    mock_hybrid_chunker.return_value = mock_chunker_instance
                    
                    chunker = DoclingChunkerWrapper()
                    
                    with pytest.raises(RuntimeError, match="Document chunking failed"):
                        chunker.chunk_document(mock_docling_document)
    
    def test_validate_chunk_valid(self, mock_docling_chunk):
        """Test validation of valid chunk."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker'):
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.return_value = 50
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    chunker = DoclingChunkerWrapper()
                    
                    assert chunker._validate_chunk(mock_docling_chunk, 0) is True
    
    def test_validate_chunk_no_text(self):
        """Test validation of chunk with no text."""
        mock_chunk = Mock()
        mock_chunk.text = ""
        
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker'):
                    chunker = DoclingChunkerWrapper()
                    
                    assert chunker._validate_chunk(mock_chunk, 0) is False
    
    def test_validate_chunk_text_too_short(self):
        """Test validation of chunk with too short text."""
        mock_chunk = Mock()
        mock_chunk.text = "Short"  # Less than 10 characters
        
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker'):
                    chunker = DoclingChunkerWrapper()
                    
                    assert chunker._validate_chunk(mock_chunk, 0) is False
    
    def test_validate_chunk_exceeds_max_tokens(self, mock_docling_chunk):
        """Test validation of chunk that exceeds max tokens (should still return True)."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker'):
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.return_value = 1000  # Exceeds default max_tokens
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    chunker = DoclingChunkerWrapper(max_tokens=512)
                    
                    # Should still return True but log a warning
                    assert chunker._validate_chunk(mock_docling_chunk, 0) is True
    
    def test_contextualize_chunk_success(self, mock_docling_chunk):
        """Test successful chunk contextualization."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker') as mock_hybrid_chunker:
                    mock_chunker_instance = Mock()
                    mock_chunker_instance.contextualize.return_value = "Contextualized text"
                    mock_hybrid_chunker.return_value = mock_chunker_instance
                    
                    chunker = DoclingChunkerWrapper()
                    result = chunker.contextualize_chunk(mock_docling_chunk)
                    
                    assert result == "Contextualized text"
    
    def test_contextualize_chunk_none_input(self):
        """Test contextualization with None chunk."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker'):
                    chunker = DoclingChunkerWrapper()
                    
                    # Should return empty string for None chunk (fallback behavior)
                    result = chunker.contextualize_chunk(None)
                    assert result == ""
    
    def test_contextualize_chunk_error_fallback(self, mock_docling_chunk):
        """Test contextualization error with fallback to original text."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker') as mock_hybrid_chunker:
                    mock_chunker_instance = Mock()
                    mock_chunker_instance.contextualize.side_effect = Exception("Contextualization failed")
                    mock_hybrid_chunker.return_value = mock_chunker_instance
                    
                    chunker = DoclingChunkerWrapper()
                    result = chunker.contextualize_chunk(mock_docling_chunk)
                    
                    # Should fallback to original text
                    assert result == mock_docling_chunk.text
    
    def test_get_chunk_metadata_success(self, mock_docling_chunk):
        """Test successful metadata extraction."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker'):
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.return_value = 25
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    chunker = DoclingChunkerWrapper()
                    metadata = chunker.get_chunk_metadata(mock_docling_chunk)
                    
                    assert 'text_length' in metadata
                    assert 'token_count' in metadata
                    assert 'page_number' in metadata
                    assert 'section' in metadata
                    assert metadata['token_count'] == 25
    
    def test_get_chunk_metadata_no_meta(self):
        """Test metadata extraction from chunk without meta."""
        mock_chunk = Mock()
        mock_chunk.text = "Test chunk"
        mock_chunk.meta = None
        
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker'):
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.return_value = 5
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    chunker = DoclingChunkerWrapper()
                    metadata = chunker.get_chunk_metadata(mock_chunk)
                    
                    assert 'text_length' in metadata
                    assert 'token_count' in metadata
                    assert metadata['text_length'] == 10
                    assert metadata['token_count'] == 5
    
    def test_count_tokens_success(self):
        """Test token counting."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker'):
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.return_value = 42
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    chunker = DoclingChunkerWrapper()
                    count = chunker.count_tokens("This is a test string")
                    
                    assert count == 42
    
    def test_count_tokens_error_fallback(self):
        """Test token counting with error fallback."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer') as mock_hf_tokenizer:
                with patch('src.docling_chunker.HybridChunker'):
                    mock_tokenizer = Mock()
                    mock_tokenizer.count_tokens.side_effect = Exception("Tokenizer error")
                    mock_hf_tokenizer.return_value = mock_tokenizer
                    
                    chunker = DoclingChunkerWrapper()
                    count = chunker.count_tokens("This is a test string")
                    
                    # Should fallback to word count
                    assert count == 5  # Number of words
    
    def test_get_chunker_config(self):
        """Test getting chunker configuration."""
        with patch('src.docling_chunker.AutoTokenizer'):
            with patch('src.docling_chunker.HuggingFaceTokenizer'):
                with patch('src.docling_chunker.HybridChunker'):
                    chunker = DoclingChunkerWrapper(
                        tokenizer_model="test-model",
                        max_tokens=256,
                        merge_peers=False
                    )
                    
                    config = chunker.get_chunker_config()
                    
                    assert config['tokenizer_model'] == "test-model"
                    assert config['max_tokens'] == 256
                    assert config['merge_peers'] is False


@pytest.mark.integration
class TestDoclingChunkerIntegration:
    """Integration tests for DoclingChunkerWrapper."""
    
    def test_real_chunking_workflow(self):
        """Test real chunking workflow (requires actual Docling)."""
        pytest.skip("Integration test - requires actual Docling installation")
    
    def test_chunker_with_different_tokenizers(self):
        """Test chunker with different tokenizer models."""
        pytest.skip("Integration test - requires HuggingFace model downloads")
    
    def test_chunker_performance(self):
        """Test chunker performance with large documents."""
        pytest.skip("Integration test - requires performance testing setup")
