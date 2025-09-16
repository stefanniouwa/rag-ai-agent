"""Docling document converter wrapper for unified document processing."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument

logger = logging.getLogger(__name__)


class DoclingConverterWrapper:
    """Wrapper for Docling's DocumentConverter with enhanced error handling and logging."""
    
    def __init__(self):
        """Initialize the DocumentConverter with default configuration."""
        self.converter = DocumentConverter()
        logger.info("Initialized DoclingConverterWrapper")
    
    def convert_document(
        self, 
        source: Union[str, Path], 
        **kwargs
    ) -> Optional[DoclingDocument]:
        """
        Convert a document using Docling's DocumentConverter.
        
        Args:
            source: Path to the document file or URL
            **kwargs: Additional arguments to pass to the converter
            
        Returns:
            DoclingDocument object if conversion successful, None otherwise
            
        Raises:
            ValueError: If source file doesn't exist or is unsupported
            RuntimeError: If conversion fails
        """
        try:
            # Validate source file if it's a local path
            if isinstance(source, (str, Path)):
                source_path = Path(source)
                if not source_path.exists() and not str(source).startswith(('http://', 'https://')):
                    raise ValueError(f"Source file does not exist: {source}")
                
                # Check file extension for supported formats
                if source_path.exists():
                    supported_extensions = {'.pdf', '.docx', '.txt', '.html', '.md', '.png', '.jpg', '.jpeg'}
                    if source_path.suffix.lower() not in supported_extensions:
                        logger.warning(f"File extension {source_path.suffix} may not be supported")
            
            logger.info(f"Converting document: {source}")
            
            # Convert document using Docling
            conversion_result = self.converter.convert(source, **kwargs)
            
            if conversion_result and conversion_result.document:
                logger.info(f"Successfully converted document: {source}")
                return conversion_result.document
            else:
                logger.error(f"Conversion returned no document for: {source}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to convert document {source}: {str(e)}")
            raise RuntimeError(f"Document conversion failed: {str(e)}") from e
    
    def get_document_metadata(self, doc: DoclingDocument) -> Dict[str, Any]:
        """
        Extract metadata from a converted DoclingDocument.
        
        Args:
            doc: The DoclingDocument to extract metadata from
            
        Returns:
            Dictionary containing document metadata
        """
        try:
            metadata = {
                'page_count': len(doc.pages) if doc.pages else 0,
                'has_tables': any(item.label.name == 'table' for page in doc.pages for item in page.items),
                'has_figures': any(item.label.name == 'figure' for page in doc.pages for item in page.items),
                'text_length': len(doc.export_to_markdown()) if doc else 0,
                'document_title': getattr(doc, 'title', None) or 'Untitled',
            }
            
            # Add page-specific metadata
            if doc.pages:
                metadata['page_dimensions'] = [
                    {'width': page.size.width, 'height': page.size.height} 
                    for page in doc.pages
                ]
            
            logger.debug(f"Extracted metadata: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {str(e)}")
            return {'error': str(e)}
    
    def validate_document(self, doc: DoclingDocument) -> bool:
        """
        Validate that a DoclingDocument is properly formatted and contains content.
        
        Args:
            doc: The DoclingDocument to validate
            
        Returns:
            True if document is valid, False otherwise
        """
        try:
            if not doc:
                logger.warning("Document is None")
                return False
            
            if not doc.pages:
                logger.warning("Document has no pages")
                return False
            
            # Check if document has any text content
            markdown_content = doc.export_to_markdown()
            if not markdown_content or len(markdown_content.strip()) < 10:
                logger.warning("Document has insufficient text content")
                return False
            
            logger.debug("Document validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Document validation failed: {str(e)}")
            return False
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported file formats.
        
        Returns:
            List of supported file extensions
        """
        return ['.pdf', '.docx', '.txt', '.html', '.md', '.png', '.jpg', '.jpeg']
    
    def convert_to_markdown(self, doc: DoclingDocument) -> str:
        """
        Convert DoclingDocument to markdown format.
        
        Args:
            doc: The DoclingDocument to convert
            
        Returns:
            Markdown representation of the document
        """
        try:
            if not self.validate_document(doc):
                raise ValueError("Invalid document provided")
            
            markdown = doc.export_to_markdown()
            logger.debug(f"Converted document to markdown ({len(markdown)} characters)")
            return markdown
            
        except Exception as e:
            logger.error(f"Failed to convert to markdown: {str(e)}")
            raise RuntimeError(f"Markdown conversion failed: {str(e)}") from e
