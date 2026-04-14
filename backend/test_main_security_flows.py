# python3 -m unittest backend/test_main_security_flows.py

from __future__ import annotations

import importlib
import asyncio
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi import HTTPException
from starlette.requests import Request


TMP_DIR = tempfile.TemporaryDirectory()
os.environ["SQLITE_DB_PATH"] = str(Path(TMP_DIR.name) / "test_dbshield.sqlite3")

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

for module_name in [
    "app",
    "database",
    "sql_injection_prevention.secure_auth",
    "sql_injection_prevention.secure_erp_placeholders",
]:
    sys.modules.pop(module_name, None)

database = importlib.import_module("database")
database.initialize_database()
app_module = importlib.import_module("app")
app_protection_module = importlib.import_module("ddos_prevention.app_protection")


class TestMainSecurityFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conn = database.connect_to_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (username, email, password, role, name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("student1", "student1@example.com", "pass1", "student", "Student One", "9000000001"),
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (username, email, password, role, name, phone)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("other_student", "other_student@example.com", "pass2", "student", "Student Two", "9000000002"),
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO courses (course_code, course_title, department, credits, semester)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("CS101", "Introduction to Programming", "CSE", 3, "Spring 2026"),
            )
            cursor.execute("SELECT id FROM users WHERE username = ?", ("other_student",))
            other_student_id = cursor.fetchone()["id"]
            cursor.execute("SELECT id FROM courses WHERE course_code = ?", ("CS101",))
            course_id = cursor.fetchone()["id"]
            cursor.execute(
                """
                INSERT OR IGNORE INTO enrollments (student_id, course_id, status, grade)
                VALUES (?, ?, ?, ?)
                """,
                (other_student_id, course_id, "admitted", "A"),
            )
            conn.commit()
        finally:
            conn.close()

    def setUp(self):
        self.original_sqli_flag = app_module.ENABLE_SQLI_PROTECTION
        self.original_auth_bypass_flag = app_module.ENABLE_AUTH_BYPASS_PROTECTION
        self.original_ddos_settings = app_module.ddos_protection.settings
        self.original_run_in_threadpool = app_protection_module.run_in_threadpool
        app_module.ddos_protection.settings = replace(
            app_module.ddos_protection.settings,
            enabled=False,
        )

        async def immediate_threadpool(func, *args, **kwargs):
            return func(*args, **kwargs)

        app_protection_module.run_in_threadpool = immediate_threadpool

    def tearDown(self):
        app_module.ENABLE_SQLI_PROTECTION = self.original_sqli_flag
        app_module.ENABLE_AUTH_BYPASS_PROTECTION = self.original_auth_bypass_flag
        app_module.ddos_protection.settings = self.original_ddos_settings
        app_protection_module.run_in_threadpool = self.original_run_in_threadpool

    def _make_request(self, token: str | None = None) -> Request:
        headers = []
        if token:
            headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(scope, receive)

    def _login(self, username: str, password: str) -> str:
        result = asyncio.run(
            app_module.login(
                app_module.LoginPayload(username=username, password=password),
            )
        )
        return result["token"]

    def test_login_allows_documented_password_sqli_when_protection_disabled(self):
        app_module.ENABLE_SQLI_PROTECTION = False

        result = asyncio.run(
            app_module.login(
                app_module.LoginPayload(username="admin", password="' OR '1'='1"),
            )
        )

        self.assertEqual(result["username"], "admin")
        self.assertEqual(result["role"], "admin")

    def test_login_blocks_documented_password_sqli_when_protection_enabled(self):
        app_module.ENABLE_SQLI_PROTECTION = True

        with self.assertRaises(HTTPException) as exc:
            asyncio.run(
                app_module.login(
                    app_module.LoginPayload(username="admin", password="' OR '1'='1"),
                )
            )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.detail, "Potential SQL injection detected in password.")

    def test_auth_bypass_mode_still_requires_a_valid_token(self):
        app_module.ENABLE_AUTH_BYPASS_PROTECTION = False

        with self.assertRaises(HTTPException) as exc:
            app_module.admin_action(
                app_module.CourseSearchPayload(query="SELECT username FROM users LIMIT 1"),
                self._make_request(),
            )

        self.assertEqual(exc.exception.status_code, 401)

    def test_auth_bypass_mode_allows_student_token_to_hit_admin_endpoint(self):
        app_module.ENABLE_AUTH_BYPASS_PROTECTION = False
        token = self._login("student1", "pass1")

        result = app_module.admin_action(
            app_module.CourseSearchPayload(query="SELECT username FROM users LIMIT 1"),
            self._make_request(token),
        )

        self.assertEqual(result["message"], "Admin action executed.")

    def test_auth_protection_blocks_student_token_from_admin_endpoint(self):
        app_module.ENABLE_AUTH_BYPASS_PROTECTION = True
        token = self._login("student1", "pass1")

        with self.assertRaises(HTTPException) as exc:
            app_module.admin_action(
                app_module.CourseSearchPayload(query="SELECT username FROM users LIMIT 1"),
                self._make_request(token),
            )

        self.assertEqual(exc.exception.status_code, 403)

    def test_auth_protection_enforces_student_data_ownership(self):
        app_module.ENABLE_AUTH_BYPASS_PROTECTION = True
        token = self._login("student1", "pass1")

        with self.assertRaises(HTTPException) as exc:
            app_module.student_view_grades(
                app_module.StudentGradePayload(student_username="other_student"),
                self._make_request(token),
            )

        self.assertEqual(exc.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
