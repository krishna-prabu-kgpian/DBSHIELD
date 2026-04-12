from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import connect_to_db, handle_student_login
from sql_injection_prevention.secure_auth import handle_student_login_secure
from database import handle_student_login
from erp_placeholders import (
    add_material_placeholder,
    admin_add_course_placeholder,
    admin_add_student_placeholder,
    admin_add_teacher_placeholder,
    admin_delete_course_placeholder,
    admin_delete_teacher_placeholder,
    admin_do_anything_placeholder,
    admin_remove_student_placeholder,
    admit_student_placeholder,
    assign_grade_placeholder,
    create_assignment_placeholder,
    create_course_placeholder,
    deregister_course_placeholder,
    enroll_course_placeholder,
    remove_student_placeholder,
    search_courses_placeholder,
    student_courses_placeholder,
    student_grades_placeholder,
)

# Import DDoS protection modules
from ddos_prevention.rate_limiter import IPRateLimiter, BoundedQueryHistory

app = FastAPI(title="DBSHIELD Backend")

# =====================================================================
# DEMONSTRATION TOGGLE
# Set this to True to enable the DDOS protection layer
# Set this to False to simulate an unprotected backend
ENABLE_PROTECTION = True 
# Set this to True to route login through the secure module.
# Set this to False to keep the intentionally vulnerable SQLi demo path.
ENABLE_SQLI_PROTECTION = True
# =====================================================================

ip_limiter = IPRateLimiter()
query_history = BoundedQueryHistory()

@app.middleware("http")
async def ddos_protection_middleware(request, call_next):
    if ENABLE_PROTECTION:
        client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
        
        # In a real scenario, attackers might spoof IPs, so IP limiting alone isn't enough
        is_allowed, block_reason = await ip_limiter.check_ip(client_ip)
        
        if not is_allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": block_reason})
            
        # Add a secondary layer: Rate limit based on the endpoint to combat distributed attacks
        endpoint_hash = f"{request.method}:{request.url.path}"
        from ddos_prevention.config import RATE_LIMIT_THRESHOLD, RATE_LIMIT_WINDOW
        is_limited = await query_history.record_and_check(endpoint_hash, RATE_LIMIT_THRESHOLD, RATE_LIMIT_WINDOW)
        
        if is_limited:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=429, content={"detail": "Endpoint rate limit exceeded"})
            
    response = await call_next(request)
    return response

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


class LoginPayload(BaseModel):
	username: str
	password: str


class CourseSearchPayload(BaseModel):
    query: str


class StudentCoursePayload(BaseModel):
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


class CreateCoursePayload(BaseModel):
    creator_username: str
    course_code: str
    title: str
    credits: int = 3


class MaterialPayload(BaseModel):
    course_code: str
    title: str
    resource_link: str


class UserProvisionPayload(BaseModel):
    username: str
    name: str
    email: str = ""


class UsernamePayload(BaseModel):
    username: str


class CourseProvisionPayload(BaseModel):
    course_code: str
    title: str
    credits: int = 3


class CourseCodePayload(BaseModel):
    course_code: str


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload) -> dict[str, str]:
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    login_handler = handle_student_login_secure if ENABLE_SQLI_PROTECTION else handle_student_login
    result = login_handler(username, password)
    if not result:
        return {"message": "Invalid credentials."}

    role = str(result.get("role", "")).lower()
    user = str(result.get("username", username))
    name = str(result.get("name", ""))

    if role not in {"student", "instructor", "admin"}:
        return {"message": "Login successful.", "username": user, "role": "student", "name": name}

    return {"message": "Login successful.", "username": user, "role": role, "name": name}


@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload) -> dict[str, list[dict[str, str]]]:
    return {"courses": search_courses_placeholder(payload.query)}


@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload) -> dict[str, list[dict[str, str]]]:
    return {"grades": student_grades_placeholder(payload.student_username)}


@app.post("/api/student/my-courses")
def student_my_courses(payload: StudentGradePayload) -> dict[str, list[dict[str, str]]]:
    return {"courses": student_courses_placeholder(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: StudentCoursePayload) -> dict[str, object]:
    return enroll_course_placeholder(payload.student_username, payload.course_code)


@app.post("/api/student/deregister")
def student_deregister(payload: StudentCoursePayload) -> dict[str, object]:
    return deregister_course_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload) -> dict[str, object]:
    return admit_student_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/remove-student")
def instructor_remove_student(payload: StudentCoursePayload) -> dict[str, object]:
    return remove_student_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload) -> dict[str, object]:
    return assign_grade_placeholder(payload.student_username, payload.course_code, payload.grade)


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload) -> dict[str, object]:
    return create_assignment_placeholder(payload.course_code, payload.title)


@app.post("/api/instructor/create-course")
def instructor_create_course(payload: CreateCoursePayload) -> dict[str, object]:
    return create_course_placeholder(
        payload.creator_username,
        payload.course_code,
        payload.title,
        payload.credits,
    )


@app.post("/api/instructor/add-material")
def instructor_add_material(payload: MaterialPayload) -> dict[str, object]:
    return add_material_placeholder(payload.course_code, payload.title, payload.resource_link)


@app.post("/api/admin/add-teacher")
def admin_add_teacher(payload: UserProvisionPayload) -> dict[str, object]:
    return admin_add_teacher_placeholder(payload.username, payload.name, payload.email)


@app.post("/api/admin/delete-teacher")
def admin_delete_teacher(payload: UsernamePayload) -> dict[str, object]:
    return admin_delete_teacher_placeholder(payload.username)


@app.post("/api/admin/add-student")
def admin_add_student(payload: UserProvisionPayload) -> dict[str, object]:
    return admin_add_student_placeholder(payload.username, payload.name, payload.email)


@app.post("/api/admin/remove-student")
def admin_remove_student(payload: UsernamePayload) -> dict[str, object]:
    return admin_remove_student_placeholder(payload.username)


@app.post("/api/admin/add-course")
def admin_add_course(payload: CourseProvisionPayload) -> dict[str, object]:
    return admin_add_course_placeholder(payload.course_code, payload.title, payload.credits)


@app.post("/api/admin/delete-course")
def admin_delete_course(payload: CourseCodePayload) -> dict[str, object]:
    return admin_delete_course_placeholder(payload.course_code)


@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload) -> dict[str, object]:
    return admin_do_anything_placeholder(payload.query)
