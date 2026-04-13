import sys
import importlib.util
from pathlib import Path
from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from database import connect_to_db, handle_student_login
from sql_injection_prevention.secure_auth import handle_student_login_secure
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
from ddos_prevention.rate_limiter import IPRateLimiter

import asyncio
import time
from collections import defaultdict

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

def _env_flag(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


TRUST_X_FORWARDED_FOR = _env_flag("TRUST_X_FORWARDED_FOR", False)
MAX_CONCURRENT_LOGIN_REQUESTS = int(os.getenv("MAX_CONCURRENT_LOGIN_REQUESTS", "12"))
login_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOGIN_REQUESTS)


# ---------------------------------------------------------------------------
# IPSpoofDetector
# ---------------------------------------------------------------------------
# Why this works for the demo
# ───────────────────────────
# The attack script ALWAYS sets X-Forwarded-For to a random private IP.
# A real browser hitting localhost NEVER sets X-Forwarded-For.
#
# This detector watches a rolling window of (real_ip → unique forwarded IPs).
# As soon as one real IP cycles through more than THRESHOLD distinct claimed
# IPs it is flagged as a spoofer.  That block ONLY applies to requests that
# arrive with an X-Forwarded-For header — so it never touches your browser.
# ---------------------------------------------------------------------------
SPOOF_UNIQUE_IP_THRESHOLD = 12   # unique forwarded IPs within the window
SPOOF_WINDOW_SECONDS      = 10   # rolling window length in seconds


class IPSpoofDetector:
    def __init__(self, threshold: int = SPOOF_UNIQUE_IP_THRESHOLD,
                 window: int = SPOOF_WINDOW_SECONDS):
        self._lock = asyncio.Lock()
        self._records: dict[str, list[tuple[str, float]]] = defaultdict(list)
        self._blocked_real_ips: set[str] = set()
        self.threshold = threshold
        self.window = window

    async def check(self, real_ip: str, forwarded_ip: str) -> tuple[bool, str]:
        async with self._lock:
            if real_ip in self._blocked_real_ips:
                return True, "Blocked: IP header spoofing detected"

            now = time.time()
            self._records[real_ip] = [
                (ip, t) for ip, t in self._records[real_ip]
                if now - t < self.window
            ]
            self._records[real_ip].append((forwarded_ip, now))

            unique_count = len({ip for ip, _ in self._records[real_ip]})
            if unique_count > self.threshold:
                self._blocked_real_ips.add(real_ip)
                print(f"[SPOOF BLOCK] {real_ip} claimed {unique_count} different "
                      f"X-Forwarded-For values in {self.window}s — blocked.")
                return True, (
                    f"Blocked: IP spoofing detected "
                    f"({unique_count} unique forwarded IPs from one source)"
                )
            return False, ""


# Module-level singletons
ip_limiter     = IPRateLimiter()   # used for Path B (direct browser connections)
spoof_detector = IPSpoofDetector()


# ---------------------------------------------------------------------------
# Middleware — two completely separate paths
# ---------------------------------------------------------------------------
#
#  PATH A  —  request carries an X-Forwarded-For header
#             Only the attack script does this (it needs to fake its IP).
#             Apply spoof detection against the real TCP peer.
#             Rate-limit by the *claimed* forwarded IP
#             (each fake IP burns its own small quota and gets dropped).
#
#  PATH B  —  request has NO X-Forwarded-For header
#             Only a direct browser/client does this.
#             Rate-limit by the real TCP peer IP alone.
#             Normal interactive use (a few clicks per second) will never
#             reach the per-IP threshold, so the user sails through.
#
#  The two paths NEVER share a rate-limit bucket, so the flood in Path A
#  cannot spill over and affect Path B.  No global endpoint counter is
#  needed or used — that was the original source of the false positives.
#
# ---------------------------------------------------------------------------
@app.middleware("http")
async def ddos_protection_middleware(request: Request, call_next):
    if not ENABLE_DDOS_PROTECTION:
        return await call_next(request)

    real_ip  = request.client.host if request.client else "unknown"
    xff      = request.headers.get("X-Forwarded-For", "")
    has_xff  = bool(xff.strip())

    # In the local demo there is no trusted reverse proxy in front of FastAPI,
    # so any client-provided X-Forwarded-For header is spoofed by definition.
    # Reject it immediately instead of spending time on downstream logic.
    if has_xff and not TRUST_X_FORWARDED_FOR:
        return JSONResponse(
            status_code=403,
            content={"detail": "Blocked: untrusted X-Forwarded-For header"},
        )

    if has_xff:
        # ── PATH A: proxied / spoofed request ────────────────────────────
        forwarded_ip = xff.split(",")[0].strip()

        # 1. Spoof detection — catches the rotating-IP attack pattern
        is_spoofing, reason = await spoof_detector.check(real_ip, forwarded_ip)
        if is_spoofing:
            return JSONResponse(status_code=429, content={"detail": reason})

        # 2. Per-claimed-IP rate limit — each fake IP still gets a tight quota.
        #    If the attacker somehow passes spoof detection (threshold not yet
        #    reached), individual fake IPs still get throttled here.
        is_allowed, reason = await ip_limiter.check_ip(forwarded_ip)
        if not is_allowed:
            return JSONResponse(status_code=429, content={"detail": reason})

    else:
        # ── PATH B: direct browser connection ────────────────────────────
        # Rate-limit only by the real TCP peer IP.
        # A human clicking through a UI generates at most a few req/s —
        # well below any sane per-IP threshold — so this never fires for
        # legitimate users regardless of what the attacker is doing.
        is_allowed, reason = await ip_limiter.check_ip(real_ip)
        if not is_allowed:
            return JSONResponse(status_code=429, content={"detail": reason})

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    login_handler = handle_student_login_secure if ENABLE_SQLI_PROTECTION else handle_student_login
    async with login_request_semaphore:
        result = await run_in_threadpool(login_handler, username, password)
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
        payload.creator_username, payload.course_code, payload.title, payload.credits)

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
