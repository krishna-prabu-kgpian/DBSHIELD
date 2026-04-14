import sys
import importlib.util
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import handle_student_login
from ddos_prevention.app_protection import AppDDoSProtection, load_app_ddos_settings
from sql_injection_prevention.secure_auth import authenticate_login_attempt
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
from sql_injection_prevention.secure_erp_placeholders import (
    add_material_placeholder_secure,
    admin_add_course_placeholder_secure,
    admin_add_student_placeholder_secure,
    admin_add_teacher_placeholder_secure,
    admin_delete_course_placeholder_secure,
    admin_delete_teacher_placeholder_secure,
    admin_do_anything_placeholder_secure,
    admin_remove_student_placeholder_secure,
    admit_student_placeholder_secure,
    assign_grade_placeholder_secure,
    create_assignment_placeholder_secure,
    create_course_placeholder_secure,
    deregister_course_placeholder_secure,
    enroll_course_placeholder_secure,
    remove_student_placeholder_secure,
    search_courses_placeholder_secure,
    student_courses_placeholder_secure,
    student_grades_placeholder_secure,
)

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
ENABLE_DDOS_PROTECTION = True 
# Set this to True to enable the secure ERP layer and explicit SQLi detection.
# Set this to False to keep the legacy demo handlers available in the codebase.
ENABLE_SQLI_PROTECTION = True
# Set this to True to ENFORCE role-based access control (secure)
# Set this to False to BYPASS role checks and allow any token (vulnerable)
ENABLE_AUTH_BYPASS_PROTECTION = True
# =====================================================================

app = FastAPI(title="DBSHIELD Backend")

ddos_protection = AppDDoSProtection(load_app_ddos_settings(ENABLE_DDOS_PROTECTION))
app.middleware("http")(ddos_protection.middleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

set_token_verifier(verify_session_token)


if ENABLE_SQLI_PROTECTION:
    add_material_service = add_material_placeholder_secure
    admin_add_course_service = admin_add_course_placeholder_secure
    admin_add_student_service = admin_add_student_placeholder_secure
    admin_add_teacher_service = admin_add_teacher_placeholder_secure
    admin_delete_course_service = admin_delete_course_placeholder_secure
    admin_delete_teacher_service = admin_delete_teacher_placeholder_secure
    admin_do_anything_service = admin_do_anything_placeholder_secure
    admin_remove_student_service = admin_remove_student_placeholder_secure
    admit_student_service = admit_student_placeholder_secure
    assign_grade_service = assign_grade_placeholder_secure
    create_assignment_service = create_assignment_placeholder_secure
    create_course_service = create_course_placeholder_secure
    deregister_course_service = deregister_course_placeholder_secure
    enroll_course_service = enroll_course_placeholder_secure
    remove_student_service = remove_student_placeholder_secure
    search_courses_service = search_courses_placeholder_secure
    student_courses_service = student_courses_placeholder_secure
    student_grades_service = student_grades_placeholder_secure
else:
    add_material_service = add_material_placeholder
    admin_add_course_service = admin_add_course_placeholder
    admin_add_student_service = admin_add_student_placeholder
    admin_add_teacher_service = admin_add_teacher_placeholder
    admin_delete_course_service = admin_delete_course_placeholder
    admin_delete_teacher_service = admin_delete_teacher_placeholder
    admin_do_anything_service = admin_do_anything_placeholder
    admin_remove_student_service = admin_remove_student_placeholder
    admit_student_service = admit_student_placeholder
    assign_grade_service = assign_grade_placeholder
    create_assignment_service = create_assignment_placeholder
    create_course_service = create_course_placeholder
    deregister_course_service = deregister_course_placeholder
    enroll_course_service = enroll_course_placeholder
    remove_student_service = remove_student_placeholder
    search_courses_service = search_courses_placeholder
    student_courses_service = student_courses_placeholder
    student_grades_service = student_grades_placeholder


def authenticate_login_request(username: str, password: str):
    return authenticate_login_attempt(
        username,
        password,
        detect_sql_injection=ENABLE_SQLI_PROTECTION,
    )


def authorize_request(
    request: Request,
    allowed_roles: list[str],
    context: str,
    *,
    owned_username: str | None = None,
) -> tuple[str, str]:
    username, role = extract_user_role_from_token(request)
    bypass_enabled = not ENABLE_AUTH_BYPASS_PROTECTION

    check_role_requirement(role, allowed_roles, bypass_enabled, context)
    if owned_username is not None and role == "student":
        check_data_ownership(username, owned_username, bypass_enabled, context)

    return username, role


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
async def login(payload: LoginPayload) -> dict[str, str]:
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    if ENABLE_SQLI_PROTECTION:
        login_result = await ddos_protection.run_login(authenticate_login_request, username, password)
        if login_result.status == "username_not_found":
            raise HTTPException(status_code=404, detail="Username not found.")
        if login_result.status == "sql_injection_detected":
            raise HTTPException(status_code=400, detail="Potential SQL injection detected in password.")
        if login_result.status == "invalid_password":
            raise HTTPException(status_code=401, detail="Incorrect password.")
        if login_result.status != "success" or not login_result.user:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        result = login_result.user
    else:
        result = await ddos_protection.run_login(handle_student_login, username, password)
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
        "token_type": "Bearer",
        "username": user,
        "role": role,
        "name": name,
        "instructions": "Use this token in requests: Authorization: Bearer " + token
    }


@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload, request: Request) -> dict[str, list[dict[str, str]]]:
    authorize_request(request, ["student", "instructor", "admin"], "Course search")
    return {"courses": search_courses_service(payload.query)}

@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload, request: Request) -> dict[str, list[dict[str, str]]]:
    authorize_request(
        request,
        ["student", "instructor", "admin"],
        "Grade viewing",
        owned_username=payload.student_username,
    )
    return {"grades": student_grades_service(payload.student_username)}

@app.post("/api/student/my-courses")
def student_my_courses(payload: StudentGradePayload, request: Request) -> dict[str, list[dict[str, str]]]:
    authorize_request(request, ["student", "instructor", "admin"], "Course listing")
    return {"courses": student_courses_service(payload.student_username)}

@app.post("/api/student/enroll")
def student_enroll(payload: StudentCoursePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["student"], "Course enrollment")
    return enroll_course_service(payload.student_username, payload.course_code)

@app.post("/api/student/deregister")
def student_deregister(payload: StudentCoursePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["student"], "Course deregistration")
    return deregister_course_service(payload.student_username, payload.course_code)



@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["instructor", "admin"], "Student admission")
    return admit_student_service(payload.student_username, payload.course_code)

@app.post("/api/instructor/remove-student")
def instructor_remove_student(payload: StudentCoursePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["instructor", "admin"], "Student removal")
    return remove_student_service(payload.student_username, payload.course_code)

@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["instructor", "admin"], "Grade assignment")
    return assign_grade_service(payload.student_username, payload.course_code, payload.grade)

@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["instructor", "admin"], "Assignment creation")
    return create_assignment_service(payload.course_code, payload.title)

@app.post("/api/instructor/create-course")
def instructor_create_course(payload: CreateCoursePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["instructor", "admin"], "Course creation")
    return create_course_service(
        payload.creator_username, payload.course_code, payload.title, payload.credits)

@app.post("/api/instructor/add-material")
def instructor_add_material(payload: MaterialPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["instructor", "admin"], "Material addition")
    return add_material_service(payload.course_code, payload.title, payload.resource_link)

@app.post("/api/admin/add-teacher")
def admin_add_teacher(payload: UserProvisionPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Teacher addition")
    return admin_add_teacher_service(payload.username, payload.name, payload.email)

@app.post("/api/admin/delete-teacher")
def admin_delete_teacher(payload: UsernamePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Teacher deletion")
    return admin_delete_teacher_service(payload.username)

@app.post("/api/admin/add-student")
def admin_add_student(payload: UserProvisionPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Student addition")
    return admin_add_student_service(payload.username, payload.name, payload.email)

@app.post("/api/admin/remove-student")
def admin_remove_student(payload: UsernamePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Student removal")
    return admin_remove_student_service(payload.username)

@app.post("/api/admin/add-course")
def admin_add_course(payload: CourseProvisionPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Course addition")
    return admin_add_course_service(payload.course_code, payload.title, payload.credits)

@app.post("/api/admin/delete-course")
def admin_delete_course(payload: CourseCodePayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Course deletion")
    return admin_delete_course_service(payload.course_code)

@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload, request: Request) -> dict[str, object]:
    authorize_request(request, ["admin"], "Admin action")
    return admin_do_anything_service(payload.query)
