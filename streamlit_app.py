"""
Streamlit Frontend for RAG AI Agent

This is the main entry point for the Streamlit web application that provides
user authentication, file upload interface, document management, and chat interface.
"""

import streamlit as st
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from src.ui.auth import render_auth_flow
from src.ui.file_upload import render_file_upload
from src.ui.document_manager import render_document_manager 
from src.ui.chat_interface import render_chat_interface
from src.config import settings

# Page configuration
st.set_page_config(
    page_title="RAG AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "# RAG AI Agent\nYour personal document intelligence assistant"
    }
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 2rem;
    }
    
    .sidebar-section {
        padding: 1rem 0;
        border-bottom: 1px solid #f0f2f6;
        margin-bottom: 1rem;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
        border-left: 4px solid #ff4b4b;
    }
    
    .user-message {
        background-color: #f0f2f6;
        border-left-color: #ff4b4b;
    }
    
    .ai-message {
        background-color: #e8f4f8;
        border-left-color: #00c0f2;
    }
    
    .citation {
        background-color: #fafafa;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
        border: 1px solid #e0e0e0;
        font-size: 0.9rem;
    }
    
    .file-upload-area {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    .upload-success {
        background-color: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.25rem;
        border: 1px solid #c3e6cb;
        margin: 0.5rem 0;
    }
    
    .upload-error {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.25rem;
        border: 1px solid #f5c6cb;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application function."""
    
    # Initialize session state for authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    
    # Main header
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("🤖 RAG AI Agent")
    st.markdown("*Your personal document intelligence assistant*")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Authentication flow
    if not st.session_state.authenticated:
        # Show authentication interface
        render_auth_flow()
    else:
        # Show main application interface
        render_main_app()

def render_main_app():
    """Render the main application interface for authenticated users."""
    
    # Sidebar for file upload and document management
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.header("📁 Document Management")
        
        # File upload section
        st.subheader("Upload Documents")
        render_file_upload()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Document library section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("Document Library")
        render_document_manager()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Session management
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("Session")
        
        if st.button("🆕 New Chat Session", use_container_width=True):
            # Reset chat session
            if "session_id" in st.session_state:
                st.session_state.session_id = None
            if "chat_history" in st.session_state:
                del st.session_state.chat_history
            st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # User info
        st.markdown("---")
        st.markdown(f"**User:** {st.session_state.user_email}")
        st.markdown(f"**Environment:** {settings.environment}")
    
    # Main content area - Chat interface
    st.header("💬 Chat with Your Documents")
    render_chat_interface()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}")
        st.error(f"An error occurred: {e}")
        
        # Show debug info in development
        if settings.environment == "development":
            st.exception(e)
