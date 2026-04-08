"""
Shared database authentication for Authorization Bypass backends.
Connects to the same database as the original backend.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import from backend
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import the original database connection
from database import connect_to_db, handle_student_login

def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate user against the real database.
    Returns user data with role, or None if authentication fails.
    """
    return handle_student_login(username, password)
