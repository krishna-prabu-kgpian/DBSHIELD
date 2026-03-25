import psycopg2
from psycopg2.extras import RealDictConnection, RealDictCursor
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT", 5432))  # Convert to int to force TCP connection
dbname = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

def connect_to_db():
    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    return conn

def handle_student_login(username: str, password: str):
    sql_query = f"SELECT * from Users WHERE username='{username}' AND password='{password}'"
    conn = connect_to_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql_query)
        result = cursor.fetchone()
        conn.close()
        
    return result