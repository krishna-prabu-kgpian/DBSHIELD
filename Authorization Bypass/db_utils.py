"""
Database utility functions for Authorization Bypass demonstration.
Queries real data from the SQLite database instead of using hardcoded values.
"""

import sqlite3
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency in local demos
    def load_dotenv(*args, **kwargs):
        return False

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_DB_PATH = BASE_DIR / "database" / "dbshield.sqlite3"
db_path = os.getenv("SQLITE_DB_PATH", str(DEFAULT_DB_PATH))


def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
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
        cursor = conn.cursor()
        # Search for courses that match query in code or title
        search_term = f"%{query.lower()}%"
        cursor.execute(f"""
            SELECT id, course_code as code, course_title as title, department
            FROM courses
            WHERE LOWER(course_code) LIKE '{search_term}' 
               OR LOWER(course_title) LIKE '{search_term}'
            LIMIT 20
        """)
        
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
    Queries the enrollments table using student username.
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT 
                c.course_code,
                c.course_title,
                e.grade,
                e.enrollment_date
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            JOIN users u ON e.student_id = u.id
            WHERE u.username = '{student_username}' AND e.grade IS NOT NULL
            ORDER BY e.enrollment_date DESC
        """)
        
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
        cursor = conn.cursor()
        # Get student ID from username
        cursor.execute(f"SELECT id FROM users WHERE username = '{student_username}'")
        student = cursor.fetchone()
        
        if not student:
            return {"success": False, "message": f"Student {student_username} not found"}
        
        student_id = student['id']
        
        # Get course ID from course code
        cursor.execute(f"SELECT id FROM courses WHERE course_code = '{course_code}'")
        course = cursor.fetchone()
        
        if not course:
            return {"success": False, "message": f"Course {course_code} not found"}
        
        course_id = course['id']
        
        # Check if already enrolled
        cursor.execute(
            f"SELECT id FROM enrollments WHERE student_id = {student_id} AND course_id = {course_id}"
        )
        if cursor.fetchone():
            return {"success": False, "message": f"Student already enrolled in {course_code}"}
        
        # Insert enrollment
        cursor.execute(
                f"""INSERT INTO enrollments (student_id, course_id)
                    VALUES ({student_id}, {course_id})"""
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
        cursor = conn.cursor()
        # Get student ID
        cursor.execute(f"SELECT id FROM users WHERE username = '{student_username}'")
        student = cursor.fetchone()
        
        if not student:
            return {"success": False, "message": f"Student {student_username} not found"}
        
        # Get course ID
        cursor.execute(f"SELECT id FROM courses WHERE course_code = '{course_code}'")
        course = cursor.fetchone()
        
        if not course:
            return {"success": False, "message": f"Course {course_code} not found"}
        
        # Update enrollment status to admitted
        cursor.execute(
                f"""UPDATE enrollments SET status = 'admitted'
                    WHERE student_id = {student['id']} AND course_id = {course['id']}"""
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
        cursor = conn.cursor()
        # Validate grade
        valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
        if grade not in valid_grades:
            return {"success": False, "message": f"Invalid grade: {grade}"}
        
        # Get student ID
        cursor.execute(f"SELECT id FROM users WHERE username = '{student_username}'")
        student = cursor.fetchone()
        
        if not student:
            return {"success": False, "message": f"Student {student_username} not found"}
        
        # Get course ID
        cursor.execute(f"SELECT id FROM courses WHERE course_code = '{course_code}'")
        course = cursor.fetchone()
        
        if not course:
            return {"success": False, "message": f"Course {course_code} not found"}
        
        # Update grade in enrollment
        cursor.execute(
                f"""UPDATE enrollments SET grade = '{grade}'
                    WHERE student_id = {student['id']} AND course_id = {course['id']}"""
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
        cursor = conn.cursor()
        # Get course ID
        cursor.execute(f"SELECT id FROM courses WHERE course_code = '{course_code}'")
        course = cursor.fetchone()
        
        if not course:
            return {"success": False, "message": f"Course {course_code} not found"}
        
        # Insert assignment
        cursor.execute(
                f"""INSERT INTO assignments (course_id, title, description)
                    VALUES ({course['id']}, '{title}', '{description}')"""
        )
        conn.commit()
        
        return {
            "success": True,
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
    For demo purposes, show what would happen with the query.
    """
    conn = get_db_connection()
    if not conn:
        return {"success": False, "message": "Database connection error"}
    
    try:
        cursor = conn.cursor()
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

