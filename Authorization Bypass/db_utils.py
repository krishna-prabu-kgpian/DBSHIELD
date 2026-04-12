"""
Database utility functions for Authorization Bypass demonstration.
Queries real data from the PostgreSQL database instead of using hardcoded values.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT", 5432))
dbname = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def search_courses_db(query: str) -> list[dict]:
    """
    Search for courses in the database.
    Returns courses matching the search query.
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Search for courses that match query in code or title
            search_term = f"%{query.lower()}%"
            cursor.execute("""
                SELECT course_code as code, course_title as title, department
                FROM courses
                WHERE LOWER(course_code) LIKE %s 
                   OR LOWER(course_title) LIKE %s
                LIMIT 20
            """, (search_term, search_term))
            
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
    except Exception as e:
        print(f"Error searching courses: {e}")
        return []
    finally:
        conn.close()


def get_student_grades_db(student_username: str) -> list[dict]:
    """
    Get grades for a specific student from the database.
    Queries the grades table using student username.
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    c.course_code,
                    c.course_title,
                    e.grade,
                    e.enrollment_date
                FROM enrollments e
                JOIN courses c ON e.course_id = c.id
                JOIN users u ON e.student_id = u.id
                WHERE u.username = %s AND e.grade IS NOT NULL
                ORDER BY e.enrollment_date DESC
            """, (student_username,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results] if results else []
    except Exception as e:
        print(f"Error fetching grades: {e}")
        return []
    finally:
        conn.close()


def enroll_student_db(student_username: str, course_code: str) -> dict:
    """
    Enroll a student in a course.
    Inserts enrollment record into the database.
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "message": "Database connection error"}
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get student ID from username
            cursor.execute("SELECT id FROM users WHERE username = %s", (student_username,))
            student = cursor.fetchone()
            
            if not student:
                return {"success": False, "message": f"Student {student_username} not found"}
            
            student_id = student['id']
            
            # Get course ID from course code
            cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course_code,))
            course = cursor.fetchone()
            
            if not course:
                return {"success": False, "message": f"Course {course_code} not found"}
            
            course_id = course['id']
            
            # Check if already enrolled
            cursor.execute(
                "SELECT id FROM enrollments WHERE student_id = %s AND course_id = %s",
                (student_id, course_id)
            )
            if cursor.fetchone():
                return {"success": False, "message": f"Student already enrolled in {course_code}"}
            
            # Insert enrollment
            cursor.execute(
                """INSERT INTO enrollments (student_id, course_id, enrollment_date)
                   VALUES (%s, %s, NOW())""",
                (student_id, course_id)
            )
            conn.commit()
            
            return {
                "success": True,
                "message": f"Enrollment request accepted for {student_username} in {course_code}."
            }
    except Exception as e:
        print(f"Error enrolling student: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def admit_student_to_course_db(student_username: str, course_code: str) -> dict:
    """
    Admit a student to a course (instructor action).
    Requires instructor authorization.
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "message": "Database connection error"}
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get student ID
            cursor.execute("SELECT id FROM users WHERE username = %s", (student_username,))
            student = cursor.fetchone()
            
            if not student:
                return {"success": False, "message": f"Student {student_username} not found"}
            
            # Get course ID
            cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course_code,))
            course = cursor.fetchone()
            
            if not course:
                return {"success": False, "message": f"Course {course_code} not found"}
            
            # Update enrollment status to admitted
            cursor.execute(
                """UPDATE enrollments SET status = 'admitted', admitted_date = NOW()
                   WHERE student_id = %s AND course_id = %s""",
                (student['id'], course['id'])
            )
            conn.commit()
            
            return {
                "success": True,
                "message": f"Instructor admitted {student_username} to {course_code}."
            }
    except Exception as e:
        print(f"Error admitting student: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def assign_grade_to_student_db(student_username: str, course_code: str, grade: str) -> dict:
    """
    Assign a grade to a student for a course (instructor action).
    Requires instructor authorization.
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "message": "Database connection error"}
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Validate grade
            valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
            if grade not in valid_grades:
                return {"success": False, "message": f"Invalid grade: {grade}"}
            
            # Get student ID
            cursor.execute("SELECT id FROM users WHERE username = %s", (student_username,))
            student = cursor.fetchone()
            
            if not student:
                return {"success": False, "message": f"Student {student_username} not found"}
            
            # Get course ID
            cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course_code,))
            course = cursor.fetchone()
            
            if not course:
                return {"success": False, "message": f"Course {course_code} not found"}
            
            # Update grade in enrollment
            cursor.execute(
                """UPDATE enrollments SET grade = %s, graded_date = NOW()
                   WHERE student_id = %s AND course_id = %s""",
                (grade, student['id'], course['id'])
            )
            conn.commit()
            
            return {
                "success": True,
                "message": f"Grade {grade} assigned to {student_username} for {course_code}."
            }
    except Exception as e:
        print(f"Error assigning grade: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def create_assignment_db(course_code: str, title: str, description: str = "") -> dict:
    """
    Create an assignment for a course (instructor action).
    Requires instructor authorization.
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "message": "Database connection error"}
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get course ID
            cursor.execute("SELECT id FROM courses WHERE course_code = %s", (course_code,))
            course = cursor.fetchone()
            
            if not course:
                return {"success": False, "message": f"Course {course_code} not found"}
            
            # Insert assignment
            cursor.execute(
                """INSERT INTO assignments (course_id, title, description, created_date)
                   VALUES (%s, %s, %s, NOW())
                   RETURNING id""",
                (course['id'], title, description)
            )
            result = cursor.fetchone()
            conn.commit()
            
            return {
                "success": True,
                "assignment_id": result['id'] if result else None,
                "message": f"Assignment '{title}' created for {course_code}."
            }
    except Exception as e:
        print(f"Error creating assignment: {e}")
        return {"success": False, "message": str(e)}
    finally:
        conn.close()


def execute_admin_action_db(action: str) -> dict:
    """
    Execute an admin action (admin-only).
    This is a placeholder that would validate and execute admin commands.
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "message": "Database connection error"}
    
    try:
        # In a real system, this would validate and execute the query safely
        # For demo purposes, we show what would happen
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Example: Support specific admin queries
            if action.lower().startswith("select"):
                # Safe read-only operation
                cursor.execute(action)
                results = cursor.fetchall()
                return {
                    "success": True,
                    "message": f"Admin query executed",
                    "result_count": len(results) if results else 0
                }
            else:
                return {
                    "success": False,
                    "message": "Only SELECT queries are allowed for security"
                }
    except Exception as e:
        return {"success": False, "message": f"Admin action error: {str(e)}"}
    finally:
        conn.close()
