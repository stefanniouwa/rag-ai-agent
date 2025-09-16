"""Unit tests for Docling document converter wrapper."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.docling_converter import DoclingConverterWrapper


class TestDoclingConverterWrapper:
    """Test cases for DoclingConverterWrapper."""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance for testing."""
        return DoclingConverterWrapper()
    
    @pytest.fixture
    def mock_docling_document(self):
        """Create a mock DoclingDocument for testing."""
        mock_doc = Mock()
        mock_doc.pages = [Mock()]
        mock_doc.pages[0].items = []
        mock_doc.pages[0].size = Mock(width=612, height=792)
        mock_doc.export_to_markdown.return_value = "# Test Document\n\nThis is a test document."
        mock_doc.title = "Test Document"
        return mock_doc
    
    def test_initialization(self, converter):
        """Test converter initialization."""
        assert converter.converter is not None
        assert hasattr(converter, 'converter')
    
    def test_convert_document_success(self, converter, mock_docling_document):
        """Test successful document conversion."""
        # Setup mock
        mock_conversion_result = Mock()
        mock_conversion_result.document = mock_docling_document
        
        # Create a test file
        test_file = Path("test.pdf")
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(converter.converter, 'convert', return_value=mock_conversion_result):
                result = converter.convert_document(test_file)
        
        assert result is not None
        assert result == mock_docling_document
    
    def test_convert_document_file_not_exists(self, converter):
        """Test conversion with non-existent file."""
        test_file = Path("nonexistent.pdf")
        
        with pytest.raises(RuntimeError, match="Document conversion failed"):
            converter.convert_document(test_file)
    
    def test_convert_document_unsupported_format(self, converter):
        """Test conversion with unsupported file format."""
        test_file = Path("test.xyz")
        
        with patch.object(Path, 'exists', return_value=True):
            # Should not raise an error but log a warning
            mock_conversion_result = Mock()
            mock_conversion_result.document = Mock()
            
            with patch.object(converter.converter, 'convert', return_value=mock_conversion_result):
                result = converter.convert_document(test_file)
                assert result is not None
    
    @patch('src.docling_converter.DocumentConverter')
    def test_convert_document_conversion_failure(self, mock_doc_converter, converter):
        """Test handling of conversion failure."""
        test_file = Path("test.pdf")
        mock_doc_converter.return_value.convert.side_effect = Exception("Conversion failed")
        
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(RuntimeError, match="Document conversion failed"):
                converter.convert_document(test_file)
    
    def test_convert_document_url(self, converter, mock_docling_document):
        """Test conversion with URL source."""
        mock_conversion_result = Mock()
        mock_conversion_result.document = mock_docling_document
        
        url = "https://example.com/document.pdf"
        
        with patch.object(converter.converter, 'convert', return_value=mock_conversion_result):
            result = converter.convert_document(url)
        
        assert result is not None
        assert result == mock_docling_document
    
    def test_get_document_metadata(self, converter, mock_docling_document):
        """Test metadata extraction from document."""
        metadata = converter.get_document_metadata(mock_docling_document)
        
        assert isinstance(metadata, dict)
        assert 'page_count' in metadata
        assert 'has_tables' in metadata
        assert 'has_figures' in metadata
        assert 'text_length' in metadata
        assert 'document_title' in metadata
        assert metadata['page_count'] == 1
        assert metadata['document_title'] == "Test Document"
    
    def test_get_document_metadata_with_tables_and_figures(self, converter):
        """Test metadata extraction with tables and figures."""
        mock_doc = Mock()
        mock_doc.pages = [Mock()]
        
        # Create mock items with table and figure labels
        mock_table_item = Mock()
        mock_table_item.label.name = 'table'
        mock_figure_item = Mock()
        mock_figure_item.label.name = 'figure'
        
        mock_doc.pages[0].items = [mock_table_item, mock_figure_item]
        mock_doc.pages[0].size = Mock(width=612, height=792)
        mock_doc.export_to_markdown.return_value = "Content with tables and figures"
        mock_doc.title = "Document with Tables"
        
        metadata = converter.get_document_metadata(mock_doc)
        
        assert metadata['has_tables'] is True
        assert metadata['has_figures'] is True
    
    def test_get_document_metadata_error_handling(self, converter):
        """Test metadata extraction error handling."""
        mock_doc = Mock()
        mock_doc.pages = None  # This should cause an error
        
        metadata = converter.get_document_metadata(mock_doc)
        
        assert 'error' in metadata
    
    def test_validate_document_valid(self, converter, mock_docling_document):
        """Test validation of valid document."""
        assert converter.validate_document(mock_docling_document) is True
    
    def test_validate_document_none(self, converter):
        """Test validation of None document."""
        assert converter.validate_document(None) is False
    
    def test_validate_document_no_pages(self, converter):
        """Test validation of document with no pages."""
        mock_doc = Mock()
        mock_doc.pages = []
        
        assert converter.validate_document(mock_doc) is False
    
    def test_validate_document_insufficient_content(self, converter):
        """Test validation of document with insufficient content."""
        mock_doc = Mock()
        mock_doc.pages = [Mock()]
        mock_doc.export_to_markdown.return_value = "Short"  # Less than 10 characters
        
        assert converter.validate_document(mock_doc) is False
    
    def test_validate_document_error_handling(self, converter):
        """Test validation error handling."""
        mock_doc = Mock()
        mock_doc.pages = [Mock()]
        mock_doc.export_to_markdown.side_effect = Exception("Export failed")
        
        assert converter.validate_document(mock_doc) is False
    
    def test_get_supported_formats(self, converter):
        """Test getting supported file formats."""
        formats = converter.get_supported_formats()
        
        assert isinstance(formats, list)
        assert '.pdf' in formats
        assert '.docx' in formats
        assert '.txt' in formats
        assert '.html' in formats
        assert '.md' in formats
    
    def test_convert_to_markdown_success(self, converter, mock_docling_document):
        """Test successful markdown conversion."""
        markdown = converter.convert_to_markdown(mock_docling_document)
        
        assert isinstance(markdown, str)
        assert len(markdown) > 0
        assert markdown == "# Test Document\n\nThis is a test document."
    
    def test_convert_to_markdown_invalid_document(self, converter):
        """Test markdown conversion with invalid document."""
        mock_doc = Mock()
        mock_doc.pages = []
        
        with pytest.raises(RuntimeError, match="Markdown conversion failed"):
            converter.convert_to_markdown(mock_doc)
    
    def test_convert_to_markdown_error_handling(self, converter, mock_docling_document):
        """Test markdown conversion error handling."""
        mock_docling_document.export_to_markdown.side_effect = Exception("Export failed")
        
        with pytest.raises(RuntimeError, match="Markdown conversion failed"):
            converter.convert_to_markdown(mock_docling_document)


@pytest.mark.integration
class TestDoclingConverterIntegration:
    """Integration tests for DoclingConverterWrapper."""
    
    def test_real_conversion_workflow(self):
        """Test real conversion workflow (requires actual Docling)."""
        # This test would require actual files and Docling installation
        # Skipped in unit tests but useful for integration testing
        pytest.skip("Integration test - requires actual Docling installation")
    
    def test_converter_with_real_pdf(self):
        """Test converter with real PDF file."""
        pytest.skip("Integration test - requires test PDF file")
    
    def test_converter_performance(self):
        """Test converter performance with large documents."""
        pytest.skip("Integration test - requires performance testing setup")
