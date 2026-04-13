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

app = FastAPI(title="DBSHIELD Backend")

# =====================================================================
# DEMONSTRATION TOGGLES
ENABLE_DDOS_PROTECTION = True
ENABLE_SQLI_PROTECTION = False
# =====================================================================


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
        payload.creator_username, payload.course_code, payload.title, payload.credits)

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
