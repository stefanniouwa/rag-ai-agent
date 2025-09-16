#!/usr/bin/env python3
"""
Launch script for the RAG AI Agent Streamlit application.

This script sets up the environment and launches the Streamlit app with proper configuration.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if required environment variables are set."""
    # Load .env file
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
    else:
        logger.warning("No .env file found. Make sure environment variables are set.")
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY", 
        "SUPABASE_SERVICE_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please set these variables in your .env file or environment")
        if not env_file.exists():
            logger.error(f"Create a .env file at {env_file} with your API keys")
            logger.error("You can copy env.example to .env and fill in your values")
        return False
    
    return True

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import streamlit
        import supabase
        import openai
        from src.config import settings
        logger.info("All dependencies are available")
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main function to launch the Streamlit app."""
    logger.info("🤖 Starting RAG AI Agent...")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Set Streamlit configuration
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    
    # Launch Streamlit
    try:
        logger.info("🚀 Launching Streamlit application...")
        logger.info("📖 The app will open in your default web browser")
        logger.info("🔗 Default URL: http://localhost:8501")
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.headless", "false"
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to launch Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
