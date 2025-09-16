"""OpenAI embedding generation for vector storage and retrieval."""

import asyncio
import logging
import time
from typing import List, Optional

from openai import AsyncOpenAI, OpenAI
from openai.types import CreateEmbeddingResponse

from .config import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """OpenAI embedding generator with error handling and retry logic."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        max_retries: int = 3,
        timeout: int = None
    ):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: OpenAI API key (defaults to settings.openai_api_key)
            model: Embedding model to use
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds (defaults to settings.openai_timeout_seconds)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout or settings.openai_timeout_seconds
        
        # Initialize OpenAI clients
        self.client = OpenAI(
            api_key=self.api_key,
            timeout=self.timeout
        )
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        logger.info(f"Initialized EmbeddingGenerator with model: {model}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            ValueError: If text is empty or too long
            RuntimeError: If embedding generation fails
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            # Clean and validate text
            cleaned_text = self._clean_text(text)
            if len(cleaned_text) > 8191:  # OpenAI text-embedding-3-small limit
                logger.warning(f"Text length {len(cleaned_text)} exceeds model limit, truncating")
                cleaned_text = cleaned_text[:8191]
            
            logger.debug(f"Generating embedding for text of length: {len(cleaned_text)}")
            
            # Generate embedding with retries
            for attempt in range(self.max_retries + 1):
                try:
                    response: CreateEmbeddingResponse = self.client.embeddings.create(
                        model=self.model,
                        input=cleaned_text
                    )
                    
                    if response.data and len(response.data) > 0:
                        embedding = response.data[0].embedding
                        logger.debug(f"Successfully generated embedding with {len(embedding)} dimensions")
                        return embedding
                    else:
                        raise RuntimeError("Empty response from OpenAI API")
                        
                except Exception as e:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                        time.sleep(wait_time)
                    else:
                        raise
            
            raise RuntimeError(f"Failed to generate embedding after {self.max_retries} retries")
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise RuntimeError(f"Embedding generation failed: {str(e)}") from e
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple text strings in batch.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors (one per input text)
            
        Raises:
            ValueError: If texts list is empty
            RuntimeError: If batch embedding generation fails
        """
        try:
            if not texts:
                raise ValueError("Texts list cannot be empty")
            
            # Clean and validate texts
            cleaned_texts = []
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    logger.warning(f"Skipping empty text at index {i}")
                    cleaned_texts.append("")
                    continue
                
                cleaned_text = self._clean_text(text)
                if len(cleaned_text) > 8191:
                    logger.warning(f"Text {i} length {len(cleaned_text)} exceeds limit, truncating")
                    cleaned_text = cleaned_text[:8191]
                
                cleaned_texts.append(cleaned_text)
            
            # Filter out empty texts for API call
            non_empty_texts = [t for t in cleaned_texts if t]
            if not non_empty_texts:
                raise ValueError("No valid texts to process")
            
            logger.info(f"Generating embeddings for {len(non_empty_texts)} texts")
            
            # Generate embeddings with retries
            for attempt in range(self.max_retries + 1):
                try:
                    response: CreateEmbeddingResponse = self.client.embeddings.create(
                        model=self.model,
                        input=non_empty_texts
                    )
                    
                    if response.data and len(response.data) == len(non_empty_texts):
                        embeddings = [item.embedding for item in response.data]
                        logger.info(f"Successfully generated {len(embeddings)} embeddings")
                        
                        # Map back to original texts list (including empty ones)
                        result_embeddings = []
                        non_empty_index = 0
                        
                        for text in cleaned_texts:
                            if text:
                                result_embeddings.append(embeddings[non_empty_index])
                                non_empty_index += 1
                            else:
                                # Return zero vector for empty texts
                                result_embeddings.append([0.0] * len(embeddings[0]))
                        
                        return result_embeddings
                    else:
                        raise RuntimeError(f"Expected {len(non_empty_texts)} embeddings, got {len(response.data)}")
                        
                except Exception as e:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Batch attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                        time.sleep(wait_time)
                    else:
                        raise
            
            raise RuntimeError(f"Failed to generate batch embeddings after {self.max_retries} retries")
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise RuntimeError(f"Batch embedding generation failed: {str(e)}") from e
    
    async def generate_embeddings_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings asynchronously for multiple text strings.
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding vectors (one per input text)
        """
        try:
            if not texts:
                raise ValueError("Texts list cannot be empty")
            
            # Clean and validate texts
            cleaned_texts = []
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    logger.warning(f"Skipping empty text at index {i}")
                    cleaned_texts.append("")
                    continue
                
                cleaned_text = self._clean_text(text)
                if len(cleaned_text) > 8191:
                    logger.warning(f"Text {i} length {len(cleaned_text)} exceeds limit, truncating")
                    cleaned_text = cleaned_text[:8191]
                
                cleaned_texts.append(cleaned_text)
            
            # Filter out empty texts for API call
            non_empty_texts = [t for t in cleaned_texts if t]
            if not non_empty_texts:
                raise ValueError("No valid texts to process")
            
            logger.info(f"Generating embeddings asynchronously for {len(non_empty_texts)} texts")
            
            # Generate embeddings with retries
            for attempt in range(self.max_retries + 1):
                try:
                    response: CreateEmbeddingResponse = await self.async_client.embeddings.create(
                        model=self.model,
                        input=non_empty_texts
                    )
                    
                    if response.data and len(response.data) == len(non_empty_texts):
                        embeddings = [item.embedding for item in response.data]
                        logger.info(f"Successfully generated {len(embeddings)} embeddings async")
                        
                        # Map back to original texts list (including empty ones)
                        result_embeddings = []
                        non_empty_index = 0
                        
                        for text in cleaned_texts:
                            if text:
                                result_embeddings.append(embeddings[non_empty_index])
                                non_empty_index += 1
                            else:
                                # Return zero vector for empty texts
                                result_embeddings.append([0.0] * len(embeddings[0]))
                        
                        return result_embeddings
                    else:
                        raise RuntimeError(f"Expected {len(non_empty_texts)} embeddings, got {len(response.data)}")
                        
                except Exception as e:
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Async attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                        await asyncio.sleep(wait_time)
                    else:
                        raise
            
            raise RuntimeError(f"Failed to generate async embeddings after {self.max_retries} retries")
            
        except Exception as e:
            logger.error(f"Failed to generate async embeddings: {str(e)}")
            raise RuntimeError(f"Async embedding generation failed: {str(e)}") from e
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text for embedding generation.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text string
        """
        if not text:
            return ""
        
        # Basic text cleaning
        cleaned = text.strip()
        
        # Remove excessive whitespace
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove null characters that might cause issues
        cleaned = cleaned.replace('\x00', '')
        
        return cleaned
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings for the current model.
        
        Returns:
            Embedding dimension (1536 for text-embedding-3-small)
        """
        # Known dimensions for OpenAI models
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        
        return model_dimensions.get(self.model, 1536)  # Default to 1536
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate an embedding vector.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if embedding is valid, False otherwise
        """
        try:
            if not embedding:
                return False
            
            if not isinstance(embedding, list):
                return False
            
            if len(embedding) != self.get_embedding_dimension():
                logger.warning(f"Embedding dimension mismatch: {len(embedding)} vs expected {self.get_embedding_dimension()}")
                return False
            
            # Check for valid float values
            for val in embedding:
                if not isinstance(val, (int, float)):
                    return False
                if not (-1.0 <= val <= 1.0):  # OpenAI embeddings are normalized
                    logger.warning(f"Embedding value {val} outside expected range [-1, 1]")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating embedding: {str(e)}")
            return False
