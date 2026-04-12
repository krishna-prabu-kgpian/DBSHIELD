"""
VULNERABLE VERSION: Authorization Bypass Demonstration
======================================================

✅ AUTHENTICATION: Users MUST login with username/password to get Bearer token
   All endpoints require valid Bearer token in Authorization header

❌ AUTHORIZATION: NO ROLE CHECKS on endpoints
   Authenticated user can call ANY endpoint regardless of their role
   Student can act as instructor or admin even though token says "student"

This demonstrates: "Authentication != Authorization"
Just because you're logged in doesn't mean you should access everything!

DO NOT USE IN PRODUCTION!
This is for educational/security testing purposes only.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import authentication from original backend database
from auth_database import authenticate_user, create_session_token, verify_session_token
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


# ============== Authentication Helper ==============

def extract_user_role(request: Request) -> tuple[str, str]:
    """
    Extract user information from Bearer token in Authorization header.
    
    ✅ AUTHENTICATION: Validates token exists and is valid
    ❌ AUTHORIZATION: Does NOT check if role matches endpoint
    
    This is the vulnerability - we authenticate but don't authorize!
    """
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Missing or invalid Authorization header. Format: Bearer <token>"
        )
    
    token = auth_header.replace("Bearer ", "").strip()
    
    # Verify token is valid
    user_data = verify_session_token(token)
    if not user_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token. Please login again."
        )
    
    username = user_data.get("username")
    role = user_data.get("role")
    
    if not username or not role:
        raise HTTPException(status_code=401, detail="Malformed token")
    
    return username, role


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
    """Authenticate user and return Bearer token."""
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    # Query the real database
    result = authenticate_user(username, password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    role = str(result.get("role", "")).lower()
    user = str(result.get("username", username))
    name = str(result.get("name", ""))

    if role not in {"student", "instructor", "admin"}:
        role = "student"

    # ✅ Create Bearer token (same as secure version)
    token = create_session_token(user, role)

    return {
        "message": "Login successful.",
        "token": token,
        "username": user,
        "role": role,
        "name": name,
        "instructions": "Use this token: Authorization: Bearer " + token
    }


# ❌ VULNERABLE: Authentication required, but NO authorization checks

@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload, request: Request) -> dict:
    """✅ Authenticated - ❌ No authorization check (anyone can search)."""
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ Don't check role - any authenticated user can search
    return {"courses": search_courses_db(payload.query)}


@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload, request: Request) -> dict:
    """
    ✅ AUTHENTICATED: User must provide valid Bearer token
    ❌ VULNERABLE: NO AUTHORIZATION CHECK
    - Student can view ANY student's grades
    - No check that student is viewing their own data
    - No role validation
    """
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ Don't check role or data ownership - just return grades
    return {"grades": get_student_grades_db(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: EnrollPayload, request: Request) -> dict:
    """✅ Authenticated - ❌ No authorization check."""
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ Don't check role
    return enroll_student_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request) -> dict:
    """
    ✅ AUTHENTICATED: User must provide valid Bearer token
    ❌ VULNERABLE: NO ROLE CHECK!
    - Even a student with token can admit other students
    - Token says role="student" but endpoint doesn't check it
    - Should be restricted to role="instructor" only
    """
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ CRITICAL BUG: Don't check if role=="instructor"
    # Student can call this endpoint and modify course enrollment!
    return admit_student_to_course_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload, request: Request) -> dict:
    """
    ✅ AUTHENTICATED: User must provide valid Bearer token
    ❌ VULNERABLE: NO ROLE CHECK!
    - Any authenticated user can modify any student's grades
    - Token contains role but endpoint doesn't verify role=="instructor"
    - Critical data integrity violation!
    """
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ CRITICAL BUG: Don't check if role=="instructor"
    # Student with token can assign failing grades to others!
    return assign_grade_to_student_db(payload.student_username, payload.course_code, payload.grade)


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload, request: Request) -> dict:
    """
    ✅ AUTHENTICATED: User must provide valid Bearer token
    ❌ VULNERABLE: NO ROLE CHECK!
    - Should be restricted to role="instructor" only
    - Student can create fake assignments
    """
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ Don't check role
    return create_assignment_db(payload.course_code, payload.title)


@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload, request: Request) -> dict:
    """
    ✅ AUTHENTICATED: User must provide valid Bearer token
    ❌ VULNERABLE: NO ROLE CHECK!
    - Should be restricted to role="admin" only
    - Any authenticated user can execute admin commands!
    - Massive security risk
    """
    username, role = extract_user_role(request)  # ✅ Check if logged in
    # ❌ CRITICAL BUG: Don't check if role=="admin"
    # Student with token can execute admin queries!
    return execute_admin_action_db(payload.query)
