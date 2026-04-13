from __future__ import annotations

from database import connect_to_db


def handle_student_login_secure(username: str, password: str):
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, password, role, name, phone
            FROM users
            WHERE username = ? AND password = ?
            """,
            (username, password),
        )
        result = cursor.fetchone()
    finally:
        conn.close()

    return dict(result) if result else None
