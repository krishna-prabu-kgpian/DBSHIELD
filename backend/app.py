from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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


def handle_student_login(username: str, password: str) -> None:
	# Placeholder hook for future processing/storage logic.
	_ = (username, password)


@app.get("/health")
def health_check() -> dict[str, str]:
	return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload) -> dict[str, str]:
	username = payload.username.strip()
	password = payload.password

	if not username or not password:
		raise HTTPException(status_code=400, detail="Username and password are required.")

	handle_student_login(username, password)
	return {"message": "Credentials received."}