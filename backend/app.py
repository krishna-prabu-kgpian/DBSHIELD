from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import connect_to_db, handle_student_login

app = FastAPI(title="DBSHIELD Backend")

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


def search_courses_placeholder(query: str) -> list[dict[str, str]]:
    all_courses = [
        {"code": "CS101", "title": "Intro to Programming"},
        {"code": "CS205", "title": "Data Structures"},
        {"code": "MA201", "title": "Discrete Mathematics"},
        {"code": "HS110", "title": "Communication Skills"},
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
        {"course": "CS101", "grade": "A"},
        {"course": "MA201", "grade": "B+"},
    ]


def enroll_course_placeholder(student_username: str, course_code: str) -> dict[str, str]:
    return {
        "message": f"Enrollment request accepted for {student_username} in {course_code}."
    }


def admit_student_placeholder(student_username: str, course_code: str) -> dict[str, str]:
    return {
        "message": f"Instructor admitted {student_username} to {course_code}."
    }


def assign_grade_placeholder(student_username: str, course_code: str, grade: str) -> dict[str, str]:
    return {
        "message": f"Grade {grade} assigned to {student_username} for {course_code}."
    }


def create_assignment_placeholder(course_code: str, title: str) -> dict[str, str]:
    return {"message": f"Assignment '{title}' created for {course_code}."}


def admin_do_anything_placeholder(action: str) -> dict[str, str]:
    return {"message": f"Admin action placeholder executed: {action}"}


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload) -> dict[str, str]:
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    result = handle_student_login(username, password)
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
    # Placeholder endpoint: returns only the requested student's grades.
    return {"grades": student_grades_placeholder(payload.student_username)}


@app.post("/api/student/enroll")
def student_enroll(payload: EnrollPayload) -> dict[str, str]:
    return enroll_course_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload) -> dict[str, str]:
    return admit_student_placeholder(payload.student_username, payload.course_code)


@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload) -> dict[str, str]:
    return assign_grade_placeholder(payload.student_username, payload.course_code, payload.grade)


@app.post("/api/instructor/create-assignment")
def instructor_create_assignment(payload: AssignmentPayload) -> dict[str, str]:
    return create_assignment_placeholder(payload.course_code, payload.title)


@app.post("/api/admin/action")
def admin_action(payload: CourseSearchPayload) -> dict[str, str]:
    return admin_do_anything_placeholder(payload.query)