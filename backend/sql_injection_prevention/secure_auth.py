from __future__ import annotations

from database import connect_to_db


def handle_student_login_secure(username: str, password: str):
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT id, username, email, password, role, name, phone
            FROM users
            WHERE username = '{username}' AND password = '{password}'
            """
        )
        result = cursor.fetchone()
    finally:
        conn.close()

    return dict(result) if result else None
