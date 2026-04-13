# python3 -m unittest backend/sql_injection_prevention/test_secure_erp_placeholders.py
import os
import sys
import tempfile
import unittest
from pathlib import Path


TMP_DIR = tempfile.TemporaryDirectory()
os.environ["SQLITE_DB_PATH"] = str(Path(TMP_DIR.name) / "test_dbshield.sqlite3")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import connect_to_db, initialize_database
from erp_placeholders import (
    search_courses_placeholder,
    student_courses_placeholder,
    student_grades_placeholder,
)
from sql_injection_prevention.secure_erp_placeholders import (
    admin_add_student_placeholder_secure,
    admin_delete_course_placeholder_secure,
    admin_do_anything_placeholder_secure,
    assign_grade_placeholder_secure,
    enroll_course_placeholder_secure,
    search_courses_placeholder_secure,
    student_courses_placeholder_secure,
    student_grades_placeholder_secure,
)


DOCUMENTED_USERNAME_PAYLOADS = [
    ("comment_bypass", "student1' --"),
    ("or_bypass", "student1' OR '1'='1"),
    (
        "union_username_forgery",
        "' UNION SELECT 1,'FORGED','Spring 2026' --",
    ),
]

COURSE_CODE_PAYLOADS = [
    ("tautology", "CS101' OR '1'='1"),
    ("comment_bypass", "CS101' --"),
]

ADMIN_GUARD_PAYLOADS = [
    "DROP TABLE users;",
    "UPDATE users SET role = 'admin'",
    "SELECT * FROM users; DELETE FROM users",
]


class TestSecureERPPlaceholders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()
        conn = connect_to_db()
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
                INSERT OR IGNORE INTO courses (course_code, course_title, department, credits, semester)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("CS101", "Introduction to Programming", "CSE", 3, "Spring 2026"),
            )
            cursor.execute("SELECT id FROM users WHERE username = ?", ("student1",))
            student_id = cursor.fetchone()["id"]
            cursor.execute("SELECT id FROM courses WHERE course_code = ?", ("CS101",))
            course_id = cursor.fetchone()["id"]
            cursor.execute(
                """
                INSERT OR IGNORE INTO enrollments (student_id, course_id, status, grade)
                VALUES (?, ?, ?, ?)
                """,
                (student_id, course_id, "admitted", "A"),
            )
            conn.commit()
        finally:
            conn.close()

    def _count_courses_by_code(self, course_code: str) -> int:
        conn = connect_to_db()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM courses WHERE course_code = ?", (course_code,))
            return int(cursor.fetchone()["count"])
        finally:
            conn.close()

    def _lookup_grade(self, student_username: str, course_code: str) -> str | None:
        conn = connect_to_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT e.grade
                FROM enrollments e
                JOIN users u ON e.student_id = u.id
                JOIN courses c ON e.course_id = c.id
                WHERE u.username = ? AND c.course_code = ?
                """,
                (student_username, course_code),
            )
            row = cursor.fetchone()
            return str(row["grade"]) if row and row["grade"] is not None else None
        finally:
            conn.close()

    def test_secure_course_search_blocks_tautology_payload(self):
        vulnerable_results = search_courses_placeholder("CS101' OR '1'='1")
        secure_results = search_courses_placeholder_secure("CS101' OR '1'='1")

        self.assertGreaterEqual(len(vulnerable_results), 1)
        self.assertEqual(secure_results, [])

    def test_secure_grades_lookup_blocks_username_injection(self):
        results = student_grades_placeholder_secure("student1' OR '1'='1")
        self.assertEqual(results, [])

    def test_documented_username_payloads_are_blocked_by_secure_student_lookups(self):
        for case_name, payload in DOCUMENTED_USERNAME_PAYLOADS:
            with self.subTest(case=case_name, target="grades"):
                self.assertEqual(student_grades_placeholder_secure(payload), [])
            with self.subTest(case=case_name, target="courses"):
                self.assertEqual(student_courses_placeholder_secure(payload), [])

    def test_documented_username_payloads_succeed_against_vulnerable_student_lookups(self):
        for case_name, payload in DOCUMENTED_USERNAME_PAYLOADS:
            with self.subTest(case=case_name, target="grades"):
                self.assertGreaterEqual(len(student_grades_placeholder(payload)), 1)
            with self.subTest(case=case_name, target="courses"):
                self.assertGreaterEqual(len(student_courses_placeholder(payload)), 1)

    def test_secure_delete_course_treats_payload_as_literal(self):
        response = admin_delete_course_placeholder_secure("CS101' OR '1'='1")
        self.assertIn("removed", response["message"])

        self.assertEqual(self._count_courses_by_code("CS101"), 1)

    def test_secure_delete_course_treats_documented_payloads_as_literals(self):
        for case_name, payload in COURSE_CODE_PAYLOADS:
            with self.subTest(case=case_name):
                response = admin_delete_course_placeholder_secure(payload)
                self.assertIn("removed", response["message"])
                self.assertEqual(self._count_courses_by_code("CS101"), 1)

    def test_secure_enroll_treats_injected_username_as_literal(self):
        response = enroll_course_placeholder_secure("student1' OR '1'='1", "CS101")
        self.assertEqual(response["message"], "Could not enroll student1' OR '1'='1 in CS101.")

    def test_secure_assign_grade_treats_payload_as_data(self):
        payload = "A', graded_date = NULL --"
        response = assign_grade_placeholder_secure("student1", "CS101", payload)

        self.assertEqual(
            response["message"],
            "Grade A', graded_date = NULL -- assigned to student1 for CS101.",
        )
        self.assertEqual(self._lookup_grade("student1", "CS101"), payload)

    def test_secure_admin_add_student_treats_payload_as_literal_data(self):
        payload_username = "student_literal' --"
        response = admin_add_student_placeholder_secure(payload_username, "Literal Student", "")

        self.assertIn(payload_username, response["message"])
        lookup_results = student_courses_placeholder_secure(payload_username)
        self.assertEqual(lookup_results, [])

    def test_admin_query_guard_blocks_mutating_sql(self):
        for payload in ADMIN_GUARD_PAYLOADS:
            with self.subTest(payload=payload):
                response = admin_do_anything_placeholder_secure(payload)
                self.assertEqual(
                    response["message"],
                    "Only single read-only SELECT queries are allowed for security.",
                )

    def test_admin_query_guard_allows_single_read_only_select(self):
        response = admin_do_anything_placeholder_secure(
            "SELECT username, role FROM users WHERE username = 'student1'"
        )
        self.assertEqual(response["message"], "Admin action executed.")
        self.assertEqual(response["row_count"], 1)
        self.assertEqual(response["rows"][0]["username"], "student1")
        self.assertEqual(response["rows"][0]["role"], "student")


if __name__ == "__main__":
    unittest.main()
