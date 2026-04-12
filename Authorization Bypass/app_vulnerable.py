"""
VULNERABLE VERSION: Authorization Bypass Demonstration
======================================================

This is the ORIGINAL backend with NO authorization checks.
ANY authenticated user can call ANY endpoint regardless of their role.

DO NOT USE IN PRODUCTION!
This is for educational/security testing purposes only.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import authentication from original backend database
from auth_database import authenticate_user
from db_utils import (
    search_courses_db,
    get_student_grades_db,
    enroll_student_db,
    admit_student_to_course_db,
    assign_grade_to_student_db,
    create_assignment_db,
    execute_admin_action_db
)

app = FastAPI(title="DBSHIELD Backend - VULNERABLE VERSION")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class LoginPayload(BaseModel):
    username: str
    password: str


class CourseSearchPayload(BaseModel):
    query: str


class EnrollPayload(BaseModel):
    course_code: str
    student_username: str


class StudentGradePayload(BaseModel):
    student_username: str


class AdmitStudentPayload(BaseModel):
    student_username: str
    course_code: str


class GradeStudentPayload(BaseModel):
    student_username: str
    course_code: str
    grade: str


class AssignmentPayload(BaseModel):
    course_code: str
    title: str


# ============== Database Functions (Real Data) ==============


# ============== Endpoints ==============

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload) -> dict[str, str]:
    """Authenticate user against the real database."""
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    # Query the real database (same as original backend)
    result = authenticate_user(username, password)
    
    if not result:
        return {"message": "Invalid credentials."}

    role = str(result.get("role", "")).lower()
    user = str(result.get("username", username))
    name = str(result.get("name", ""))

    if role not in {"student", "instructor", "admin"}:
        return {"message": "Login successful.", "username": user, "role": "student", "name": name}

    return {"message": "Login successful.", "username": user, "role": role, "name": name}


# ❌ VULNERABLE: No authorization checks below

@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload) -> dict:
    return {"courses": search_courses_db(payload.query)}


@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload) -> dict:
    """
    VULNERABLE: ANY user can view ANY student's grades.
    No check that the requester is viewing their own grades.
    """
    return {"grades": get_student_grades_db(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: EnrollPayload) -> dict:
    return enroll_student_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload) -> dict:
    """
    VULNERABLE: NO ROLE CHECK!
    A student user can call this endpoint.
    Should be restricted to role="instructor" only.
    """
    return admit_student_to_course_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload) -> dict:
    """
    VULNERABLE: NO ROLE CHECK!
    A student user can call this and modify anyone's grades.
    """
    return assign_grade_to_student_db(payload.student_username, payload.course_code, payload.grade)


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload) -> dict:
    """
    VULNERABLE: NO ROLE CHECK!
    Should be restricted to role="instructor" only.
    """
    return create_assignment_db(payload.course_code, payload.title)


@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload) -> dict:
    """
    VULNERABLE: NO ROLE CHECK!
    Should be restricted to role="admin" only.
    """
    return execute_admin_action_db(payload.query)
