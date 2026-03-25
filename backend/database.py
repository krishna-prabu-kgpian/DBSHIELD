import psycopg2
from psycopg2.extras import RealDictConnection, RealDictCursor
import os

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
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