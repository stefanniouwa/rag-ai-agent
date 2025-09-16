"""
Phase 2A: Document Ingestion Pipeline that ingests a single document and prints the status and number of chunks created. You can check the status and details of the document in the Supabase dashboard."
"""
from src.ingest import ingest_document

# Ingest a single document
result = ingest_document("/Users/stefn/Interlinked/rag_ai_agent/StefanNio_AI_EngineerResume1.pdf")
print(f"Status: {result.conversion_status}")
print(f"Chunks created: {result.chunks_created}")