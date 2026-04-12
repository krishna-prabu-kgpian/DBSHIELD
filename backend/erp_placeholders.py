"""Placeholder ERP service layer.

This module intentionally contains no database calls.
Use it as a temporary integration surface until real DB-backed handlers are added.
"""

from __future__ import annotations


def _placeholder_response(message: str) -> dict[str, object]:
    return {
        "message": message,
        "placeholder": True,
        "db_integration_required": True,
    }


def search_courses_placeholder(query: str) -> list[dict[str, str]]:
    all_courses = [
        {"code": "CS101", "title": "Intro to Programming", "credits": "4"},
        {"code": "CS205", "title": "Data Structures", "credits": "4"},
        {"code": "CS301", "title": "Database Systems", "credits": "3"},
        {"code": "MA201", "title": "Discrete Mathematics", "credits": "3"},
        {"code": "HS110", "title": "Communication Skills", "credits": "2"},
    ]

    term = query.strip().lower()
    if not term:
        return all_courses

    return [
        course
        for course in all_courses
        if term in course["code"].lower() or term in course["title"].lower()
    ]


def student_grades_placeholder(student_username: str) -> list[dict[str, str]]:
    _ = student_username
    return [
        {"course": "CS101", "grade": "A", "semester": "Spring 2026"},
        {"course": "MA201", "grade": "B+", "semester": "Spring 2026"},
    ]


def student_courses_placeholder(student_username: str) -> list[dict[str, str]]:
    _ = student_username
    return [
        {"code": "CS205", "title": "Data Structures", "status": "enrolled"},
        {"code": "HS110", "title": "Communication Skills", "status": "enrolled"},
    ]


def enroll_course_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    return _placeholder_response(
        f"Enrollment request accepted for {student_username} in {course_code}."
    )


def deregister_course_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    return _placeholder_response(
        f"Deregistration request accepted for {student_username} from {course_code}."
    )


def admit_student_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    return _placeholder_response(
        f"Instructor admitted {student_username} to {course_code}."
    )


def remove_student_placeholder(student_username: str, course_code: str) -> dict[str, object]:
    return _placeholder_response(
        f"Instructor removed {student_username} from {course_code}."
    )


def assign_grade_placeholder(student_username: str, course_code: str, grade: str) -> dict[str, object]:
    return _placeholder_response(
        f"Grade {grade} assigned to {student_username} for {course_code}."
    )


def create_assignment_placeholder(course_code: str, title: str) -> dict[str, object]:
    return _placeholder_response(f"Assignment '{title}' created for {course_code}.")


def create_course_placeholder(
    creator_username: str,
    course_code: str,
    title: str,
    credits: int,
) -> dict[str, object]:
    return _placeholder_response(
        f"Course {course_code} ({title}, {credits} credits) created by {creator_username}."
    )


def add_material_placeholder(course_code: str, title: str, resource_link: str) -> dict[str, object]:
    return _placeholder_response(
        f"Material '{title}' added to {course_code}. Link: {resource_link}"
    )


def admin_add_teacher_placeholder(username: str, name: str, email: str) -> dict[str, object]:
    return _placeholder_response(
        f"Teacher {username} ({name}) added. Contact: {email or 'not provided'}."
    )


def admin_delete_teacher_placeholder(username: str) -> dict[str, object]:
    return _placeholder_response(f"Teacher {username} removed.")


def admin_add_student_placeholder(username: str, name: str, email: str) -> dict[str, object]:
    return _placeholder_response(
        f"Student {username} ({name}) added. Contact: {email or 'not provided'}."
    )


def admin_remove_student_placeholder(username: str) -> dict[str, object]:
    return _placeholder_response(f"Student {username} removed.")


def admin_add_course_placeholder(course_code: str, title: str, credits: int) -> dict[str, object]:
    return _placeholder_response(
        f"Course {course_code} ({title}, {credits} credits) added by admin."
    )


def admin_delete_course_placeholder(course_code: str) -> dict[str, object]:
    return _placeholder_response(f"Course {course_code} removed by admin.")


def admin_do_anything_placeholder(action: str) -> dict[str, object]:
    return _placeholder_response(f"Admin action placeholder executed: {action}")
