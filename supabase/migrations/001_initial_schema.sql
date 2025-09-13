-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Create documents table for file metadata
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create vectors table for storing document chunks and embeddings
CREATE TABLE vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small dimension
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create chat_histories table for conversation memory
CREATE TABLE chat_histories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for optimal query performance

-- Index for document lookups
CREATE INDEX idx_documents_filename ON documents(filename);
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at DESC);

-- Indexes for vector operations
CREATE INDEX idx_vectors_doc_id ON vectors(doc_id);
CREATE INDEX idx_vectors_chunk_id ON vectors(doc_id, chunk_id);

-- Vector similarity search index using ivfflat
-- Note: This requires data to be present for optimal performance
-- Consider creating this index after initial data load in production
CREATE INDEX idx_vectors_embedding ON vectors USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Indexes for chat history
CREATE INDEX idx_chat_histories_session_id ON chat_histories(session_id);
CREATE INDEX idx_chat_histories_session_turn ON chat_histories(session_id, turn_index);
CREATE INDEX idx_chat_histories_created_at ON chat_histories(created_at DESC);

-- Create RPC function for vector similarity search
CREATE OR REPLACE FUNCTION vector_search(
    query_embedding VECTOR(1536),
    match_count INTEGER DEFAULT 4
)
RETURNS TABLE (
    id UUID,
    doc_id UUID,
    chunk_id INTEGER,
    content TEXT,
    embedding VECTOR(1536),
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        v.id,
        v.doc_id,
        v.chunk_id,
        v.content,
        v.embedding,
        v.metadata,
        1 - (v.embedding <=> query_embedding) AS similarity
    FROM vectors v
    WHERE v.embedding IS NOT NULL
    ORDER BY v.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Create function to get document statistics
CREATE OR REPLACE FUNCTION get_document_stats(doc_uuid UUID)
RETURNS TABLE (
    document_id UUID,
    filename TEXT,
    chunk_count BIGINT,
    total_content_length BIGINT,
    uploaded_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        d.id,
        d.filename,
        COUNT(v.id) AS chunk_count,
        SUM(LENGTH(v.content)) AS total_content_length,
        d.uploaded_at
    FROM documents d
    LEFT JOIN vectors v ON d.id = v.doc_id
    WHERE d.id = doc_uuid
    GROUP BY d.id, d.filename, d.uploaded_at;
$$;

-- Create function to clean up orphaned vectors (safety measure)
CREATE OR REPLACE FUNCTION cleanup_orphaned_vectors()
RETURNS INTEGER
LANGUAGE SQL
AS $$
    WITH deleted AS (
        DELETE FROM vectors 
        WHERE doc_id NOT IN (SELECT id FROM documents)
        RETURNING id
    )
    SELECT COUNT(*)::INTEGER FROM deleted;
$$;

-- Create function to get chat session summary
CREATE OR REPLACE FUNCTION get_chat_session_summary(session_id_param TEXT)
RETURNS TABLE (
    session_id TEXT,
    message_count BIGINT,
    first_message_at TIMESTAMP WITH TIME ZONE,
    last_message_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        ch.session_id,
        COUNT(*) AS message_count,
        MIN(ch.created_at) AS first_message_at,
        MAX(ch.created_at) AS last_message_at
    FROM chat_histories ch
    WHERE ch.session_id = session_id_param
    GROUP BY ch.session_id;
$$;

-- Add constraints for data integrity
ALTER TABLE vectors 
ADD CONSTRAINT vectors_chunk_id_positive CHECK (chunk_id >= 0);

ALTER TABLE chat_histories 
ADD CONSTRAINT chat_histories_turn_index_positive CHECK (turn_index >= 0);

-- Add unique constraint for chat turn ordering within sessions
ALTER TABLE chat_histories 
ADD CONSTRAINT chat_histories_session_turn_unique UNIQUE (session_id, turn_index);

-- Add comments for documentation
COMMENT ON TABLE documents IS 'Stores metadata for uploaded documents';
COMMENT ON TABLE vectors IS 'Stores document chunks with vector embeddings for similarity search';
COMMENT ON TABLE chat_histories IS 'Stores conversation history for RAG chat sessions';

COMMENT ON COLUMN vectors.embedding IS 'Vector embedding from OpenAI text-embedding-3-small (1536 dimensions)';
COMMENT ON COLUMN vectors.metadata IS 'Additional metadata like page numbers, section headers, etc.';
COMMENT ON COLUMN chat_histories.session_id IS 'Unique identifier for chat session, typically user-based';
COMMENT ON COLUMN chat_histories.turn_index IS 'Sequential turn number within a session';

-- Grant necessary permissions (adjust based on your RLS policies)
-- These are basic permissions; you may want to implement Row Level Security (RLS)
-- for multi-tenant scenarios

-- Allow authenticated users to perform CRUD operations
GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON vectors TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON chat_histories TO authenticated;

-- Allow usage of sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Allow execution of custom functions
GRANT EXECUTE ON FUNCTION vector_search TO authenticated;
GRANT EXECUTE ON FUNCTION get_document_stats TO authenticated;
GRANT EXECUTE ON FUNCTION get_chat_session_summary TO authenticated;

-- Admin function (restrict to service role)
GRANT EXECUTE ON FUNCTION cleanup_orphaned_vectors TO service_role;
