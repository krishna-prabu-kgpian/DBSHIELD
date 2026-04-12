# python3 -m unittest backend/sql_injection_prevention/test_sql_injection_prevention.py

import unittest
from pathlib import Path
import sys
import sqlite3

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import handle_student_login, initialize_database
from sql_injection_prevention.secure_auth import handle_student_login_secure


WORKING_CREDENTIALS = ("admin", "admin123")

DOCUMENTED_WORKING_PAYLOADS = [
    ("comment_bypass", "admin' --", "anything"),
    ("or_bypass", "' OR '1'='1", "' OR '1'='1"),
    ("union_users_extract", "' UNION SELECT id,username,email,password,role,name,phone FROM users --", "anything"),
    (
        "sqlite_version_disclosure",
        "' UNION SELECT 1,sqlite_version(),sqlite_version(),sqlite_version(),"
        "sqlite_version(),sqlite_version(),sqlite_version() --",
        "anything",
    ),
    ("blind_length_check", "admin' AND LENGTH(password)=8 --", "anything"),
    ("blind_substr_check", "admin' AND SUBSTR(password,1,5)='admin' --", "anything"),
    ("blind_substring_check", "admin' AND SUBSTRING(password,1,5)='admin' --", "anything"),
    ("union_role_forgery", "' UNION SELECT 1,'pwned','pwned@example.com','x','admin','Injected Admin','9999999999' --", "anything"),
    (
        "pragma_table_info_enumeration",
        "' UNION SELECT 1,group_concat(name,','),group_concat(name,','),"
        "group_concat(name,','),group_concat(name,','),group_concat(name,','),"
        "group_concat(name,',') FROM pragma_table_info('users') --",
        "anything",
    ),
    ("sqlite_master_table_enumeration", "' UNION SELECT 1,name,type,sql,type,name,sql FROM sqlite_master WHERE type='table' --", "anything"),
    (
        "users_count_extraction",
        "' UNION SELECT 1,CAST(COUNT(*) AS TEXT),CAST(COUNT(*) AS TEXT),"
        "CAST(COUNT(*) AS TEXT),CAST(COUNT(*) AS TEXT),CAST(COUNT(*) AS TEXT),"
        "CAST(COUNT(*) AS TEXT) FROM users --",
        "anything",
    ),
    (
        "heavy_query_blind_payload",
        "admin' AND CASE WHEN SUBSTR(password,1,1)='a' THEN "
        "(WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x<200000) "
        "SELECT MAX(x) FROM cnt) ELSE 1 END --",
        "anything",
    ),
]

NOT_COMPATIBLE_WITH_CURRENT_SQLITE_PAYLOADS = [
    ("version_function", "' UNION SELECT 1,version(),version(),version(),version(),version(),version() --", "anything"),
    ("sleep_function", "admin' AND sleep(3) --", "anything"),
    ("pg_sleep_function", "admin' AND pg_sleep(3) --", "anything"),
    (
        "string_agg_information_schema",
        "' UNION SELECT 1,STRING_AGG(column_name,','),STRING_AGG(column_name,','),"
        "STRING_AGG(column_name,','),STRING_AGG(column_name,','),STRING_AGG(column_name,','),"
        "STRING_AGG(column_name,',') FROM information_schema.columns WHERE table_name='users' --",
        "anything",
    ),
    (
        "postgres_cast_syntax",
        "' UNION SELECT 1,COUNT(*)::text,COUNT(*)::text,COUNT(*)::text,"
        "COUNT(*)::text,COUNT(*)::text,COUNT(*)::text FROM users --",
        "anything",
    ),
    ("now_interval_syntax", "admin' AND NOW() - INTERVAL '1 second' IS NOT NULL --", "anything"),
]

NOT_DEMONSTRABLE_AGAINST_CURRENT_LOGIN_PATH = [
    ("stacked_insert", "admin'; INSERT INTO users(username,email,password,role,name,phone) VALUES ('evil','evil@x','x','admin','evil','1'); --", "anything"),
]


class TestSQLInjectionDefense(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_valid_login_still_works(self):
        result = handle_student_login_secure(*WORKING_CREDENTIALS)
        self.assertIsNotNone(result)
        self.assertEqual(result["username"], "admin")

    def test_documented_working_payloads_are_blocked_by_secure_login(self):
        for case_name, username, password in DOCUMENTED_WORKING_PAYLOADS:
            with self.subTest(case=case_name):
                result = handle_student_login_secure(username, password)
                self.assertIsNone(result)

    def test_documented_working_payloads_succeed_against_vulnerable_login(self):
        for case_name, username, password in DOCUMENTED_WORKING_PAYLOADS:
            with self.subTest(case=case_name):
                result = handle_student_login(username, password)
                self.assertIsNotNone(result)

    def test_sqlite_incompatible_payloads_raise_or_fail_on_vulnerable_login(self):
        for case_name, username, password in NOT_COMPATIBLE_WITH_CURRENT_SQLITE_PAYLOADS:
            with self.subTest(case=case_name):
                try:
                    result = handle_student_login(username, password)
                except sqlite3.Error:
                    continue
                self.assertIsNone(result)

    def test_stacked_queries_do_not_execute_in_sqlite_execute_path(self):
        for case_name, username, password in NOT_DEMONSTRABLE_AGAINST_CURRENT_LOGIN_PATH:
            with self.subTest(case=case_name):
                with self.assertRaises(sqlite3.Error):
                    handle_student_login(username, password)


if __name__ == "__main__":
    unittest.main()
