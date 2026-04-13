import sys
import importlib.util
from pathlib import Path
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

# Import Authorization Bypass prevention module
# Add the parent directory (DBSHIELD) to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    # Import from folder with space in name
    auth_bypass_path = Path(__file__).resolve().parent.parent / "Authorization Bypass"
    
    # Load authorization module
    auth_spec = importlib.util.spec_from_file_location("authorization", auth_bypass_path / "authorization.py")
    auth_module = importlib.util.module_from_spec(auth_spec)
    auth_spec.loader.exec_module(auth_module)
    
    # Load auth_database module
    auth_db_spec = importlib.util.spec_from_file_location("auth_database", auth_bypass_path / "auth_database.py")
    auth_db_module = importlib.util.module_from_spec(auth_db_spec)
    auth_db_spec.loader.exec_module(auth_db_module)
    
    # Import functions
    check_role_requirement = auth_module.check_role_requirement
    extract_user_role_from_token = auth_module.extract_user_role_from_token
    check_data_ownership = auth_module.check_data_ownership
    set_token_verifier = auth_module.set_token_verifier
    create_session_token = auth_db_module.create_session_token
    verify_session_token = auth_db_module.verify_session_token
except ImportError as e:
    # Fallback if module not found
    print(f"Warning: Authorization Bypass module not found: {e}")
    def check_role_requirement(*args, **kwargs): pass
    def extract_user_role_from_token(*args, **kwargs): return "", ""
    def check_data_ownership(*args, **kwargs): pass
    def set_token_verifier(*args, **kwargs): pass
    def create_session_token(*args, **kwargs): return "dummy_token"
    def verify_session_token(*args, **kwargs): return None


# =====================================================================
# DEMONSTRATION TOGGLE
# Set this to True to enable the DDOS protection layer
# Set this to False to simulate an unprotected backend
ENABLE_PROTECTION = True 
# Set this to True to route login through the secure module.
# Set this to False to keep the intentionally vulnerable SQLi demo path.
ENABLE_SQLI_PROTECTION = True
# Set this to True to ENABLE authorization bypass vulnerability (insecure)
# Set this to False to DISABLE authorization bypass and enforce RBAC (secure)
ENABLE_AUTHORIZATION_BYPASS = False
# =====================================================================

app = FastAPI(title="DBSHIELD Backend")

# Initialize token verifier for authorization module
set_token_verifier(verify_session_token)

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
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    role = str(result.get("role", "")).lower()
    user = str(result.get("username", username))
    name = str(result.get("name", ""))

    if role not in {"student", "instructor", "admin"}:
        role = "student"

    # ✅ Create Bearer token tied to authenticated user
    token = create_session_token(user, role)

    return {
        "message": "Login successful.",
        "token": token,
        "username": user,
        "role": role,
        "name": name,
        "instructions": "Use this token in requests: Authorization: Bearer " + token
    }


@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload, request: Request) -> dict[str, list[dict[str, str]]]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["student", "instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Course search")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass  # Allow access even without proper auth in bypass mode
        else:
            raise
    return {"courses": search_courses_placeholder(payload.query)}


@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload, request: Request) -> dict[str, list[dict[str, str]]]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["student", "instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Grade viewing")
        # Data ownership check: students can only view their own grades
        if role == "student":
            check_data_ownership(username, payload.student_username, ENABLE_AUTHORIZATION_BYPASS, "Grade viewing")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass  # Allow access in bypass mode
        else:
            raise
    return {"grades": student_grades_placeholder(payload.student_username)}


@app.post("/api/student/my-courses")
def student_my_courses(payload: StudentGradePayload, request: Request) -> dict[str, list[dict[str, str]]]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["student", "instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Course listing")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return {"courses": student_courses_placeholder(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: StudentCoursePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["student"], ENABLE_AUTHORIZATION_BYPASS, "Course enrollment")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return enroll_course_placeholder(payload.student_username, payload.course_code)


@app.post("/api/student/deregister")
def student_deregister(payload: StudentCoursePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["student"], ENABLE_AUTHORIZATION_BYPASS, "Course deregistration")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return deregister_course_placeholder(payload.student_username, payload.course_code)



@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Student admission")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admit_student_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/remove-student")
def instructor_remove_student(payload: StudentCoursePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Student removal")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return remove_student_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Grade assignment")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return assign_grade_placeholder(payload.student_username, payload.course_code, payload.grade)


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Assignment creation")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return create_assignment_placeholder(payload.course_code, payload.title)


@app.post("/api/instructor/create-course")
def instructor_create_course(payload: CreateCoursePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Course creation")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return create_course_placeholder(
        payload.creator_username,
        payload.course_code,
        payload.title,
        payload.credits,
    )


@app.post("/api/instructor/add-material")
def instructor_add_material(payload: MaterialPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["instructor", "admin"], ENABLE_AUTHORIZATION_BYPASS, "Material addition")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return add_material_placeholder(payload.course_code, payload.title, payload.resource_link)


@app.post("/api/admin/add-teacher")
def admin_add_teacher(payload: UserProvisionPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Teacher addition")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_add_teacher_placeholder(payload.username, payload.name, payload.email)


@app.post("/api/admin/delete-teacher")
def admin_delete_teacher(payload: UsernamePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Teacher deletion")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_delete_teacher_placeholder(payload.username)


@app.post("/api/admin/add-student")
def admin_add_student(payload: UserProvisionPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Student addition")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_add_student_placeholder(payload.username, payload.name, payload.email)


@app.post("/api/admin/remove-student")
def admin_remove_student(payload: UsernamePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Student removal")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_remove_student_placeholder(payload.username)


@app.post("/api/admin/add-course")
def admin_add_course(payload: CourseProvisionPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Course addition")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_add_course_placeholder(payload.course_code, payload.title, payload.credits)


@app.post("/api/admin/delete-course")
def admin_delete_course(payload: CourseCodePayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Course deletion")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_delete_course_placeholder(payload.course_code)


@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload, request: Request) -> dict[str, object]:
    try:
        username, role = extract_user_role_from_token(request)
        check_role_requirement(role, ["admin"], ENABLE_AUTHORIZATION_BYPASS, "Admin action")
    except HTTPException:
        if ENABLE_AUTHORIZATION_BYPASS:
            pass
        else:
            raise
    return admin_do_anything_placeholder(payload.query)
