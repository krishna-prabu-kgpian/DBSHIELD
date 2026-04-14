"""
Shared database authentication for Authorization Bypass backends.
Implements token-based authentication to prevent header spoofing.
"""

import sys
from pathlib import Path
import secrets

# Add parent directory to path so we can import from backend
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import the original database connection
from database import connect_to_db
from sql_injection_prevention.secure_auth import authenticate_login_attempt

# Simple in-memory token store (in production, use database)
# Format: {token: {username, role, created_at}}
_token_store = {}


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate user against the real database.
    Returns user data with role, or None if authentication fails.
    """
    attempt = authenticate_login_attempt(username, password, detect_sql_injection=True)
    return attempt.user if attempt.status == "success" else None


def create_session_token(username: str, role: str) -> str:
    """
    Create a session token for authenticated user.
    This proves the user has logged in with valid credentials.
    
    Args:
        username: The authenticated username
        role: The user's role
    
    Returns:
        A secure token string
    """
    token = secrets.token_urlsafe(32)
    _token_store[token] = {"username": username, "role": role}
    return token


def verify_session_token(token: str) -> dict | None:
    """
    Verify a session token is valid and return user info.
    
    Args:
        token: The session token from the request
    
    Returns:
        Dict with {username, role} if valid, None otherwise
    """
    if token in _token_store:
        return _token_store[token]
    return None


def verify_user_role(username: str, claimed_role: str) -> bool:
    """
    Verify that a user exists in the database with the claimed role.
    This is a fallback for header-based auth (for demo purposes).
    
    Args:
        username: The claimed username
        claimed_role: The claimed role
    
    Returns:
        True if user exists with that exact role, False otherwise
    """
    try:
        conn = connect_to_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
        finally:
            conn.close()

        if result:
            actual_role = str(result["role"]).lower()
            return actual_role == claimed_role.lower()
        return False
    except Exception as e:
        print(f"Error verifying user role: {e}")
        return False
    
    return False
