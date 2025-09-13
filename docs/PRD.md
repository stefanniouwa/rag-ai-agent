PRD: Streamlit RAG AI Agent Webapp

1. Overview

Build a single-user webapp that ingests local documents (PDF, DOCX, TXT, HTML, MD), chunks + embeds them into Supabase pgvector, and provides a chat interface where the user can query across their personal corpus. Answers include citations with snippet + source metadata. The app will be simple, deployable on Streamlit Cloud, and built with TDD.

⸻

2. Objectives
	•	Ingestion pipeline: Upload docs → chunk → embed → store vectors in Supabase.
	•	Query pipeline: Chat UI → embed query → search vectors → generate answer → return with citations.
	•	Memory: Short-term chat memory (last 5 turns) stored in Supabase.
	•	Document management: View uploaded files; delete file also deletes vectors.
	•	Authentication: Supabase login to protect access.
	•	Deployment: Easy deploy to Streamlit Cloud (env vars for secrets).

⸻

3. Scope

In Scope
	•	Local file upload (PDF, DOCX, TXT, HTML, MD).
	•	Supabase as vector DB (pgvector extension).
	•	OpenAI API (text-embedding-3-small, gpt-4.1-mini or gpt-3.5-turbo for responses).
	•	Streamlit UI:
	•	File uploader & file list
	•	Chat box + response with citations
	•	Login/logout (via Supabase)

Out of Scope (v1)
	•	Multi-user roles
	•	External integrations (Google Drive, Airtable, email)
	•	Advanced monitoring, latency budgets, streaming answers

⸻

4. Architecture

Frontend (Streamlit)
	•	Single-page app with:
	•	File Upload Section
	•	Document Management Table
	•	Chat Interface

Backend (Python modules)
	•	ingest.py → chunk + embed + upsert to Supabase
	•	query.py → embed query, search top-k, return results
	•	chat.py → orchestrates retrieval + LLM answer + formatting with citations
	•	db.py → Supabase client helpers
	•	memory.py → chat memory (context window = 5, stored in Supabase table)

Database (Supabase)
	•	documents (file metadata)
	•	vectors (chunk_id, file_id, embedding, content, metadata)
	•	chat_histories (session_id, turn_id, user_text, ai_text, timestamp)

⸻

5. Data Model (Supabase)

documents
	•	id (UUID, PK)
	•	filename (text)
	•	uploaded_at (timestamp)

vectors
	•	id (UUID, PK)
	•	doc_id (FK → documents.id)
	•	chunk_id (int)
	•	content (text)
	•	embedding (vector[1536])
	•	metadata (JSONB: {page, source})

chat_histories
	•	id (UUID, PK)
	•	session_id (UUID or string)
	•	turn_index (int)
	•	user_message (text)
	•	ai_response (text)
	•	created_at (timestamp)

⸻

6. Key Flows

A. Ingestion
	1.	User uploads file.
	2.	App reads & extracts text.
	3.	Chunk into 1000 chars, 200 overlap.
	4.	Embed chunks → OpenAI embeddings.
	5.	Insert into Supabase vectors + update documents.

B. Query
	1.	User enters question in chat.
	2.	Query embedded → OpenAI.
	3.	Vector search in Supabase (top-k=4).
	4.	Retrieved chunks sent to OpenAI chat model.
	5.	Answer returned with citations.
	6.	User + AI turns logged in chat_histories.

C. Document Management
	•	List uploaded docs.
	•	Delete doc → cascade delete vectors.

⸻

7. TDD Approach
	•	Unit tests
	•	Chunker produces expected splits.
	•	Embedding call returns correct dimensions.
	•	Vector insertion/retrieval shape.
	•	Integration tests
	•	Upload doc → expect correct vector count.
	•	Query doc → expect answer contains at least one citation.
	•	Delete doc → expect vectors removed.
	•	E2E tests (Streamlit)
	•	Simulate file upload + query → answer displayed.
	•	Auth flow test (login required).

Tools: pytest, pytest-asyncio, responses for API mocking, GitHub Actions CI.

⸻

8. Session ID Discussion
	•	Using session_id = user_id:
	•	Pros: persistent across sessions, tied to auth identity.
	•	Cons: no way to separate conversations; could clutter memory.
	•	Using session_id = random per chat session:
	•	Pros: clean separation; useful for testing.
	•	Cons: no persistence across sessions unless exported.

Proposal: use session_id = user_id by default (since single user), but allow “New Session” button in UI to reset context.

⸻

9. Milestones
	1.	Setup (Day 1-2)
	•	Streamlit skeleton
	•	Supabase schema migration
	•	Auth login working
	2.	Ingestion (Day 3-5)
	•	File upload → chunk/embed/upsert
	•	Document table display
	•	Unit + integration tests
	3.	Query (Day 6-8)
	•	Chat UI with OpenAI integration
	•	Vector search + citations
	•	Chat memory
	•	Tests
	4.	Document Management (Day 9-10)
	•	Delete with cascade
	•	Tests
	5.	Polish + CI/CD (Day 11-12)
	•	GitHub Actions CI setup
	•	Deployment to Streamlit Cloud
	•	Final E2E test