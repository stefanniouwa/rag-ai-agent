#!/usr/bin/env python3
"""Validation script for Phase 1 implementation."""

import sys
import os
from pathlib import Path

def validate_project_structure():
    """Validate that all required files and directories exist."""
    print("🔍 Validating project structure...")
    
    required_files = [
        "requirements.txt",
        "pyproject.toml", 
        "pytest.ini",
        "README.md",
        "env.example",
        "src/__init__.py",
        "src/config.py",
        "src/models.py", 
        "src/db.py",
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/test_db.py",
        "supabase/migrations/001_initial_schema.sql"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def validate_imports():
    """Validate that our modules can be imported successfully."""
    print("🔍 Validating module imports...")
    
    try:
        # Test basic imports without external dependencies
        sys.path.insert(0, str(Path.cwd()))
        
        # Set test environment variables
        os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
        os.environ.setdefault("SUPABASE_ANON_KEY", "test-key")
        os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-key")
        os.environ.setdefault("OPENAI_API_KEY", "test-key")
        
        # Import and validate our models
        from src.models import Document, VectorChunk, ChatMessage
        print("✅ Data models imported successfully")
        
        # Import configuration
        from src.config import Settings, get_settings
        settings = get_settings()
        print("✅ Configuration loaded successfully")
        
        # Test model creation (without database)
        from uuid import uuid4
        from datetime import datetime
        
        doc = Document(
            id=uuid4(),
            filename="test.pdf",
            uploaded_at=datetime.now()
        )
        print(f"✅ Document model created: {doc.filename}")
        
        vector = VectorChunk(
            id=uuid4(),
            doc_id=doc.id,
            chunk_id=0,
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
            metadata={"page": 1}
        )
        print(f"✅ VectorChunk model created: {len(vector.content)} chars")
        
        chat = ChatMessage(
            session_id="test-session",
            turn_index=1,
            user_message="Test question",
            ai_response="Test response"
        )
        print(f"✅ ChatMessage model created: session {chat.session_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def validate_sql_migration():
    """Validate SQL migration file."""
    print("🔍 Validating SQL migration...")
    
    migration_file = Path("supabase/migrations/001_initial_schema.sql")
    if not migration_file.exists():
        print("❌ Migration file not found")
        return False
    
    content = migration_file.read_text()
    
    required_elements = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        "CREATE TABLE documents",
        "CREATE TABLE vectors", 
        "CREATE TABLE chat_histories",
        "vector_search",
        "VECTOR(1536)",
        "pgvector"
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ Missing SQL elements: {missing_elements}")
        return False
    
    print("✅ SQL migration contains all required elements")
    return True

def validate_dependencies():
    """Validate that requirements.txt contains all necessary dependencies."""
    print("🔍 Validating dependencies...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        return False
    
    content = requirements_file.read_text()
    
    required_deps = [
        "streamlit",
        "supabase", 
        "openai",
        "docling",
        "transformers",
        "pydantic",
        "pytest"
    ]
    
    missing_deps = []
    for dep in required_deps:
        if dep not in content:
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"❌ Missing dependencies: {missing_deps}")
        return False
    
    print("✅ All required dependencies present")
    return True

def main():
    """Run all validation checks."""
    print("🚀 Phase 1 Implementation Validation")
    print("=" * 40)
    
    checks = [
        validate_project_structure,
        validate_dependencies,
        validate_sql_migration,
        validate_imports
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed with error: {e}")
            results.append(False)
        print()
    
    print("=" * 40)
    if all(results):
        print("🎉 Phase 1 implementation validation: SUCCESS!")
        print("✅ Ready to proceed to Phase 2A (Document Ingestion)")
        return 0
    else:
        print("❌ Phase 1 implementation validation: FAILED!")
        print(f"Passed: {sum(results)}/{len(results)} checks")
        return 1

if __name__ == "__main__":
    sys.exit(main())
