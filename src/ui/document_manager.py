"""
Document management UI for Streamlit frontend.

This module provides document listing, metadata display, and delete functionality
for managing the user's document library.
"""

import streamlit as st
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from ..db import get_db_client, SupabaseClient
from ..models import Document, VectorChunk
from ..config import settings

logger = logging.getLogger(__name__)


class DocumentManager:
    """Manages document operations for the UI."""
    
    def __init__(self):
        """Initialize the document manager."""
        self.db_client = get_db_client()
    
    def get_all_documents(self) -> List[Document]:
        """
        Get all documents from the database.
        
        Returns:
            List of Document objects
        """
        try:
            return self.db_client.list_documents()
        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return []
    
    def get_document_stats(self, doc_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary with document statistics
        """
        try:
            chunks = self.db_client.get_document_vectors(doc_id)
            
            return {
                "chunk_count": len(chunks),
                "total_content_length": sum(len(chunk.content) for chunk in chunks),
                "avg_chunk_length": sum(len(chunk.content) for chunk in chunks) / len(chunks) if chunks else 0,
                "has_embeddings": all(chunk.embedding is not None for chunk in chunks)
            }
        except Exception as e:
            logger.error(f"Error getting document stats for {doc_id}: {e}")
            return {
                "chunk_count": 0,
                "total_content_length": 0,
                "avg_chunk_length": 0,
                "has_embeddings": False
            }
    
    def delete_document(self, doc_id: str) -> tuple[bool, str]:
        """
        Delete a document and all its associated data.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            success = self.db_client.delete_document(doc_id)
            if success:
                logger.info(f"Document deleted successfully: {doc_id}")
                return True, "Document deleted successfully!"
            else:
                logger.warning(f"Failed to delete document: {doc_id}")
                return False, "Failed to delete document."
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False, f"Error deleting document: {str(e)}"
    
    def delete_multiple_documents(self, doc_ids: List[str]) -> Dict[str, Any]:
        """
        Delete multiple documents.
        
        Args:
            doc_ids: List of document IDs to delete
            
        Returns:
            Dictionary with deletion results
        """
        results = {
            "successful": [],
            "failed": [],
            "total": len(doc_ids)
        }
        
        for doc_id in doc_ids:
            success, message = self.delete_document(doc_id)
            if success:
                results["successful"].append(doc_id)
            else:
                results["failed"].append({"doc_id": doc_id, "error": message})
        
        return results




def render_document_list(documents: List[Document], doc_manager: DocumentManager):
    """Render documents as a simple list with basic operations."""
    
    # Bulk operations
    st.markdown("#### 🗂️ Document Library")
    
    # Select all checkbox
    select_all = st.checkbox("Select all documents")
    
    selected_docs = []
    
    # Document list
    for i, doc in enumerate(documents):
        col1, col2, col3, col4 = st.columns([0.5, 3, 1.5, 1])
        
        with col1:
            # Individual checkbox
            selected = st.checkbox(
                f"Select {doc.filename}", 
                value=select_all,
                key=f"doc_select_{doc.id}",
                label_visibility="collapsed"
            )
            if selected:
                selected_docs.append(doc)
        
        with col2:
            st.write(f"📄 **{doc.filename}**")
            st.caption(f"Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
        
        with col3:
            # Get document stats
            stats = doc_manager.get_document_stats(str(doc.id))
            st.write(f"📝 {stats['chunk_count']} chunks")
        
        with col4:
            if st.button("🗑️", key=f"delete_{doc.id}", help="Delete document"):
                delete_single_document(doc, doc_manager)
    
    # Bulk delete operation
    if selected_docs:
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{len(selected_docs)} documents selected**")
        
        with col2:
            if st.button("🗑️ Delete Selected", use_container_width=True, type="primary"):
                delete_multiple_documents(selected_docs, doc_manager)
        
        with col3:
            if st.button("❌ Clear Selection", use_container_width=True):
                st.rerun()


def render_document_details(documents: List[Document], doc_manager: DocumentManager):
    """Render documents with detailed information and statistics."""
    
    st.markdown("#### 📊 Detailed Document View")
    
    # Create a dataframe for better visualization
    doc_data = []
    for doc in documents:
        stats = doc_manager.get_document_stats(str(doc.id))
        doc_data.append({
            "Document": doc.filename,
            "Uploaded": doc.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            "Chunks": stats['chunk_count'],
            "Content Size": f"{stats['total_content_length']:,} chars",
            "Avg Chunk Size": f"{stats['avg_chunk_length']:.0f} chars",
            "Embeddings": "✓" if stats['has_embeddings'] else "✗",
            "ID": str(doc.id)
        })
    
    if doc_data:
        df = pd.DataFrame(doc_data)
        
        # Display the dataframe
        st.dataframe(
            df.drop('ID', axis=1),  # Hide ID column from display
            use_container_width=True,
            hide_index=True
        )
        
        # Document actions
        st.markdown("---")
        st.markdown("#### 🛠️ Document Actions")
        
        # Document selection for actions
        selected_doc = st.selectbox(
            "Select a document for actions:",
            options=[(doc['Document'], doc['ID']) for doc in doc_data],
            format_func=lambda x: x[0],
            index=None
        )
        
        if selected_doc:
            doc_name, doc_id = selected_doc
            selected_document = next((doc for doc in documents if str(doc.id) == doc_id), None)
            
            if selected_document:
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("📊 View Details", use_container_width=True):
                        show_document_details(selected_document, doc_manager)
                
                with col2:
                    if st.button("🗑️ Delete", use_container_width=True, type="primary"):
                        delete_single_document(selected_document, doc_manager)
                
                with col3:
                    st.write("")  # Spacer


def show_document_details(document: Document, doc_manager: DocumentManager):
    """Show detailed information about a specific document."""
    
    with st.expander(f"📄 Details for {document.filename}", expanded=True):
        # Basic information
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Basic Information:**")
            st.write(f"• **Filename:** {document.filename}")
            st.write(f"• **Document ID:** {document.id}")
            st.write(f"• **Upload Date:** {document.uploaded_at}")
        
        with col2:
            st.markdown("**Processing Statistics:**")
            stats = doc_manager.get_document_stats(str(document.id))
            st.write(f"• **Total Chunks:** {stats['chunk_count']}")
            st.write(f"• **Content Length:** {stats['total_content_length']:,} characters")
            st.write(f"• **Average Chunk Size:** {stats['avg_chunk_length']:.0f} characters")
            st.write(f"• **Embeddings Status:** {'✓ Complete' if stats['has_embeddings'] else '✗ Missing'}")
        
        # Show some sample chunks
        if stats['chunk_count'] > 0:
            st.markdown("**Sample Content:**")
            try:
                from uuid import UUID
                chunks = doc_manager.db_client.get_document_vectors(UUID(str(document.id)))
                if chunks:
                    # Show first few chunks
                    for i, chunk in enumerate(chunks[:3]):
                        with st.expander(f"Chunk {chunk.chunk_id}", expanded=False):
                            st.text(chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content)
                    
                    if len(chunks) > 3:
                        st.caption(f"... and {len(chunks) - 3} more chunks")
            except Exception as e:
                st.error(f"Error loading chunks: {e}")


def delete_single_document(document: Document, doc_manager: DocumentManager):
    """Handle deletion of a single document with confirmation."""
    
    # Use session state to track deletion confirmation
    confirm_key = f"confirm_delete_{document.id}"
    
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    
    if not st.session_state[confirm_key]:
        # Show confirmation dialog
        st.warning(f"Are you sure you want to delete **{document.filename}**?")
        st.caption("This action cannot be undone. All document chunks and embeddings will be permanently removed.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete", key=f"confirm_yes_{document.id}", type="primary"):
                st.session_state[confirm_key] = True
                st.rerun()
        with col2:
            if st.button("❌ Cancel", key=f"confirm_no_{document.id}"):
                st.info("Deletion cancelled.")
    else:
        # Perform deletion
        with st.spinner(f"Deleting {document.filename}..."):
            success, message = doc_manager.delete_document(str(document.id))
        
        if success:
            st.success(message)
            # Clear confirmation state
            del st.session_state[confirm_key]
            st.rerun()
        else:
            st.error(message)
            # Reset confirmation state
            st.session_state[confirm_key] = False


def delete_multiple_documents(documents: List[Document], doc_manager: DocumentManager):
    """Handle deletion of multiple documents with confirmation."""
    
    # Use session state to track deletion confirmation
    confirm_key = "confirm_bulk_delete"
    
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    
    if not st.session_state[confirm_key]:
        # Show confirmation dialog
        st.warning(f"Are you sure you want to delete **{len(documents)} documents**?")
        st.caption("This action cannot be undone. All document chunks and embeddings will be permanently removed.")
        
        # Show list of documents to be deleted
        with st.expander("Documents to be deleted:", expanded=False):
            for doc in documents:
                st.write(f"• {doc.filename}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete All", key="confirm_bulk_yes", type="primary"):
                st.session_state[confirm_key] = True
                st.rerun()
        with col2:
            if st.button("❌ Cancel", key="confirm_bulk_no"):
                st.info("Bulk deletion cancelled.")
    else:
        # Perform bulk deletion
        doc_ids = [str(doc.id) for doc in documents]
        
        with st.spinner(f"Deleting {len(documents)} documents..."):
            results = doc_manager.delete_multiple_documents(doc_ids)
        
        # Show results
        if results["successful"]:
            st.success(f"Successfully deleted {len(results['successful'])} documents!")
        
        if results["failed"]:
            st.error(f"Failed to delete {len(results['failed'])} documents:")
            for failure in results["failed"]:
                st.write(f"• {failure['doc_id']}: {failure['error']}")
        
        # Clear confirmation state
        del st.session_state[confirm_key]
        st.rerun()


def render_document_statistics():
    """Render overall document library statistics."""
    doc_manager = DocumentManager()
    documents = doc_manager.get_all_documents()
    
    if not documents:
        return
    
    # Calculate overall statistics
    total_docs = len(documents)
    total_chunks = 0
    total_size = 0
    docs_with_embeddings = 0
    
    for doc in documents:
        stats = doc_manager.get_document_stats(str(doc.id))
        total_chunks += stats['chunk_count']
        total_size += stats['total_content_length']
        if stats['has_embeddings']:
            docs_with_embeddings += 1
    
    # Display statistics
    st.markdown("#### 📈 Library Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", total_docs)
    
    with col2:
        st.metric("Total Chunks", f"{total_chunks:,}")
    
    with col3:
        st.metric("Content Size", f"{total_size:,} chars")
    
    with col4:
        embedding_percentage = (docs_with_embeddings / total_docs * 100) if total_docs > 0 else 0
        st.metric("Embeddings Complete", f"{embedding_percentage:.0f}%")


def render_document_manager():
    """Main function to render the complete document management interface."""
    
    # Overall statistics
    render_document_statistics()
    
    # Main document management interface
    doc_manager = DocumentManager()
    documents = doc_manager.get_all_documents()
    
    if not documents:
        st.info("📭 No documents uploaded yet.")
        st.markdown("Use the **Upload Documents** section above to add documents to your library.")
        return
    
    # Document management tabs
    tab1, tab2 = st.tabs(["📋 Manage Documents", "📊 Statistics"])
    
    with tab1:
        # Document list display options
        display_mode = st.radio(
            "View Mode:",
            ["List View", "Detailed View"],
            horizontal=True
        )
        
        if display_mode == "List View":
            render_document_list(documents, doc_manager)
        else:
            render_document_details(documents, doc_manager)
    
    with tab2:
        render_document_statistics()
        
        # Additional analytics could go here
        st.markdown("#### 📅 Upload Timeline")
        if documents:
            # Create a simple timeline visualization
            upload_dates = [doc.uploaded_at.date() for doc in documents]
            upload_counts = pd.Series(upload_dates).value_counts().sort_index()
            
            if len(upload_counts) > 0:
                st.bar_chart(upload_counts)
            else:
                st.info("No upload timeline data available.")
