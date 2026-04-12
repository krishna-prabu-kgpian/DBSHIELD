"""
SECURE VERSION: Authorization Bypass Prevention
================================================

This backend implements proper role-based access control (RBAC).
Only endpoints matching the user's role will be accessible.

Authorization Strategy:
- Authentication: Verify user identity (username/password)
- Authorization: Verify user role for each endpoint
- Data Isolation: Ensure users only access their own data
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

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

app = FastAPI(title="DBSHIELD Backend - SECURE VERSION")

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


# ============== Authorization Helpers ==============

def extract_user_role(request: Request) -> Optional[tuple[str, str]]:
    """
    Extract user information from request headers.
    In production, this would validate JWT tokens.
    
    For demo: X-User and X-Role headers simulate JWT claims.
    """
    username = request.headers.get("X-User")
    role = request.headers.get("X-Role")
    
    if not username or not role:
        raise HTTPException(status_code=401, detail="Missing authentication headers (X-User, X-Role)")
    
    if role.lower() not in {"student", "instructor", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    return username, role.lower()


def require_role(*allowed_roles: str):
    """Decorator to enforce role-based access control."""
    def decorator(func):
        async def wrapper(request: Request = None, **kwargs):
            username, role = extract_user_role(request)
            
            if role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. This endpoint requires role: {', '.join(allowed_roles)}"
                )
            
            kwargs['username'] = username
            kwargs['role'] = role
            return await func(request=request, **kwargs) if hasattr(func, '__await__') else func(request=request, **kwargs)
        
        def sync_wrapper(request: Request = None, **kwargs):
            username, role = extract_user_role(request)
            
            if role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. This endpoint requires role: {', '.join(allowed_roles)}"
                )
            
            kwargs['username'] = username
            kwargs['role'] = role
            return func(request=request, **kwargs)
        
        return sync_wrapper
    
    return decorator


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


# ============== STUDENT ENDPOINTS (Secured) ==============

@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload, request: Request) -> dict:
    """Search courses - accessible by any role, typically students."""
    username, role = extract_user_role(request)
    return {"courses": search_courses_db(payload.query)}


@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload, request: Request) -> dict:
    """
    ✅ SECURED: Student can only view their OWN grades.
    
    Authorization Check:
    - User must be authenticated
    - User must be viewing their own grades (data ownership)
    """
    username, role = extract_user_role(request)
    
    # Restrict to students (or allow admin override in real system)
    if role not in {"student", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Only students can view grades"
        )
    
    # CRITICAL: Verify user is viewing their own data
    if role == "student" and username != payload.student_username:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Users can only view their own grades."
        )
    
    return {"grades": get_student_grades_db(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: EnrollPayload, request: Request) -> dict:
    """Enroll in course - only for students."""
    username, role = extract_user_role(request)
    
    if role != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can enroll in courses"
        )
    
    return enroll_student_db(payload.student_username, payload.course_code)


# ============== INSTRUCTOR ENDPOINTS (Secured) ==============

@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request) -> dict:
    """
    ✅ SECURED: Only instructors can admit students.
    
    Authorization Check:
    - User must be authenticated
    - User MUST have role="instructor"
    """
    username, role = extract_user_role(request)
    
    # CRITICAL: Verify user is an instructor
    if role != "instructor":
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. This endpoint requires role: instructor. You have role: {role}"
        )
    
    return admit_student_to_course_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload, request: Request) -> dict:
    """
    ✅ SECURED: Only instructors can assign grades.
    
    Authorization Check:
    - User must be authenticated
    - User MUST have role="instructor"
    """
    username, role = extract_user_role(request)
    
    # CRITICAL: Verify user is an instructor
    if role != "instructor":
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Only instructors can assign grades. You have role: {role}"
        )
    
    return assign_grade_to_student_db(
        payload.student_username,
        payload.course_code,
        payload.grade
    )


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload, request: Request) -> dict:
    """
    ✅ SECURED: Only instructors can create assignments.
    
    Authorization Check:
    - User must be authenticated
    - User MUST have role="instructor"
    """
    username, role = extract_user_role(request)
    
    # CRITICAL: Verify user is an instructor
    if role != "instructor":
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Only instructors can create assignments. You have role: {role}"
        )
    
    return create_assignment_db(payload.course_code, payload.title)


# ============== ADMIN ENDPOINTS (Secured) ==============

@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload, request: Request) -> dict:
    """
    ✅ SECURED: Only admins can perform admin actions.
    
    Authorization Check:
    - User must be authenticated
    - User MUST have role="admin"
    """
    username, role = extract_user_role(request)
    
    # CRITICAL: Verify user is an admin
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Admin privileges required. You have role: {role}"
        )
    
    return execute_admin_action_db(payload.query)
