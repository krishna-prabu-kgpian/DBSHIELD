#!/usr/bin/env python3
"""
Authorization Bypass Attack Demonstration Script
================================================

This script demonstrates the authorization bypass vulnerability and verifies the fix.

Usage:
    python3 test_authorization_bypass.py --target vulnerable
    python3 test_authorization_bypass.py --target secure
    python3 test_authorization_bypass.py --target both
"""

import requests
import json
import sys
from typing import Dict, Any
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Configuration
VULNERABLE_URL = "http://localhost:8001"
SECURE_URL = "http://localhost:8002"

# Test user credentials (from seeded data)
TEST_USERS = {
    "student": {"username": "student1", "password": "pass1", "role": "student"},
    "instructor": {"username": "student2", "password": "pass2", "role": "instructor"},  # For demo, using student as instructor
    "admin": {"username": "admin", "password": "admin123", "role": "admin"},
}


class TestResult:
    """Represents the result of a test."""
    
    def __init__(self, name: str, should_pass: bool):
        self.name = name
        self.should_pass = should_pass
        self.passed = False
        self.status_code = None
        self.response = None
        self.error = None
        self.request_info = None
    
    def set_result(self, status_code: int, response: Any, error: str = None, request_info: Dict = None):
        self.status_code = status_code
        self.response = response
        self.error = error
        self.request_info = request_info or {}
        # Determine if test passed/failed
        if self.should_pass:
            self.passed = status_code == 200
        else:
            self.passed = status_code >= 400  # Should be error
    
    def get_symbol(self) -> str:
        if self.passed:
            return f"{Fore.GREEN}✓{Style.RESET_ALL}"
        return f"{Fore.RED}✗{Style.RESET_ALL}"
    
    def print_result(self):
        status = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if self.passed else f"{Fore.RED}FAIL{Style.RESET_ALL}"
        print(f"  {self.get_symbol()} {self.name}: {status}")
        if self.status_code:
            print(f"     HTTP {self.status_code}")
        if self.request_info:
            print(f"     {self.request_info.get('method', 'POST')} {self.request_info.get('url', '')}")
        if self.response:
            # Show truncated response
            resp_str = json.dumps(self.response, indent=2)
            if len(resp_str) > 150:
                print(f"     Response: {resp_str[:150]}...")
            else:
                print(f"     Response: {resp_str}")


def make_request(
    base_url: str, 
    endpoint: str, 
    method: str = "POST",
    payload: Dict[str, Any] = None,
    user_role: str = None
) -> tuple[int, Any, str, Dict]:
    """Make HTTP request with proper headers."""
    url = f"{base_url}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    # Add authentication headers for secured version
    if user_role:
        user_info = TEST_USERS.get(user_role)
        if user_info:
            headers["X-User"] = user_info["username"]
            headers["X-Role"] = user_role
    
    try:
        if method == "POST":
            response = requests.post(url, json=payload, headers=headers, timeout=5)
        else:
            response = requests.get(url, headers=headers, timeout=5)
        
        try:
            return response.status_code, response.json(), None, {"headers": dict(response.headers), "url": url, "method": method}
        except:
            return response.status_code, {"message": response.text}, None, {"headers": dict(response.headers), "url": url, "method": method}
    except requests.exceptions.ConnectionError as e:
        return 0, None, f"Connection error: Server not running on {base_url}", {"url": url, "method": method}
    except requests.exceptions.Timeout:
        return 0, None, "Request timeout", {"url": url, "method": method}
    except Exception as e:
        return 0, None, str(e), {"url": url, "method": method}


def test_vulnerable_version():
    """
    Test the vulnerable version - demonstrates authorization bypass.
    """
    print(f"\n{Fore.YELLOW}{'='*60}")
    print(f"TESTING VULNERABLE VERSION - should show bypass attacks")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    results = []
    
    # First, login as student
    print(f"{Fore.CYAN}1. Logging in as STUDENT user...{Style.RESET_ALL}")
    status, resp, err, req_info = make_request(VULNERABLE_URL, "/api/login", payload=TEST_USERS["student"])
    
    if status != 200:
        print(f"{Fore.RED}   Failed to login: {err}{Style.RESET_ALL}")
        return results
    
    print(f"{Fore.GREEN}   Login successful ✓{Style.RESET_ALL}")
    
    # Test 1: Student viewing other student's grades (should FAIL in secure, PASS in vulnerable)
    print(f"\n{Fore.CYAN}2. ATTACK: Student viewing OTHER student's grades...{Style.RESET_ALL}")
    test = TestResult(
        "Student access to other_student's grades",
        should_pass=True  # Should PASS in vulnerable (bad!), FAIL in secure (good)
    )
    status, resp, err, req_info = make_request(
        VULNERABLE_URL,
        "/api/student/view-grades",
        payload={"student_username": "other_student"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 2: Student calling instructor endpoint (should FAIL in secure, PASS in vulnerable)
    print(f"\n{Fore.CYAN}3. ATTACK: Student calling INSTRUCTOR endpoint (admit-student)...{Style.RESET_ALL}")
    test = TestResult(
        "Student admits another student to course",
        should_pass=True  # Should PASS in vulnerable (bad!), FAIL in secure (good)
    )
    status, resp, err, req_info = make_request(
        VULNERABLE_URL,
        "/api/instructor/admit-student",
        payload={"student_username": "target_student", "course_code": "CS101"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 3: Student assigning grades (should FAIL in secure, PASS in vulnerable)
    print(f"\n{Fore.CYAN}4. ATTACK: Student assigning grades (instructor-only)...{Style.RESET_ALL}")
    test = TestResult(
        "Student assigns grades to another student",
        should_pass=True  # Should PASS in vulnerable (bad!), FAIL in secure (good)
    )
    status, resp, err, req_info = make_request(
        VULNERABLE_URL,
        "/api/instructor/assign-grade",
        payload={"student_username": "target_student", "course_code": "CS101", "grade": "F"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 4: Student calling admin endpoint (should FAIL in secure, PASS in vulnerable)
    print(f"\n{Fore.CYAN}5. ATTACK: Student calling ADMIN endpoint...{Style.RESET_ALL}")
    test = TestResult(
        "Student executes admin action",
        should_pass=True  # Should PASS in vulnerable (bad!), FAIL in secure (good)
    )
    status, resp, err, req_info = make_request(
        VULNERABLE_URL,
        "/api/admin/action",
        payload={"query": "DROP TABLE users;"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    return results


def test_secure_version():
    """
    Test the secure version - demonstrates authorization enforcement.
    """
    print(f"\n{Fore.YELLOW}{'='*60}")
    print(f"TESTING SECURE VERSION - should block all bypass attacks")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    results = []
    
    # Test 1: Student accessing other student's grades (should FAIL - blocked)
    print(f"{Fore.CYAN}1. Student accessing other_student's grades...{Style.RESET_ALL}")
    test = TestResult(
        "Student blocked from accessing other_student's grades",
        should_pass=False  # Should FAIL (good!)
    )
    status, resp, err, req_info = make_request(
        SECURE_URL,
        "/api/student/view-grades",
        payload={"student_username": "other_student"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 2: Student calling instructor endpoint (should FAIL - blocked)
    print(f"\n{Fore.CYAN}2. Student attempting to call instructor endpoint...{Style.RESET_ALL}")
    test = TestResult(
        "Student denied from instructor endpoint (admit-student)",
        should_pass=False  # Should FAIL (good!)
    )
    status, resp, err, req_info = make_request(
        SECURE_URL,
        "/api/instructor/admit-student",
        payload={"student_username": "target_student", "course_code": "CS101"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 3: Student assigning grades (should FAIL - blocked)
    print(f"\n{Fore.CYAN}3. Student attempting to assign grades...{Style.RESET_ALL}")
    test = TestResult(
        "Student denied from assign-grade endpoint",
        should_pass=False  # Should FAIL (good!)
    )
    status, resp, err, req_info = make_request(
        SECURE_URL,
        "/api/instructor/assign-grade",
        payload={"student_username": "target_student", "course_code": "CS101", "grade": "F"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 4: Student calling admin endpoint (should FAIL - blocked)
    print(f"\n{Fore.CYAN}4. Student attempting admin action...{Style.RESET_ALL}")
    test = TestResult(
        "Student denied from admin endpoint",
        should_pass=False  # Should FAIL (good!)
    )
    status, resp, err, req_info = make_request(
        SECURE_URL,
        "/api/admin/action",
        payload={"query": "DROP TABLE users;"},
        user_role="student"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 5: Instructor can call instructor endpoints (should PASS - allowed)
    print(f"\n{Fore.CYAN}5. Instructor calling instructor endpoint...{Style.RESET_ALL}")
    test = TestResult(
        "Instructor allowed to admit student",
        should_pass=True  # Should PASS (good!)
    )
    status, resp, err, req_info = make_request(
        SECURE_URL,
        "/api/instructor/admit-student",
        payload={"student_username": "target_student", "course_code": "CS101"},
        user_role="instructor"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    # Test 6: Admin can call admin endpoints (should PASS - allowed)
    print(f"\n{Fore.CYAN}6. Admin calling admin endpoint...{Style.RESET_ALL}")
    test = TestResult(
        "Admin allowed to execute admin action",
        should_pass=True  # Should PASS (good!)
    )
    status, resp, err, req_info = make_request(
        SECURE_URL,
        "/api/admin/action",
        payload={"query": "SELECT * FROM users;"},
        user_role="admin"
    )
    test.set_result(status, resp, err, req_info)
    results.append(test)
    test.print_result()
    
    return results


def print_summary(vulnerable_results: list, secure_results: list):
    """Print test summary."""
    print(f"\n{Fore.YELLOW}{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    
    if vulnerable_results:
        vulnerable_passed = sum(1 for r in vulnerable_results if r.passed)
        print(f"{Fore.RED}Vulnerable Version: {vulnerable_passed}/{len(vulnerable_results)} tests behaved as expected")
        print(f"   (Tests PASSED = vulnerability confirmed){Style.RESET_ALL}")
    
    if secure_results:
        secure_passed = sum(1 for r in secure_results if r.passed)
        print(f"{Fore.GREEN}Secure Version: {secure_passed}/{len(secure_results)} tests behaved as expected")
        print(f"   (Tests PASSED = vulnerability fixed){Style.RESET_ALL}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_authorization_bypass.py [--target vulnerable|secure|both]")
        print()
        print("Examples:")
        print("  python3 test_authorization_bypass.py --target vulnerable")
        print("  python3 test_authorization_bypass.py --target secure")
        print("  python3 test_authorization_bypass.py --target both")
        sys.exit(1)
    
    target = sys.argv[2] if len(sys.argv) > 2 else "both"
    
    vulnerable_results = []
    secure_results = []
    
    if target in {"vulnerable", "both"}:
        try:
            vulnerable_results = test_vulnerable_version()
        except Exception as e:
            print(f"{Fore.RED}Error testing vulnerable version: {e}{Style.RESET_ALL}")
    
    if target in {"secure", "both"}:
        try:
            secure_results = test_secure_version()
        except Exception as e:
            print(f"{Fore.RED}Error testing secure version: {e}{Style.RESET_ALL}")
    
    if vulnerable_results or secure_results:
        print_summary(vulnerable_results, secure_results)


if __name__ == "__main__":
    main()
