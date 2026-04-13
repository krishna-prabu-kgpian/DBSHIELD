"""ERP service layer with direct database operations."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from database import connect_to_db


def _get_user_id(cursor: sqlite3.Cursor, username: str) -> int | None:
    cursor.execute(f"SELECT id FROM users WHERE username = '{username}'")
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def _get_course_id(cursor: sqlite3.Cursor, course_code: str) -> int | None:
    cursor.execute(f"SELECT id FROM courses WHERE course_code = '{course_code}'")
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def search_courses_placeholder(query: str) -> list[dict[str, str]]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        term = query.strip().lower()
        if term:
            like_term = f"%{term}%"
            cursor.execute(
                f"""
                SELECT course_code AS code, course_title AS title, credits
                FROM courses
                WHERE LOWER(course_code) LIKE '{like_term}' OR LOWER(course_title) LIKE '{like_term}'
                ORDER BY course_code
                """
            )
        else:
            cursor.execute(
                """
                SELECT course_code AS code, course_title AS title, credits
                FROM courses
                ORDER BY course_code
                """
            )

        rows = cursor.fetchall()
        return [
            {
                "code": str(row["code"]),
                "title": str(row["title"]),
                "credits": str(row["credits"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def student_grades_placeholder(student_username: str) -> list[dict[str, str]]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT c.course_code AS course, e.grade AS grade, c.semester AS semester
            FROM enrollments e
            JOIN users u ON e.student_id = u.id
            JOIN courses c ON e.course_id = c.id
            WHERE u.username = '{student_username}' AND e.grade IS NOT NULL
            ORDER BY c.course_code
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "course": str(row["course"]),
                "grade": str(row["grade"]),
                "semester": str(row["semester"] or ""),
            }
            for row in rows
        ]
    finally:
        conn.close()


def student_courses_placeholder(student_username: str) -> list[dict[str, str]]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT c.course_code AS code, c.course_title AS title, e.status AS status
            FROM enrollments e
            JOIN users u ON e.student_id = u.id
            JOIN courses c ON e.course_id = c.id
            WHERE u.username = '{student_username}'
            ORDER BY c.course_code
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "code": str(row["code"]),
                "title": str(row["title"]),
                "status": str(row["status"] or ""),
            }
            for row in rows
        ]
    finally:
        conn.close()


def enroll_course_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        student_id = _get_user_id(cursor, student_username)
        course_id = _get_course_id(cursor, course_code)
        if student_id is None or course_id is None:
            return {"message": f"Could not enroll {student_username} in {course_code}."}

        cursor.execute(
            f"""
            INSERT INTO enrollments (student_id, course_id, status)
            VALUES ({student_id}, {course_id}, 'enrolled')
            """
        )
        conn.commit()
        return {"message": f"Enrollment request accepted for {student_username} in {course_code}."}
    except sqlite3.IntegrityError:
        return {"message": f"Enrollment already exists for {student_username} in {course_code}."}
    finally:
        conn.close()


def deregister_course_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        student_id = _get_user_id(cursor, student_username)
        course_id = _get_course_id(cursor, course_code)
        if student_id is None or course_id is None:
            return {"message": f"Could not deregister {student_username} from {course_code}."}

        cursor.execute(
            f"DELETE FROM enrollments WHERE student_id = {student_id} AND course_id = {course_id}",
        )
        conn.commit()
        return {"message": f"Deregistration request accepted for {student_username} from {course_code}."}
    finally:
        conn.close()


def admit_student_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        student_id = _get_user_id(cursor, student_username)
        course_id = _get_course_id(cursor, course_code)
        if student_id is None or course_id is None:
            return {"message": f"Could not admit {student_username} to {course_code}."}

        cursor.execute(
            f"""
            UPDATE enrollments
            SET status = 'admitted', admitted_date = CURRENT_TIMESTAMP
            WHERE student_id = {student_id} AND course_id = {course_id}
            """
        )

        if cursor.rowcount == 0:
            cursor.execute(
                f"""
                INSERT INTO enrollments (student_id, course_id, status, admitted_date)
                VALUES ({student_id}, {course_id}, 'admitted', CURRENT_TIMESTAMP)
                """
            )

        conn.commit()
        return {"message": f"Instructor admitted {student_username} to {course_code}."}
    finally:
        conn.close()


def remove_student_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        student_id = _get_user_id(cursor, student_username)
        course_id = _get_course_id(cursor, course_code)
        if student_id is None or course_id is None:
            return {"message": f"Could not remove {student_username} from {course_code}."}

        cursor.execute(
            f"DELETE FROM enrollments WHERE student_id = {student_id} AND course_id = {course_id}",
        )
        conn.commit()
        return {"message": f"Instructor removed {student_username} from {course_code}."}
    finally:
        conn.close()


def assign_grade_placeholder(student_username: str, course_code: str, grade: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        student_id = _get_user_id(cursor, student_username)
        course_id = _get_course_id(cursor, course_code)
        if student_id is None or course_id is None:
            return {"message": f"Could not assign grade for {student_username} in {course_code}."}

        cursor.execute(
            f"""
            UPDATE enrollments
            SET grade = '{grade}', graded_date = CURRENT_TIMESTAMP
            WHERE student_id = {student_id} AND course_id = {course_id}
            """
        )

        if cursor.rowcount == 0:
            cursor.execute(
                f"""
                INSERT INTO enrollments (student_id, course_id, status, grade, graded_date)
                VALUES ({student_id}, {course_id}, 'admitted', '{grade}', CURRENT_TIMESTAMP)
                """
            )

        conn.commit()
        return {"message": f"Grade {grade} assigned to {student_username} for {course_code}."}
    finally:
        conn.close()


def create_assignment_placeholder(course_code: str, title: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        course_id = _get_course_id(cursor, course_code)
        if course_id is None:
            return {"message": f"Could not create assignment '{title}' for {course_code}."}

        cursor.execute(
            f"""
            INSERT INTO assignments (course_id, title, description)
            VALUES ({course_id}, '{title}', '')
            """
        )
        conn.commit()
        return {"message": f"Assignment '{title}' created for {course_code}."}
    finally:
        conn.close()


def create_course_placeholder(
    creator_username: str,
    course_code: str,
    title: str,
    credits: int,
) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        instructor_id = _get_user_id(cursor, creator_username)
        cursor.execute(
            f"""
            INSERT INTO courses (course_code, course_title, instructor_id, credits)
            VALUES ('{course_code}', '{title}', {('NULL' if instructor_id is None else instructor_id)}, {credits})
            """
        )
        conn.commit()
        return {"message": f"Course {course_code} ({title}, {credits} credits) created by {creator_username}."}
    except sqlite3.IntegrityError:
        return {"message": f"Course {course_code} already exists."}
    finally:
        conn.close()


def add_material_placeholder(course_code: str, title: str, resource_link: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        course_id = _get_course_id(cursor, course_code)
        if course_id is None:
            return {"message": f"Could not add material '{title}' to {course_code}."}

        cursor.execute(
            f"""
            INSERT INTO course_materials (course_id, title, resource_link)
            VALUES ({course_id}, '{title}', '{resource_link}')
            """
        )
        conn.commit()
        return {"message": f"Material '{title}' added to {course_code}. Link: {resource_link}"}
    finally:
        conn.close()


def admin_add_teacher_placeholder(username: str, name: str, email: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        resolved_email = email.strip() if email.strip() else f"{username}@dbshield.local"
        cursor.execute(
            f"""
            INSERT INTO users (username, email, password, role, name, phone)
            VALUES ('{username}', '{resolved_email}', '{username}123', 'instructor', '{name}', NULL)
            """
        )
        conn.commit()
        return {"message": f"Teacher {username} ({name}) added. Contact: {resolved_email}."}
    except sqlite3.IntegrityError:
        return {"message": f"Teacher {username} could not be added."}
    finally:
        conn.close()


def admin_delete_teacher_placeholder(username: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM users WHERE username = '{username}' AND role = 'instructor'")
        conn.commit()
        return {"message": f"Teacher {username} removed."}
    finally:
        conn.close()


def admin_add_student_placeholder(username: str, name: str, email: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        resolved_email = email.strip() if email.strip() else f"{username}@dbshield.local"
        cursor.execute(
            f"""
            INSERT INTO users (username, email, password, role, name, phone)
            VALUES ('{username}', '{resolved_email}', '{username}123', 'student', '{name}', NULL)
            """
        )
        user_id = cursor.lastrowid
        cursor.execute(
            f"""
            INSERT INTO students (user_id, cgpa, graduation_year)
            VALUES ({user_id}, 0.00, {datetime.now().year + 4})
            """
        )
        conn.commit()
        return {"message": f"Student {username} ({name}) added. Contact: {resolved_email}."}
    except sqlite3.IntegrityError:
        return {"message": f"Student {username} could not be added."}
    finally:
        conn.close()


def admin_remove_student_placeholder(username: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM users WHERE username = '{username}' AND role = 'student'")
        conn.commit()
        return {"message": f"Student {username} removed."}
    finally:
        conn.close()


def admin_add_course_placeholder(course_code: str, title: str, credits: int) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO courses (course_code, course_title, credits)
            VALUES ('{course_code}', '{title}', {credits})
            """
        )
        conn.commit()
        return {"message": f"Course {course_code} ({title}, {credits} credits) added by admin."}
    except sqlite3.IntegrityError:
        return {"message": f"Course {course_code} could not be added."}
    finally:
        conn.close()


def admin_delete_course_placeholder(course_code: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM courses WHERE course_code = '{course_code}'")
        conn.commit()
        return {"message": f"Course {course_code} removed by admin."}
    finally:
        conn.close()


def admin_do_anything_placeholder(action: str) -> dict[str, object]:
    conn = connect_to_db()
    try:
        cursor = conn.cursor()
        action_text = action.strip()
        if not action_text:
            return {"message": "No action provided."}

        cursor.execute(action_text)
        if cursor.description:
            rows = [dict(row) for row in cursor.fetchall()]
            return {
                "message": "Admin action executed.",
                "rows": rows,
                "row_count": len(rows),
            }

        conn.commit()
        return {
            "message": "Admin action executed.",
            "rows_affected": cursor.rowcount,
        }
    except Exception as exc:
        return {"message": f"Admin action failed: {exc}"}
    finally:
        conn.close()
