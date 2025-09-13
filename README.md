# RAG AI Agent - Streamlit Webapp

A single-user document intelligence webapp that allows users to upload personal documents, automatically processes them into a searchable knowledge base, and provides an AI-powered chat interface to query across their entire document corpus.

## Features

- **Document Ingestion**: Upload multiple file formats (PDF, DOCX, TXT, HTML, MD) with automatic text extraction using Docling
- **Intelligent Search**: Natural language queries across entire document collection using vector similarity search
- **Contextual Answers**: AI-generated responses with source citations and relevant snippets
- **Document Management**: View uploaded files and manage document library
- **Chat Memory**: Maintains conversation context for follow-up questions
- **Secure Access**: User authentication to protect personal documents

## Technology Stack

- **Frontend**: Streamlit web application
- **Backend**: Python with Docling for document processing
- **Database**: Supabase with pgvector extension for vector storage
- **AI Services**: OpenAI APIs for embeddings and chat completion
- **Testing**: Pytest with comprehensive unit and integration tests

## Phase 1 Implementation Status ✅

This repository currently includes the foundational data layer and infrastructure:

### Completed Components

- ✅ **Project Configuration**: `requirements.txt`, `pyproject.toml` with proper dependencies
- ✅ **Environment Setup**: `.env.example` template with all required variables
- ✅ **Database Schema**: Complete Supabase migration with pgvector support
- ✅ **Data Models**: Pydantic models for Document, VectorChunk, ChatMessage
- ✅ **Database Client**: Supabase client wrapper with CRUD operations
- ✅ **Testing Framework**: Pytest configuration with fixtures and mock setup

### Database Schema

The database includes three main tables:

- **documents**: Stores file metadata
- **vectors**: Stores document chunks with embeddings (1536-dim OpenAI)
- **chat_histories**: Stores conversation history

Key features:
- pgvector extension for efficient similarity search
- Cascade delete for data integrity
- Optimized indexes for performance
- Custom RPC functions for vector search

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp env.example .env

# Edit .env with your credentials:
# - SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY
# - OPENAI_API_KEY
```

### 2. Install Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install core dependencies
pip install -r requirements.txt

# Or install with development dependencies
pip install -e ".[dev]"

# Validate installation
python3 validate_phase1.py
```

### 3. Database Setup

1. Create a new Supabase project
2. Run the migration:
```sql
-- Execute the contents of supabase/migrations/001_initial_schema.sql
-- in your Supabase SQL editor
```

### 4. Run Tests

```bash
# Run unit tests
pytest tests/ -m "not integration"

# Run all tests (requires database connection)
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Project Structure

```
rag_ai_agent/
├── src/                    # Source code
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models
│   └── db.py              # Database client
├── tests/                 # Test suite
│   ├── conftest.py        # Test fixtures
│   └── test_db.py         # Database tests
├── supabase/
│   └── migrations/        # Database migrations
├── docs/                  # Documentation
│   └── features/          # Implementation plans
├── requirements.txt       # Dependencies
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

## Development

### Code Quality

The project includes comprehensive tooling for code quality:

- **Testing**: pytest with fixtures, mocking, and coverage reporting
- **Linting**: flake8 for code style
- **Formatting**: black and isort for consistent formatting
- **Type Checking**: mypy for static type analysis
- **Security**: bandit for security vulnerability scanning

### Running Quality Checks

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type check
mypy src/

# Security scan
bandit -r src/
```

## Next Steps

The following phases will build upon this foundation:

- **Phase 2A**: Document ingestion pipeline with Docling
- **Phase 2B**: Query and retrieval system with OpenAI
- **Phase 2C**: Streamlit frontend interface
- **Phase 3**: Integration and document management
- **Phase 4**: Testing and quality assurance
- **Phase 5**: Deployment and production setup

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `ENVIRONMENT` | No | Environment (development/production) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

### Optional Configuration

Additional settings for fine-tuning performance and behavior are available in `env.example`.

## License

MIT License - see LICENSE file for details.

## Contributing

This project follows Test-Driven Development (TDD) principles. Please ensure all tests pass and maintain high code coverage for any contributions.
