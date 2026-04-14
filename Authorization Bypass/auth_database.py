import sys
from pathlib import Path
import secrets


backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))


from database import connect_to_db
from sql_injection_prevention.secure_auth import authenticate_login_attempt


_token_store = {}


def authenticate_user(username: str, password: str) -> dict:
    attempt = authenticate_login_attempt(username, password, detect_sql_injection=True)
    return attempt.user if attempt.status == "success" else None


def create_session_token(username: str, role: str) -> str:
    token = secrets.token_urlsafe(32)
    _token_store[token] = {"username": username, "role": role}
    return token


def verify_session_token(token: str) -> dict | None:
    if token in _token_store:
        return _token_store[token]
    return None


def verify_user_role(username: str, claimed_role: str) -> bool:
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
