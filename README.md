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

## Implementation Status ✅

This repository includes a complete RAG AI Agent with Streamlit frontend:

### Phase 1: Data Layer and Infrastructure ✅
- ✅ **Project Configuration**: `requirements.txt`, `pyproject.toml` with proper dependencies
- ✅ **Environment Setup**: `.env.example` template with all required variables
- ✅ **Database Schema**: Complete Supabase migration with pgvector support
- ✅ **Data Models**: Pydantic models for Document, VectorChunk, ChatMessage
- ✅ **Database Client**: Supabase client wrapper with CRUD operations
- ✅ **Testing Framework**: Pytest configuration with fixtures and mock setup

### Phase 2A: Document Ingestion Pipeline ✅
- ✅ **Docling Integration**: Advanced document processing with semantic chunking
- ✅ **Multi-format Support**: PDF, DOCX, TXT, HTML, MD file processing
- ✅ **Embedding Generation**: OpenAI text-embedding-3-small integration
- ✅ **Vector Storage**: Automatic embedding storage in Supabase pgvector
- ✅ **Error Handling**: Comprehensive error handling and logging

### Phase 2B: Query and Retrieval System ✅
- ✅ **Vector Search**: Cosine similarity search with pgvector
- ✅ **Chat Memory**: Conversation context management with rolling window
- ✅ **LLM Integration**: GPT-4o-mini for response generation
- ✅ **Citation Support**: Source attribution and metadata handling
- ✅ **Async Processing**: Asynchronous query processing

### Phase 2C: Streamlit Frontend ✅
- ✅ **User Authentication**: Supabase Auth integration with session management
- ✅ **File Upload Interface**: Multi-file drag-and-drop with progress tracking
- ✅ **Document Management**: Document library with stats and delete functionality
- ✅ **Chat Interface**: Interactive chat with message history and citations
- ✅ **Responsive Design**: Modern UI with custom styling and theming

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

### 4. Run the Application

```bash
# Launch the Streamlit web application
python run_streamlit.py

# Or run directly with streamlit
streamlit run streamlit_app.py

# The app will open at http://localhost:8501
```

### 5. Using the Application

1. **Sign Up/Sign In**: Create an account or sign in with existing credentials
2. **Upload Documents**: Use the sidebar to upload PDF, DOCX, TXT, HTML, or MD files
3. **Manage Documents**: View your document library and manage uploaded files
4. **Ask Questions**: Use the chat interface to query your documents
5. **View Sources**: See citations and source references for AI responses

### 6. Run Tests

```bash
# Run unit tests
pytest tests/ -m "not integration"

# Run all tests (requires database connection)
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run Streamlit component tests
pytest tests/test_streamlit_app.py
```

## Project Structure

```
rag_ai_agent/
├── streamlit_app.py       # Main Streamlit application
├── run_streamlit.py       # Launch script
├── src/                   # Source code
│   ├── ui/               # Streamlit UI components
│   │   ├── auth.py       # Authentication components
│   │   ├── file_upload.py # File upload interface
│   │   ├── document_manager.py # Document management
│   │   └── chat_interface.py # Chat interface
│   ├── config.py         # Configuration management
│   ├── models.py         # Data models
│   ├── db.py            # Database client
│   ├── ingest.py        # Document ingestion pipeline
│   ├── docling_converter.py # Document conversion
│   ├── docling_chunker.py # Document chunking
│   ├── embeddings.py    # Embedding generation
│   ├── query.py         # Vector search and retrieval
│   ├── chat.py          # LLM orchestration
│   └── memory.py        # Chat memory management
├── tests/               # Test suite
│   ├── conftest.py      # Test fixtures
│   ├── test_*.py        # Component tests
│   └── test_streamlit_app.py # Streamlit tests
├── .streamlit/          # Streamlit configuration
│   └── config.toml      # App configuration
├── supabase/
│   └── migrations/      # Database migrations
├── docs/                # Documentation
│   └── features/        # Implementation plans
├── requirements.txt     # Dependencies
├── pyproject.toml      # Project configuration
└── README.md           # This file
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
