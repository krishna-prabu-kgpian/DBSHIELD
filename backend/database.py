import os
from pathlib import Path
import sqlite3

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_DB_PATH = BASE_DIR.parent / "database" / "dbshield.sqlite3"
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", str(DEFAULT_DB_PATH))).expanduser().resolve()
SCHEMA_PATH = BASE_DIR.parent / "database" / "tables.sql"


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema_sql)
        conn.execute(
            """
            INSERT OR IGNORE INTO users (username, email, password, role, name, phone)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("admin", "admin@dbshield.local", "admin123", "admin", "Admin User", "9000000000"),
        )
        conn.commit()

def connect_to_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def handle_student_login(username: str, password: str):
    import time
    
    # Simulate realistic database query parsing overhead
    # During a DDoS, a database parsing complex queries (or under high connection load) slows down significantly.
    time.sleep(0.05)
    
    sql_query = f"SELECT * from users WHERE username='{username}' AND password='{password}'"
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchone()
    finally:
        conn.close()

    return dict(result) if result else None
