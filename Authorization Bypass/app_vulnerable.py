from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


def extract_user_role(request: Request) -> tuple[str, str]:
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Missing or invalid Authorization header. Format: Bearer <token>"
        )
    
    token = auth_header.replace("Bearer ", "").strip()
    
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

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload) -> dict[str, str]:
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    result = authenticate_user(username, password)
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    role = str(result.get("role", "")).lower()
    user = str(result.get("username", username))
    name = str(result.get("name", ""))

    if role not in {"student", "instructor", "admin"}:
        role = "student"

    token = create_session_token(user, role)

    return {
        "message": "Login successful.",
        "token": token,
        "username": user,
        "role": role,
        "name": name,
        "instructions": "Use this token: Authorization: Bearer " + token
    }


@app.post("/api/student/search-courses")
def student_search_courses(payload: CourseSearchPayload, request: Request) -> dict:
    username, role = extract_user_role(request)
    return {"courses": search_courses_db(payload.query)}

@app.post("/api/student/view-grades")
def student_view_grades(payload: StudentGradePayload, request: Request) -> dict:
    username, role = extract_user_role(request)

    return {"grades": get_student_grades_db(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: EnrollPayload, request: Request) -> dict:
    username, role = extract_user_role(request)

    return enroll_student_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request) -> dict:
    username, role = extract_user_role(request)

    return admit_student_to_course_db(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload, request: Request) -> dict:
    username, role = extract_user_role(request)

    return assign_grade_to_student_db(payload.student_username, payload.course_code, payload.grade)


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload, request: Request) -> dict:
    username, role = extract_user_role(request)

    return create_assignment_db(payload.course_code, payload.title)

@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload, request: Request) -> dict:
    username, role = extract_user_role(request)

    return execute_admin_action_db(payload.query)
