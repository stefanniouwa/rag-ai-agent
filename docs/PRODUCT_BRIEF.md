# Product Brief: Streamlit RAG AI Agent Webapp

## 1. Project Overview / Description

A single-user document intelligence webapp that allows users to upload personal documents (PDF, DOCX, TXT, HTML, MD), automatically processes them into a searchable knowledge base, and provides an AI-powered chat interface to query across their entire document corpus. The system returns contextual answers with citations and source snippets, creating a personal AI assistant for document research and knowledge retrieval.

## 2. Target Audience

- Individual knowledge workers, researchers, and students
- Professionals managing large document collections
- Anyone needing to quickly search and extract insights from personal document libraries
- Users comfortable with simple web interfaces who value data privacy

## 3. Primary Benefits / Features

- **Document Ingestion**: Upload multiple file formats with automatic text extraction and processing
- **Intelligent Search**: Natural language queries across entire document collection
- **Contextual Answers**: AI-generated responses with source citations and relevant snippets
- **Document Management**: View uploaded files and manage document library
- **Chat Memory**: Maintains conversation context for follow-up questions
- **Secure Access**: User authentication to protect personal documents
- **Easy Deployment**: One-click deployment to Streamlit Cloud

## 4. High-Level Tech/Architecture

- **Frontend**: Streamlit web application with file upload, document management, and chat interface
- **Backend**: Python modules for document processing, vector search, and AI orchestration
- **Database**: Supabase with pgvector extension for vector storage and metadata
- **AI Services**: OpenAI APIs for embeddings (text-embedding-3-small) and chat completion (GPT-4.1-mini)
- **Deployment**: Streamlit Cloud with environment variable configuration
- **Development**: Test-driven development approach with comprehensive unit, integration, and E2E testing
