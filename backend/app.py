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