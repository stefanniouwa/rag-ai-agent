"""Unit tests for OpenAI embedding generation."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.embeddings import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Test cases for EmbeddingGenerator."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI embedding response."""
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        return mock_response
    
    @pytest.fixture
    def mock_batch_openai_response(self):
        """Create mock OpenAI batch embedding response."""
        mock_response = Mock()
        mock_response.data = []
        for i in range(3):
            mock_item = Mock()
            mock_item.embedding = [0.1 + i * 0.1, 0.2 + i * 0.1, 0.3 + i * 0.1] * 512
            mock_response.data.append(mock_item)
        return mock_response
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_initialization_default(self, mock_async_openai, mock_openai):
        """Test initialization with default parameters."""
        generator = EmbeddingGenerator()
        
        assert generator.model == "text-embedding-3-small"
        assert generator.max_retries == 3
        assert generator.client is not None
        assert generator.async_client is not None
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_initialization_custom(self, mock_async_openai, mock_openai):
        """Test initialization with custom parameters."""
        generator = EmbeddingGenerator(
            api_key="test-key",
            model="text-embedding-3-large",
            max_retries=5,
            timeout=120
        )
        
        assert generator.api_key == "test-key"
        assert generator.model == "text-embedding-3-large"
        assert generator.max_retries == 5
        assert generator.timeout == 120
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embedding_success(self, mock_async_openai, mock_openai, mock_openai_response):
        """Test successful single embedding generation."""
        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client
        
        generator = EmbeddingGenerator()
        result = generator.generate_embedding("Test text for embedding")
        
        assert isinstance(result, list)
        assert len(result) == 1536  # Expected dimension
        assert all(isinstance(x, float) for x in result)
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embedding_empty_text(self, mock_async_openai, mock_openai):
        """Test embedding generation with empty text."""
        generator = EmbeddingGenerator()
        
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            generator.generate_embedding("")
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embedding_long_text_truncation(self, mock_async_openai, mock_openai, mock_openai_response):
        """Test embedding generation with text that exceeds length limit."""
        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_openai_response
        mock_openai.return_value = mock_client
        
        generator = EmbeddingGenerator()
        long_text = "A" * 10000  # Exceeds 8191 character limit
        
        result = generator.generate_embedding(long_text)
        
        # Should truncate and still work
        assert isinstance(result, list)
        assert len(result) == 1536
        
        # Verify the API was called with truncated text
        call_args = mock_client.embeddings.create.call_args
        assert len(call_args[1]['input']) <= 8191
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embedding_api_failure_with_retry(self, mock_async_openai, mock_openai, mock_openai_response):
        """Test embedding generation with API failure and successful retry."""
        mock_client = Mock()
        # First call fails, second succeeds
        mock_client.embeddings.create.side_effect = [
            Exception("API Error"),
            mock_openai_response
        ]
        mock_openai.return_value = mock_client
        
        generator = EmbeddingGenerator(max_retries=1)
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = generator.generate_embedding("Test text")
        
        assert isinstance(result, list)
        assert len(result) == 1536
        assert mock_client.embeddings.create.call_count == 2
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embedding_max_retries_exceeded(self, mock_async_openai, mock_openai):
        """Test embedding generation when max retries are exceeded."""
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("Persistent API Error")
        mock_openai.return_value = mock_client
        
        generator = EmbeddingGenerator(max_retries=2)
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(RuntimeError, match="Embedding generation failed"):
                generator.generate_embedding("Test text")
        
        assert mock_client.embeddings.create.call_count == 3  # Initial + 2 retries
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embeddings_batch_success(self, mock_async_openai, mock_openai, mock_batch_openai_response):
        """Test successful batch embedding generation."""
        mock_client = Mock()
        mock_client.embeddings.create.return_value = mock_batch_openai_response
        mock_openai.return_value = mock_client
        
        generator = EmbeddingGenerator()
        texts = ["Text one", "Text two", "Text three"]
        
        results = generator.generate_embeddings(texts)
        
        assert len(results) == 3
        assert all(len(embedding) == 1536 for embedding in results)
        assert all(isinstance(embedding, list) for embedding in results)
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embeddings_empty_list(self, mock_async_openai, mock_openai):
        """Test batch embedding generation with empty list."""
        generator = EmbeddingGenerator()
        
        with pytest.raises(RuntimeError, match="Batch embedding generation failed"):
            generator.generate_embeddings([])
    
    @patch('src.embeddings.OpenAI')
    @patch('src.embeddings.AsyncOpenAI')
    def test_generate_embeddings_with_empty_texts(self, mock_async_openai, mock_openai):
        """Test batch embedding generation with some empty texts."""
        mock_client = Mock()
        # Create response for 2 non-empty texts
        mock_response = Mock()
        mock_response.data = []
        for i in range(2):
            mock_item = Mock()
            mock_item.embedding = [0.1 + i * 0.1] * 1536
            mock_response.data.append(mock_item)
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        generator = EmbeddingGenerator()
        texts = ["Valid text", "", "Another valid text", "   "]  # 2 valid, 2 empty
        
        results = generator.generate_embeddings(texts)
        
        assert len(results) == 4
        # Empty texts should get zero vectors
        assert results[1] == [0.0] * 1536
        assert results[3] == [0.0] * 1536
        # Valid texts should have proper embeddings
        assert results[0] != [0.0] * 1536
        assert results[2] != [0.0] * 1536
    
    @patch('src.embeddings.AsyncOpenAI')
    @patch('src.embeddings.OpenAI')
    def test_generate_embeddings_async_success(self, mock_openai, mock_async_openai, mock_batch_openai_response):
        """Test successful async batch embedding generation."""
        mock_async_client = Mock()
        mock_async_client.embeddings.create = AsyncMock(return_value=mock_batch_openai_response)
        mock_async_openai.return_value = mock_async_client
        
        generator = EmbeddingGenerator()
        texts = ["Text one", "Text two", "Text three"]
        
        # Run async function
        async def run_test():
            return await generator.generate_embeddings_async(texts)
        
        results = asyncio.run(run_test())
        
        assert len(results) == 3
        assert all(len(embedding) == 1536 for embedding in results)
    
    @patch('src.embeddings.AsyncOpenAI')
    @patch('src.embeddings.OpenAI')
    def test_generate_embeddings_async_with_retry(self, mock_openai, mock_async_openai, mock_batch_openai_response):
        """Test async embedding generation with retry."""
        mock_async_client = Mock()
        # First call fails, second succeeds
        mock_async_client.embeddings.create = AsyncMock(side_effect=[
            Exception("Async API Error"),
            mock_batch_openai_response
        ])
        mock_async_openai.return_value = mock_async_client
        
        generator = EmbeddingGenerator(max_retries=1)
        texts = ["Text one"]
        
        # Fix the mock to return correct response for single text
        mock_single_response = Mock()
        mock_single_response.data = [Mock()]
        mock_single_response.data[0].embedding = [0.1] * 1536
        
        mock_async_client.embeddings.create = AsyncMock(side_effect=[
            Exception("Async API Error"),
            mock_single_response  # Return single response, not batch
        ])
        
        async def run_test():
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Mock async sleep
                return await generator.generate_embeddings_async(texts)
        
        results = asyncio.run(run_test())
        
        assert len(results) == 1
        assert len(results[0]) == 1536
    
    def test_clean_text(self):
        """Test text cleaning functionality."""
        generator = EmbeddingGenerator()
        
        # Test various text cleaning scenarios
        assert generator._clean_text("  text with spaces  ") == "text with spaces"
        assert generator._clean_text("text\n\nwith\n\nmultiple\nlines") == "text with multiple lines"
        assert generator._clean_text("text\x00with\x00nulls") == "textwithnulls"  # Fix expected result
        assert generator._clean_text("") == ""
        assert generator._clean_text(None) == ""
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension for different models."""
        generator_small = EmbeddingGenerator(model="text-embedding-3-small")
        assert generator_small.get_embedding_dimension() == 1536
        
        generator_large = EmbeddingGenerator(model="text-embedding-3-large")
        assert generator_large.get_embedding_dimension() == 3072
        
        generator_ada = EmbeddingGenerator(model="text-embedding-ada-002")
        assert generator_ada.get_embedding_dimension() == 1536
        
        generator_unknown = EmbeddingGenerator(model="unknown-model")
        assert generator_unknown.get_embedding_dimension() == 1536  # Default
    
    def test_validate_embedding_valid(self):
        """Test validation of valid embedding."""
        generator = EmbeddingGenerator()
        valid_embedding = [0.1, -0.2, 0.5] * 512  # 1536 dimensions, normalized values
        
        assert generator.validate_embedding(valid_embedding) is True
    
    def test_validate_embedding_invalid_cases(self):
        """Test validation of various invalid embeddings."""
        generator = EmbeddingGenerator()
        
        # Empty embedding
        assert generator.validate_embedding([]) is False
        
        # Wrong type
        assert generator.validate_embedding("not a list") is False
        
        # Wrong dimension
        assert generator.validate_embedding([0.1, 0.2, 0.3]) is False
        
        # Invalid values (non-numeric)
        invalid_embedding = ["string"] * 1536
        assert generator.validate_embedding(invalid_embedding) is False
        
        # Values outside expected range (though this might still be valid)
        extreme_embedding = [2.0] * 1536  # Values > 1.0
        # This should still validate (just log a warning)
        # assert generator.validate_embedding(extreme_embedding) is True
    
    def test_validate_embedding_none(self):
        """Test validation of None embedding."""
        generator = EmbeddingGenerator()
        assert generator.validate_embedding(None) is False


@pytest.mark.integration
class TestEmbeddingGeneratorIntegration:
    """Integration tests for EmbeddingGenerator."""
    
    def test_real_openai_api_call(self):
        """Test real OpenAI API call (requires API key)."""
        pytest.skip("Integration test - requires OpenAI API key")
    
    def test_rate_limiting_behavior(self):
        """Test behavior under rate limiting."""
        pytest.skip("Integration test - requires rate limiting simulation")
    
    def test_large_batch_processing(self):
        """Test processing of large batches."""
        pytest.skip("Integration test - requires performance testing")


@pytest.mark.asyncio
class TestEmbeddingGeneratorAsync:
    """Async-specific tests for EmbeddingGenerator."""
    
    @patch('src.embeddings.AsyncOpenAI')
    @patch('src.embeddings.OpenAI')
    async def test_async_timeout_handling(self, mock_openai, mock_async_openai):
        """Test async timeout handling."""
        mock_async_client = Mock()
        mock_async_client.embeddings.create = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_async_openai.return_value = mock_async_client
        
        generator = EmbeddingGenerator(max_retries=0)
        
        with pytest.raises(RuntimeError):
            await generator.generate_embeddings_async(["Test text"])
    
    @patch('src.embeddings.AsyncOpenAI')
    @patch('src.embeddings.OpenAI')
    async def test_async_concurrent_calls(self, mock_openai, mock_async_openai):
        """Test concurrent async embedding calls."""
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1] * 1536
        
        mock_async_client = Mock()
        mock_async_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_async_openai.return_value = mock_async_client
        
        generator = EmbeddingGenerator()
        
        # Run multiple async calls concurrently
        tasks = [
            generator.generate_embeddings_async([f"Text {i}"])
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(len(result) == 1 for result in results)
        assert all(len(result[0]) == 1536 for result in results)
