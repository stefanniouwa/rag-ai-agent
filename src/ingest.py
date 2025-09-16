"""Document processing and ingestion pipeline using Docling and OpenAI embeddings."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hierarchical_chunker import DocChunk

from .config import settings
from .db import get_db_client, SupabaseClient
from .docling_converter import DoclingConverterWrapper
from .docling_chunker import DoclingChunkerWrapper
from .embeddings import EmbeddingGenerator
from .models import ConversionResult, Document, VectorChunk

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """Complete document ingestion pipeline using Docling and OpenAI."""
    
    def __init__(
        self,
        tokenizer_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        embedding_model: str = "text-embedding-3-small",
        max_tokens: int = None,
        batch_size: int = 10
    ):
        """
        Initialize the ingestion pipeline.
        
        Args:
            tokenizer_model: HuggingFace tokenizer model for chunking
            embedding_model: OpenAI embedding model
            max_tokens: Maximum tokens per chunk (defaults to settings.chunk_size)
            batch_size: Number of chunks to process in each embedding batch
        """
        self.tokenizer_model = tokenizer_model
        self.embedding_model = embedding_model
        self.max_tokens = max_tokens or settings.chunk_size
        self.batch_size = batch_size
        
        # Initialize components
        self.converter = DoclingConverterWrapper()
        self.chunker = DoclingChunkerWrapper(
            tokenizer_model=tokenizer_model,
            max_tokens=self.max_tokens,
            merge_peers=True
        )
        self.embedder = EmbeddingGenerator(model=embedding_model)
        self.db = get_db_client()
        
        logger.info(f"Initialized DocumentIngestionPipeline with {tokenizer_model}, {embedding_model}")
    
    def ingest_document(
        self, 
        file_path: str, 
        filename: Optional[str] = None
    ) -> ConversionResult:
        """
        Complete document ingestion workflow.
        
        Args:
            file_path: Path to the document file
            filename: Custom filename (defaults to file_path basename)
            
        Returns:
            ConversionResult with ingestion details
            
        Raises:
            ValueError: If file doesn't exist or is unsupported
            RuntimeError: If ingestion fails
        """
        try:
            # Validate input
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"File does not exist: {file_path}")
            
            file_path = Path(file_path)
            display_filename = filename or file_path.name
            
            logger.info(f"Starting document ingestion for: {display_filename}")
            
            # Step 1: Convert document using Docling
            logger.info("Step 1: Converting document with Docling")
            docling_doc = self.converter.convert_document(file_path)
            
            if not docling_doc:
                raise RuntimeError("Document conversion failed - no document returned")
            
            if not self.converter.validate_document(docling_doc):
                raise RuntimeError("Document validation failed after conversion")
            
            # Step 2: Create document record in database
            logger.info("Step 2: Creating document record")
            doc_record = self.db.create_document(display_filename)
            
            try:
                # Step 3: Chunk document using Docling HybridChunker
                logger.info("Step 3: Chunking document with HybridChunker")
                chunks = self.chunker.chunk_document(docling_doc)
                
                if not chunks:
                    raise RuntimeError("Document chunking produced no chunks")
                
                logger.info(f"Generated {len(chunks)} chunks")
                
                # Step 4: Generate embeddings and store vectors
                logger.info("Step 4: Generating embeddings and storing vectors")
                chunks_created = self._process_and_store_chunks(doc_record.id, chunks)
                
                # Step 5: Return success result
                result = ConversionResult(
                    doc_id=doc_record.id,
                    filename=display_filename,
                    chunks_created=chunks_created,
                    conversion_status="success"
                )
                
                logger.info(f"Successfully ingested document: {display_filename} ({chunks_created} chunks)")
                return result
                
            except Exception as e:
                # Cleanup on failure - delete document record
                logger.error(f"Ingestion failed, cleaning up document record: {str(e)}")
                try:
                    self.db.delete_document(doc_record.id)
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup document record: {str(cleanup_error)}")
                raise
                
        except Exception as e:
            error_msg = f"Document ingestion failed for {file_path}: {str(e)}"
            logger.error(error_msg)
            
            # Return error result
            return ConversionResult(
                doc_id=UUID('00000000-0000-0000-0000-000000000000'),  # Dummy ID for failed conversions
                filename=filename or str(file_path),
                chunks_created=0,
                conversion_status="failed",
                error_message=str(e)
            )
    
    def _process_and_store_chunks(
        self, 
        doc_id: UUID, 
        chunks: List[DocChunk]
    ) -> int:
        """
        Process chunks: generate embeddings and store in database.
        
        Args:
            doc_id: Document ID for associating chunks
            chunks: List of DocChunk objects
            
        Returns:
            Number of chunks successfully stored
        """
        try:
            total_chunks = len(chunks)
            stored_count = 0
            
            # Process chunks in batches for better performance
            for i in range(0, total_chunks, self.batch_size):
                batch_chunks = chunks[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_chunks + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")
                
                try:
                    # Extract text content from chunks
                    chunk_texts = []
                    for chunk in batch_chunks:
                        # Use contextualized text if available, fallback to regular text
                        try:
                            text = self.chunker.contextualize_chunk(chunk)
                            if not text:
                                text = chunk.text or ""
                        except Exception:
                            text = chunk.text or ""
                        
                        chunk_texts.append(text)
                    
                    # Generate embeddings for batch
                    embeddings = self.embedder.generate_embeddings(chunk_texts)
                    
                    # Create VectorChunk objects
                    vector_chunks = []
                    for j, (chunk, text, embedding) in enumerate(zip(batch_chunks, chunk_texts, embeddings)):
                        chunk_id = i + j
                        
                        # Extract chunk metadata
                        chunk_metadata = self.chunker.get_chunk_metadata(chunk)
                        
                        # Add additional metadata
                        chunk_metadata.update({
                            'batch_id': batch_num,
                            'tokenizer_model': self.tokenizer_model,
                            'embedding_model': self.embedding_model,
                            'chunk_length': len(text),
                        })
                        
                        vector_chunk = VectorChunk(
                            id=UUID('00000000-0000-0000-0000-000000000000'),  # Will be generated by DB
                            doc_id=doc_id,
                            chunk_id=chunk_id,
                            content=text,
                            embedding=embedding,
                            metadata=chunk_metadata
                        )
                        vector_chunks.append(vector_chunk)
                    
                    # Store batch in database
                    self.db.insert_vectors(vector_chunks)
                    stored_count += len(vector_chunks)
                    
                    logger.info(f"Stored batch {batch_num}/{total_batches} ({len(vector_chunks)} chunks)")
                    
                except Exception as batch_error:
                    logger.error(f"Failed to process batch {batch_num}: {str(batch_error)}")
                    # Continue with next batch rather than failing completely
                    continue
            
            logger.info(f"Successfully stored {stored_count}/{total_chunks} chunks")
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to process and store chunks: {str(e)}")
            raise RuntimeError(f"Chunk processing failed: {str(e)}") from e
    
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file before ingestion.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            file_path = Path(file_path)
            
            # Check if file exists
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"
            
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_file_size_mb:
                return False, f"File size ({file_size_mb:.1f}MB) exceeds limit ({settings.max_file_size_mb}MB)"
            
            # Check file extension
            supported_formats = self.converter.get_supported_formats()
            if file_path.suffix.lower() not in supported_formats:
                return False, f"Unsupported file format: {file_path.suffix}. Supported: {supported_formats}"
            
            # Check if file is readable
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Try to read first 1KB
            except PermissionError:
                return False, f"Permission denied reading file: {file_path}"
            except Exception as e:
                return False, f"Cannot read file: {str(e)}"
            
            return True, None
            
        except Exception as e:
            return False, f"File validation error: {str(e)}"
    
    def get_pipeline_info(self) -> Dict[str, Any]:
        """
        Get information about the current pipeline configuration.
        
        Returns:
            Dictionary with pipeline configuration details
        """
        return {
            'tokenizer_model': self.tokenizer_model,
            'embedding_model': self.embedding_model,
            'max_tokens': self.max_tokens,
            'batch_size': self.batch_size,
            'supported_formats': self.converter.get_supported_formats(),
            'embedding_dimension': self.embedder.get_embedding_dimension(),
            'chunker_config': self.chunker.get_chunker_config(),
        }
    
    def test_pipeline(self) -> Dict[str, bool]:
        """
        Test all pipeline components.
        
        Returns:
            Dictionary with component test results
        """
        results = {}
        
        # Test database connection
        try:
            results['database'] = self.db.test_connection()
        except Exception as e:
            logger.error(f"Database test failed: {str(e)}")
            results['database'] = False
        
        # Test embedding generation
        try:
            test_embedding = self.embedder.generate_embedding("Test text for pipeline validation")
            results['embeddings'] = self.embedder.validate_embedding(test_embedding)
        except Exception as e:
            logger.error(f"Embedding test failed: {str(e)}")
            results['embeddings'] = False
        
        # Test chunker configuration
        try:
            chunker_config = self.chunker.get_chunker_config()
            results['chunker'] = bool(chunker_config.get('tokenizer_model'))
        except Exception as e:
            logger.error(f"Chunker test failed: {str(e)}")
            results['chunker'] = False
        
        # Test converter
        try:
            supported_formats = self.converter.get_supported_formats()
            results['converter'] = len(supported_formats) > 0
        except Exception as e:
            logger.error(f"Converter test failed: {str(e)}")
            results['converter'] = False
        
        return results


# Convenience functions for external use
def ingest_document(file_path: str, filename: Optional[str] = None) -> ConversionResult:
    """
    Convenience function to ingest a single document.
    
    Args:
        file_path: Path to the document file
        filename: Custom filename (optional)
        
    Returns:
        ConversionResult with ingestion details
    """
    pipeline = DocumentIngestionPipeline()
    return pipeline.ingest_document(file_path, filename)


def validate_document_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to validate a document file.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    pipeline = DocumentIngestionPipeline()
    return pipeline.validate_file(file_path)


def get_ingestion_pipeline() -> DocumentIngestionPipeline:
    """
    Get a configured ingestion pipeline instance.
    
    Returns:
        DocumentIngestionPipeline instance
    """
    return DocumentIngestionPipeline()


def test_ingestion_pipeline() -> Dict[str, bool]:
    """
    Test the ingestion pipeline components.
    
    Returns:
        Dictionary with component test results
    """
    pipeline = DocumentIngestionPipeline()
    return pipeline.test_pipeline()
