"""
File upload interface and handlers for Streamlit frontend.

This module provides multi-file upload functionality with progress indicators,
file type validation, and integration with the document ingestion pipeline.
"""

import streamlit as st
import logging
from typing import List, Dict, Any
from pathlib import Path
import tempfile
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from ..config import settings
from ..ingest import DocumentIngestionPipeline, ConversionResult
from ..models import Document

logger = logging.getLogger(__name__)


class FileUploadManager:
    """Manages file upload and processing operations."""
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.html', '.md', '.htm'}
    
    def __init__(self):
        """Initialize the file upload manager."""
        self.ingestion_pipeline = DocumentIngestionPipeline()
    
    def validate_file(self, uploaded_file) -> tuple[bool, str]:
        """
        Validate uploaded file.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        if uploaded_file is None:
            return False, "No file provided"
        
        # Check file size
        if uploaded_file.size > settings.max_file_size_mb * 1024 * 1024:
            return False, f"File size exceeds {settings.max_file_size_mb}MB limit"
        
        # Check file extension
        file_extension = Path(uploaded_file.name).suffix.lower()
        if file_extension not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file type. Supported types: {', '.join(self.SUPPORTED_EXTENSIONS)}"
        
        return True, "File is valid"
    
    def save_uploaded_file(self, uploaded_file, temp_dir: Path) -> Path:
        """
        Save uploaded file to temporary directory.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            temp_dir: Temporary directory path
            
        Returns:
            Path to saved file
        """
        file_path = temp_dir / uploaded_file.name
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return file_path
    
    def process_file(self, file_path: Path) -> ConversionResult:
        """
        Process a single file through the ingestion pipeline.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            ConversionResult with processing results
        """
        try:
            return self.ingestion_pipeline.ingest_document(str(file_path))
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            from uuid import UUID
            return ConversionResult(
                doc_id=UUID('00000000-0000-0000-0000-000000000000'),
                filename=file_path.name,
                chunks_created=0,
                conversion_status="failed",
                error_message=f"Processing failed: {str(e)}"
            )




def process_uploaded_files(uploaded_files: List, upload_manager: FileUploadManager):
    """
    Process multiple uploaded files with progress tracking.
    
    Args:
        uploaded_files: List of Streamlit uploaded file objects
        upload_manager: FileUploadManager instance
    """
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Progress tracking
        total_files = len(uploaded_files)
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        # Results tracking
        successful_uploads = []
        failed_uploads = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            # Update progress
            progress = (i) / total_files
            progress_bar.progress(progress)
            status_text.text(f"Processing {uploaded_file.name}... ({i + 1}/{total_files})")
            
            # Validate file
            is_valid, validation_message = upload_manager.validate_file(uploaded_file)
            if not is_valid:
                failed_uploads.append({
                    "filename": uploaded_file.name,
                    "error": validation_message
                })
                continue
            
            try:
                # Save file to temporary location
                file_path = upload_manager.save_uploaded_file(uploaded_file, temp_path)
                
                # Process file through ingestion pipeline
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    result = upload_manager.process_file(file_path)
                
                if result.conversion_status == "success":
                    successful_uploads.append({
                        "filename": uploaded_file.name,
                        "doc_id": result.doc_id,
                        "chunks": result.chunks_created,
                        "status": result.conversion_status
                    })
                else:
                    failed_uploads.append({
                        "filename": uploaded_file.name,
                        "error": result.error_message or "Unknown error"
                    })
                    
            except Exception as e:
                logger.error(f"Unexpected error processing {uploaded_file.name}: {e}")
                failed_uploads.append({
                    "filename": uploaded_file.name,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # Complete progress
        progress_bar.progress(1.0)
        status_text.text("Processing complete!")
        
        # Display results
        display_upload_results(successful_uploads, failed_uploads, results_container)


def display_upload_results(successful_uploads: List[Dict], failed_uploads: List[Dict], container):
    """
    Display upload and processing results.
    
    Args:
        successful_uploads: List of successful upload results
        failed_uploads: List of failed upload results  
        container: Streamlit container to display results
    """
    with container:
        st.markdown("### 📊 Upload Results")
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("✅ Successful", len(successful_uploads))
        with col2:
            st.metric("❌ Failed", len(failed_uploads))
        with col3:
            total_chunks = sum(upload["chunks"] for upload in successful_uploads)
            st.metric("📝 Total Chunks", total_chunks)
        
        # Successful uploads
        if successful_uploads:
            st.markdown("#### ✅ Successfully Processed Files")
            for upload in successful_uploads:
                with st.expander(f"📄 {upload['filename']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Document ID:** {upload['doc_id']}")
                        st.write(f"**Chunks Created:** {upload['chunks']}")
                    with col2:
                        st.write(f"**Status:** {upload['status']}")
                        st.write(f"**Processing Complete:** ✅")
        
        # Failed uploads
        if failed_uploads:
            st.markdown("#### ❌ Failed Files")
            for failure in failed_uploads:
                with st.expander(f"❌ {failure['filename']}", expanded=False):
                    st.error(f"**Error:** {failure['error']}")
        
        # Clear file uploader after processing
        if successful_uploads or failed_uploads:
            if st.button("📁 Upload More Files", use_container_width=True):
                # Clear the file uploader by rerunning
                st.rerun()


def show_upload_guidelines():
    """Display upload guidelines and tips."""
    with st.expander("📋 Upload Guidelines", expanded=False):
        st.markdown("""
        ### File Upload Guidelines
        
        **Supported File Types:**
        - 📄 PDF documents (.pdf)
        - 📝 Word documents (.docx)
        - 📃 Text files (.txt)
        - 🌐 HTML files (.html, .htm)
        - 📓 Markdown files (.md)
        
        **File Size & Limits:**
        - Maximum file size: {max_size}MB per file
        - Maximum files per upload: {max_files} files
        - Processing time varies by file size and complexity
        
        **Best Practices:**
        - Use descriptive filenames
        - Ensure text is readable (not scanned images)
        - Upload related documents together
        - Wait for processing to complete before uploading more
        
        **Processing:**
        - Files are automatically processed and indexed
        - Text is extracted and split into searchable chunks
        - You can chat with your documents immediately after upload
        """.format(
            max_size=settings.max_file_size_mb,
            max_files=settings.max_files_per_upload
        ))


def render_file_upload():
    """Main function to render the complete file upload interface."""
    # Show upload guidelines
    show_upload_guidelines()
    
    # Main upload interface
    upload_manager = FileUploadManager()
    
    # File uploader widget
    uploaded_files = st.file_uploader(
        "Choose files to upload",
        type=[ext.lstrip('.') for ext in upload_manager.SUPPORTED_EXTENSIONS],
        accept_multiple_files=True,
        help=f"Supported formats: {', '.join(upload_manager.SUPPORTED_EXTENSIONS)}. Max {settings.max_file_size_mb}MB per file.",
        key="main_file_uploader"
    )
    
    if uploaded_files:
        # Validate number of files
        if len(uploaded_files) > settings.max_files_per_upload:
            st.error(f"Too many files selected. Maximum allowed: {settings.max_files_per_upload}")
            return
        
        # Display selected files preview
        st.markdown("#### 📋 Selected Files")
        
        valid_files = []
        for i, file in enumerate(uploaded_files):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"📄 {file.name}")
            with col2:
                st.write(f"{file.size / 1024:.1f} KB")
            with col3:
                is_valid, message = upload_manager.validate_file(file)
                if is_valid:
                    st.success("✓ Valid")
                    valid_files.append(file)
                else:
                    st.error("✗ Invalid")
            with col4:
                if not upload_manager.validate_file(file)[0]:
                    st.caption(upload_manager.validate_file(file)[1])
        
        # Show upload button only if there are valid files
        if valid_files:
            st.markdown("---")
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("🚀 Upload and Process Files", use_container_width=True, type="primary"):
                    process_uploaded_files(valid_files, upload_manager)
            with col2:
                st.metric("Valid Files", len(valid_files))
        else:
            st.warning("No valid files selected. Please check the file requirements above.")
