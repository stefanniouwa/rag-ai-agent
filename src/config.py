"""Configuration management for the RAG AI Agent."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    
    # Environment Configuration
    environment: str = Field(default="development", description="Environment (development/production)")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Application Configuration
    max_file_size_mb: int = Field(default=50, description="Maximum file size in MB")
    max_files_per_upload: int = Field(default=10, description="Maximum files per upload")
    chunk_size: int = Field(default=512, description="Text chunk size")
    chunk_overlap: int = Field(default=50, description="Text chunk overlap")
    top_k_results: int = Field(default=4, description="Top K results for vector search")
    chat_memory_turns: int = Field(default=5, description="Number of chat turns to remember")
    
    # Performance Configuration
    supabase_timeout_seconds: int = Field(default=30, description="Supabase request timeout")
    openai_timeout_seconds: int = Field(default=60, description="OpenAI request timeout")
    max_concurrent_uploads: int = Field(default=3, description="Maximum concurrent uploads")


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
