"""Docling HybridChunker integration with custom configuration for intelligent chunking."""

import logging
from typing import Iterator, List, Optional

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.base import BaseTokenizer
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hierarchical_chunker import DocChunk
from transformers import AutoTokenizer

from .config import settings

logger = logging.getLogger(__name__)


class DoclingChunkerWrapper:
    """Wrapper for Docling's HybridChunker with custom configuration and error handling."""
    
    def __init__(
        self, 
        tokenizer_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_tokens: int = None,
        merge_peers: bool = True
    ):
        """
        Initialize the HybridChunker with specified configuration.
        
        Args:
            tokenizer_model: HuggingFace tokenizer model to use
            max_tokens: Maximum tokens per chunk (defaults to settings.chunk_size)
            merge_peers: Whether to merge peer chunks (defaults to True)
        """
        self.tokenizer_model = tokenizer_model
        self.max_tokens = max_tokens or settings.chunk_size
        self.merge_peers = merge_peers
        
        # Initialize tokenizer
        self.tokenizer = self._setup_tokenizer()
        
        # Initialize chunker
        self.chunker = self._setup_chunker()
        
        logger.info(
            f"Initialized DoclingChunkerWrapper with tokenizer: {tokenizer_model}, "
            f"max_tokens: {self.max_tokens}, merge_peers: {merge_peers}"
        )
    
    def _setup_tokenizer(self) -> BaseTokenizer:
        """
        Setup HuggingFace tokenizer for chunking.
        
        Returns:
            Configured BaseTokenizer instance
        """
        try:
            hf_tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_model)
            tokenizer = HuggingFaceTokenizer(tokenizer=hf_tokenizer)
            logger.debug(f"Successfully initialized tokenizer: {self.tokenizer_model}")
            return tokenizer
            
        except Exception as e:
            logger.error(f"Failed to initialize tokenizer {self.tokenizer_model}: {str(e)}")
            # Fallback to a basic tokenizer if specified model fails
            try:
                logger.warning("Falling back to basic all-MiniLM-L6-v2 tokenizer")
                hf_tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
                return HuggingFaceTokenizer(tokenizer=hf_tokenizer)
            except Exception as fallback_error:
                logger.error(f"Fallback tokenizer also failed: {str(fallback_error)}")
                raise RuntimeError(f"Failed to initialize any tokenizer: {str(e)}") from e
    
    def _setup_chunker(self) -> HybridChunker:
        """
        Setup HybridChunker with configured tokenizer.
        
        Returns:
            Configured HybridChunker instance
        """
        try:
            chunker = HybridChunker(
                tokenizer=self.tokenizer,
                merge_peers=self.merge_peers
            )
            logger.debug("Successfully initialized HybridChunker")
            return chunker
            
        except Exception as e:
            logger.error(f"Failed to initialize HybridChunker: {str(e)}")
            raise RuntimeError(f"Chunker initialization failed: {str(e)}") from e
    
    def chunk_document(self, doc: DoclingDocument) -> List[DocChunk]:
        """
        Chunk a DoclingDocument into smaller pieces using HybridChunker.
        
        Args:
            doc: The DoclingDocument to chunk
            
        Returns:
            List of DocChunk objects
            
        Raises:
            ValueError: If document is invalid
            RuntimeError: If chunking fails
        """
        try:
            if not doc:
                raise ValueError("Document cannot be None")
            
            if not doc.pages:
                raise ValueError("Document must have at least one page")
            
            logger.info(f"Starting chunking process for document with {len(doc.pages)} pages")
            
            # Generate chunks
            chunk_iter: Iterator[DocChunk] = self.chunker.chunk(dl_doc=doc)
            chunks = list(chunk_iter)
            
            logger.info(f"Successfully generated {len(chunks)} chunks")
            
            # Validate chunks
            valid_chunks = []
            for i, chunk in enumerate(chunks):
                if self._validate_chunk(chunk, i):
                    valid_chunks.append(chunk)
                else:
                    logger.warning(f"Skipping invalid chunk {i}")
            
            logger.info(f"Returning {len(valid_chunks)} valid chunks out of {len(chunks)} total")
            return valid_chunks
            
        except Exception as e:
            logger.error(f"Failed to chunk document: {str(e)}")
            raise RuntimeError(f"Document chunking failed: {str(e)}") from e
    
    def _validate_chunk(self, chunk: DocChunk, chunk_index: int) -> bool:
        """
        Validate a DocChunk to ensure it has meaningful content.
        
        Args:
            chunk: The DocChunk to validate
            chunk_index: Index of the chunk for logging
            
        Returns:
            True if chunk is valid, False otherwise
        """
        try:
            # Check if chunk has text content
            if not chunk.text or not chunk.text.strip():
                logger.debug(f"Chunk {chunk_index} has no text content")
                return False
            
            # Check minimum text length
            if len(chunk.text.strip()) < 10:
                logger.debug(f"Chunk {chunk_index} text too short: {len(chunk.text)} chars")
                return False
            
            # Check token count
            token_count = self.tokenizer.count_tokens(chunk.text)
            if token_count > self.max_tokens:
                logger.warning(
                    f"Chunk {chunk_index} exceeds max tokens: {token_count} > {self.max_tokens}"
                )
                # Still return True as this might be acceptable depending on use case
            
            logger.debug(f"Chunk {chunk_index} is valid: {token_count} tokens, {len(chunk.text)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Error validating chunk {chunk_index}: {str(e)}")
            return False
    
    def contextualize_chunk(self, chunk: DocChunk) -> str:
        """
        Get contextualized text for a chunk with metadata.
        
        Args:
            chunk: The DocChunk to contextualize
            
        Returns:
            Contextualized text string
        """
        try:
            if not chunk:
                raise ValueError("Chunk cannot be None")
            
            contextualized = self.chunker.contextualize(chunk=chunk)
            logger.debug(f"Contextualized chunk: {len(contextualized)} characters")
            return contextualized
            
        except Exception as e:
            logger.error(f"Failed to contextualize chunk: {str(e)}")
            # Return original text as fallback
            return chunk.text if chunk and chunk.text else ""
    
    def get_chunk_metadata(self, chunk: DocChunk) -> dict:
        """
        Extract metadata from a DocChunk.
        
        Args:
            chunk: The DocChunk to extract metadata from
            
        Returns:
            Dictionary containing chunk metadata
        """
        try:
            metadata = {
                'text_length': len(chunk.text) if chunk.text else 0,
                'token_count': self.tokenizer.count_tokens(chunk.text) if chunk.text else 0,
            }
            
            # Add chunk metadata if available
            if hasattr(chunk, 'meta') and chunk.meta:
                try:
                    chunk_meta = chunk.meta.export_json_dict()
                    metadata.update(chunk_meta)
                except Exception as meta_error:
                    logger.warning(f"Failed to export chunk metadata: {str(meta_error)}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract chunk metadata: {str(e)}")
            return {'error': str(e)}
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string using the configured tokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            return self.tokenizer.count_tokens(text)
        except Exception as e:
            logger.error(f"Failed to count tokens: {str(e)}")
            # Rough fallback estimation
            return len(text.split())
    
    def get_chunker_config(self) -> dict:
        """
        Get current chunker configuration.
        
        Returns:
            Dictionary with chunker configuration
        """
        return {
            'tokenizer_model': self.tokenizer_model,
            'max_tokens': self.max_tokens,
            'merge_peers': self.merge_peers,
        }
