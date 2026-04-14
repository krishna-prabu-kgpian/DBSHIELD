from __future__ import annotations

from dataclasses import dataclass
import re

from database import connect_to_db


SQLI_PASSWORD_PATTERN = re.compile(
    r"(--|/\*|\*/|;|\bOR\b|\bUNION\b|\bSELECT\b|\bDROP\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LoginAttemptResult:
    status: str
    user: dict | None = None


def _looks_like_sql_injection(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False

    return bool(SQLI_PASSWORD_PATTERN.search(candidate))


def authenticate_login_attempt(
    username: str,
    password: str,
    *,
    detect_sql_injection: bool = True,
) -> LoginAttemptResult:
    normalized_username = username.strip()

    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, password, role, name, phone
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        )
        result = cursor.fetchone()
    finally:
        conn.close()

    if not result:
        return LoginAttemptResult(status="username_not_found")

    if detect_sql_injection and _looks_like_sql_injection(password):
        return LoginAttemptResult(status="sql_injection_detected")

    user = dict(result)
    if str(user.get("password", "")) != password:
        return LoginAttemptResult(status="invalid_password")

    return LoginAttemptResult(status="success", user=user)


def handle_student_login_secure(username: str, password: str):
    attempt = authenticate_login_attempt(username, password, detect_sql_injection=True)
    return attempt.user if attempt.status == "success" else None
