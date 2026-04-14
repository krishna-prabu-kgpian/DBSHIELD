# python3 -m unittest backend/ddos_prevention/test_app_protection.py

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path

from fastapi.responses import JSONResponse
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ddos_prevention.app_protection import AppDDoSProtection, AppDDoSProtectionSettings
import ddos_prevention.app_protection as app_protection_module


class ExplodingSemaphore:
    async def __aenter__(self):
        raise AssertionError("login semaphore should not be used when protection is disabled")

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestAppDDoSProtection(unittest.TestCase):
    def _make_request(self, headers: dict[str, str] | None = None) -> Request:
        raw_headers = [
            (key.lower().encode("utf-8"), value.encode("utf-8"))
            for key, value in (headers or {}).items()
        ]
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "headers": raw_headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        return Request(scope, receive)

    def test_disabled_run_login_skips_the_concurrency_gate(self):
        protection = AppDDoSProtection(AppDDoSProtectionSettings(enabled=False))
        protection._login_semaphore = ExplodingSemaphore()
        original_run_in_threadpool = app_protection_module.run_in_threadpool

        async def immediate_threadpool(func, *args, **kwargs):
            return func(*args, **kwargs)

        app_protection_module.run_in_threadpool = immediate_threadpool

        try:
            async def run():
                return await protection.run_login(
                    lambda username, password: {"username": username, "password": password},
                    "student1",
                    "pass1",
                )

            result = asyncio.run(run())
        finally:
            app_protection_module.run_in_threadpool = original_run_in_threadpool

        self.assertEqual(result["username"], "student1")
        self.assertEqual(result["password"], "pass1")

    def test_enabled_middleware_blocks_untrusted_forwarded_for_headers(self):
        protection = AppDDoSProtection(AppDDoSProtectionSettings(enabled=True))
        request = self._make_request({"X-Forwarded-For": "10.0.0.1"})

        async def call_next(_: Request):
            return JSONResponse({"status": "ok"})

        response = asyncio.run(protection.middleware(request, call_next))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.body)["detail"],
            "Blocked: untrusted X-Forwarded-For header",
        )

    def test_disabled_middleware_leaves_forwarded_for_headers_alone(self):
        protection = AppDDoSProtection(AppDDoSProtectionSettings(enabled=False))
        request = self._make_request({"X-Forwarded-For": "10.0.0.1"})

        async def call_next(_: Request):
            return JSONResponse({"status": "ok"})

        response = asyncio.run(protection.middleware(request, call_next))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.body), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
