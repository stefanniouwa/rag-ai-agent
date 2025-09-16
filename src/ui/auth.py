"""
Authentication components for Streamlit frontend using Supabase Auth.

This module provides user authentication functionality including login, logout,
signup, and session management using Supabase authentication services.
"""

import streamlit as st
import logging
from typing import Optional, Dict, Any
from supabase import Client
from supabase.lib.client_options import ClientOptions
from supabase import create_client
import uuid

from ..config import settings

logger = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication with Supabase."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        # Create Supabase client with anon key for auth operations
        options = ClientOptions(
            postgrest_client_timeout=settings.supabase_timeout_seconds,
        )
        
        self.client: Client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_anon_key,
            options=options
        )
    
    def sign_up(self, email: str, password: str) -> tuple[bool, str]:
        """
        Sign up a new user.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            
            if response.user:
                logger.info(f"User signed up successfully: {email}")
                return True, "Account created successfully! Please check your email for verification."
            else:
                logger.warning(f"Sign up failed for {email}: No user returned")
                return False, "Failed to create account. Please try again."
                
        except Exception as e:
            logger.error(f"Sign up error for {email}: {e}")
            return False, f"Sign up error: {str(e)}"
    
    def sign_in(self, email: str, password: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Sign in an existing user.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Tuple of (success: bool, message: str, user_data: Optional[Dict])
        """
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                logger.info(f"User signed in successfully: {email}")
                return True, "Signed in successfully!", {
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "session": response.session
                }
            else:
                logger.warning(f"Sign in failed for {email}: Invalid credentials")
                return False, "Invalid email or password.", None
                
        except Exception as e:
            logger.error(f"Sign in error for {email}: {e}")
            return False, f"Sign in error: {str(e)}", None
    
    def sign_out(self) -> tuple[bool, str]:
        """
        Sign out the current user.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.client.auth.sign_out()
            logger.info("User signed out successfully")
            return True, "Signed out successfully!"
            
        except Exception as e:
            logger.error(f"Sign out error: {e}")
            return False, f"Sign out error: {str(e)}"
    
    def reset_password(self, email: str) -> tuple[bool, str]:
        """
        Send password reset email.
        
        Args:
            email: User email address
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.client.auth.reset_password_email(email)
            logger.info(f"Password reset email sent to: {email}")
            return True, "Password reset email sent! Check your inbox."
            
        except Exception as e:
            logger.error(f"Password reset error for {email}: {e}")
            return False, f"Password reset error: {str(e)}"


# Global auth manager instance
_auth_manager: Optional[AuthManager] = None

def get_auth_manager() -> AuthManager:
    """Get or create global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def render_auth_flow() -> bool:
    """
    Render the authentication flow UI.
    
    Returns:
        bool: True if user is authenticated, False otherwise
    """
    auth_manager = get_auth_manager()
    
    # Check if user is already authenticated
    if st.session_state.get("authenticated", False):
        return True
    
    # Authentication tabs
    tab1, tab2, tab3 = st.tabs(["🔑 Sign In", "📝 Sign Up", "🔄 Reset Password"])
    
    with tab1:
        render_sign_in_form(auth_manager)
    
    with tab2:
        render_sign_up_form(auth_manager)
    
    with tab3:
        render_reset_password_form(auth_manager)
    
    return st.session_state.get("authenticated", False)


def render_sign_in_form(auth_manager: AuthManager):
    """Render the sign in form."""
    st.subheader("Sign In to Your Account")
    
    with st.form("sign_in_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("Sign In", use_container_width=True)
        
        if submit_button:
            if not email or not password:
                st.error("Please enter both email and password.")
                return
            
            with st.spinner("Signing in..."):
                success, message, user_data = auth_manager.sign_in(email, password)
            
            if success and user_data:
                st.success(message)
                
                # Set session state
                st.session_state.authenticated = True
                st.session_state.user_id = user_data["user_id"]
                st.session_state.user_email = user_data["email"]
                st.session_state.session_id = str(uuid.uuid4())
                
                # Rerun to show main app
                st.rerun()
            else:
                st.error(message)


def render_sign_up_form(auth_manager: AuthManager):
    """Render the sign up form."""
    st.subheader("Create New Account")
    
    with st.form("sign_up_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Choose a strong password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        submit_button = st.form_submit_button("Create Account", use_container_width=True)
        
        if submit_button:
            if not email or not password or not confirm_password:
                st.error("Please fill in all fields.")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            
            if len(password) < 8:
                st.error("Password must be at least 8 characters long.")
                return
            
            with st.spinner("Creating account..."):
                success, message = auth_manager.sign_up(email, password)
            
            if success:
                st.success(message)
                st.info("You can now sign in with your credentials.")
            else:
                st.error(message)


def render_reset_password_form(auth_manager: AuthManager):
    """Render the password reset form."""
    st.subheader("Reset Password")
    
    with st.form("reset_password_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        submit_button = st.form_submit_button("Send Reset Email", use_container_width=True)
        
        if submit_button:
            if not email:
                st.error("Please enter your email address.")
                return
            
            with st.spinner("Sending reset email..."):
                success, message = auth_manager.reset_password(email)
            
            if success:
                st.success(message)
            else:
                st.error(message)


def logout_user():
    """Logout the current user and clear session state."""
    auth_manager = get_auth_manager()
    
    # Sign out from Supabase
    auth_manager.sign_out()
    
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    # Rerun to show auth flow
    st.rerun()
