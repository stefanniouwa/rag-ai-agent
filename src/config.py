"""Configuration management for the RAG AI Agent."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_anon_key: str = Field(..., env="SUPABASE_ANON_KEY")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # Environment Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Application Configuration
    max_file_size_mb: int = Field(default=50, env="MAX_FILE_SIZE_MB")
    max_files_per_upload: int = Field(default=10, env="MAX_FILES_PER_UPLOAD")
    chunk_size: int = Field(default=512, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, env="CHUNK_OVERLAP")
    top_k_results: int = Field(default=4, env="TOP_K_RESULTS")
    chat_memory_turns: int = Field(default=5, env="CHAT_MEMORY_TURNS")
    
    # Performance Configuration
    supabase_timeout_seconds: int = Field(default=30, env="SUPABASE_TIMEOUT_SECONDS")
    openai_timeout_seconds: int = Field(default=60, env="OPENAI_TIMEOUT_SECONDS")
    max_concurrent_uploads: int = Field(default=3, env="MAX_CONCURRENT_UPLOADS")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
