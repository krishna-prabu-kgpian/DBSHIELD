# Authorization Bypass Attack - Demonstration Guide

## Table of Contents
1. [Setup](#setup)
2. [Running Both Versions](#running-both-versions)
3. [Live Demonstration Script](#live-demonstration-script)
4. [Explaining to Stakeholders](#explaining-to-stakeholders)
5. [Key Points to Highlight](#key-points-to-highlight)

---

## Setup

### Prerequisites
```bash
pip install fastapi uvicorn requests colorama
```

### File Structure
```
Authorization Bypass/
├── app_vulnerable.py        # ❌ Vulnerable backend (NO authorization)
├── app_secure.py            # ✅ Secure backend (WITH authorization)
├── auth.py                  # Authorization utilities
├── test_authorization_bypass.py  # Automated tests
└── README.md                # Documentation
```

---

## Running Both Versions

### Terminal 1: Run Vulnerable Version
```bash
# Navigate to Authorization Bypass directory
cd "Authorization Bypass"

# Start vulnerable version on port 8001
python3 -m uvicorn app_vulnerable:app --host 0.0.0.0 --port 8001 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete
```

### Terminal 2: Run Secure Version
```bash
# Navigate to Authorization Bypass directory
cd "Authorization Bypass"

# Start secure version on port 8002
python3 -m uvicorn app_secure:app --host 0.0.0.0 --port 8002 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8002
INFO:     Application startup complete
```

### Terminal 3: Run Automated Tests
```bash
cd "Authorization Bypass"

# Test both versions
python3 test_authorization_bypass.py --target both

# Or test individually
python3 test_authorization_bypass.py --target vulnerable
python3 test_authorization_bypass.py --target secure
```

---

## Live Demonstration Script

### For In-Person/Video Presentation

**Duration: 15-20 minutes**

#### Part 1: Introduction (2 min)
```
"Today I'll demonstrate a critical authorization bypass vulnerability 
and show you how we fixed it.

In this ERP system, we have three roles:
- Students: Can search courses, enroll, view own grades
- Instructors: Can admit students, assign grades, create assignments
- Admins: Can perform system-level actions

The vulnerability: ANY authenticated user can call ANY endpoint, 
regardless of their role. Let me show you."
```

#### Part 2: Demonstrate Vulnerability (8 min)

**Show 1: Student Views Other Student's Grades**

```bash
# Terminal command to show
curl -X POST http://localhost:8001/api/student/view-grades \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "target_student"
  }'
```

**Response (VULNERABLE):**
```json
{
  "grades": [
    {"course": "CS101", "grade": "A"},
    {"course": "MA201", "grade": "B+"}
  ]
}
```

**Explain:** "A student just accessed another student's grades without any permission check. This is a privacy breach."

---

**Show 2: Student Modifies Grades (as Instructor)**

```bash
curl -X POST http://localhost:8001/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "anyone",
    "course_code": "CS101",
    "grade": "F"
  }'
```

**Response (VULNERABLE):**
```json
{
  "message": "Grade F assigned to anyone for CS101."
}
```

**Explain:** "A student just assigned an 'F' grade to another student by calling an instructor-only endpoint. There's no verification of user role."

---

**Show 3: Student Calls Admin Endpoint**

```bash
curl -X POST http://localhost:8001/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM users WHERE role=\"admin\""
  }'
```

**Response (VULNERABLE):**
```json
{
  "message": "Admin action placeholder executed: SELECT * FROM users WHERE role=\"admin\""
}
```

**Explain:** "A student can now execute admin commands. They could have attempted to drop tables, modify system settings, or export sensitive data."

---

#### Part 3: Show the Secure Version (5 min)

**Show 1: Student Creating Own Request with Headers**

```bash
curl -X POST http://localhost:8002/api/student/view-grades \
  -H "Content-Type: application/json" \
  -H "X-User: student1" \
  -H "X-Role: student" \
  -d '{
    "student_username": "other_student"
  }'
```

**Response (SECURE - BLOCKED):**
```json
{
  "detail": "Access denied. Users can only view their own grades."
}
```

**Status Code: 403 Forbidden**

**Explain:** "Now the endpoint checks if the student is viewing their own data. The request is blocked."

---

**Show 2: Student Attempting Instructor Endpoint**

```bash
curl -X POST http://localhost:8002/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -H "X-User: student1" \
  -H "X-Role: student" \
  -d '{
    "student_username": "anyone",
    "course_code": "CS101",
    "grade": "F"
  }'
```

**Response (SECURE - BLOCKED):**
```json
{
  "detail": "Access denied. This endpoint requires role: instructor. You have role: student"
}
```

**Status Code: 403 Forbidden**

**Explain:** "Before executing the action, the system checks: 'Is this user an instructor?' When it checks your role as 'student', it denies access."

---

**Show 3: Legitimate Instructor Request**

```bash
curl -X POST http://localhost:8002/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -H "X-User: instructor_user" \
  -H "X-Role: instructor" \
  -d '{
    "student_username": "john_doe",
    "course_code": "CS101",
    "grade": "A"
  }'
```

**Response (SECURE - ALLOWED):**
```json
{
  "message": "Grade A assigned to john_doe for CS101."
}
```

**Explain:** "When an actual instructor makes the request, it's allowed. The authorization check passes because the role matches."

---

#### Part 4: Show Automated Test Results (3 min)

```bash
python3 test_authorization_bypass.py --target both
```

**Explain the output:**
- Vulnerable version: "Tests PASSED" = Vulnerability confirmed
- Secure version: "Tests PASSED" = Vulnerability fixed

---

## Explaining to Stakeholders

### For Technical Audience (Developers/Security Team)

**Key Points:**
1. **Missing Authorization Layer**: The backend authenticates users but never verifies their role for protected endpoints
2. **Attack Vector**: Any authenticated user can craft HTTP requests to protected endpoints
3. **Data Exposure**: Cross-student access to grades, assignments, etc.
4. **Privilege Escalation**: Students can modify grades, admit/reject themselves from courses
5. **Fix**: Role-based access control (RBAC) middleware

**Code Example to Show:**

Vulnerable:
```python
@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload):
    # ❌ WRONG: No role check!
    return assign_grade_placeholder(...)
```

Secure:
```python
@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload: GradeStudentPayload, request: Request):
    # ✅ RIGHT: Verify role before execution
    username, role = extract_user_role(request)
    if role != "instructor":
        raise HTTPException(status_code=403, detail="...")
    return assign_grade_placeholder(...)
```

---

### For Non-Technical Stakeholders (Management/Business)

**Simplify the Explanation:**

"Imagine a lock on a door that only checks 'Is someone there?' but never checks 'Are they allowed to be here?'

In our system:
- ❌ **Problem**: We verify users log in (lock works), but don't verify their access level
- ✅ **Solution**: We added a second check that verifies both identity AND permission

**Real-World Impact:**
- A student could change their own grade
- A student could remove themselves from courses
- A student could access other students' private information
- The system could be compromised"

---

## Key Points to Highlight

### 1. Authentication vs Authorization
- **Authentication**: "Who are you?" (Login with username/password)
- **Authorization**: "What are you allowed to do?" (Role-based access)
- **Both are needed** for security

### 2. The Principle of Least Privilege
- Users should only access resources they need
- Students shouldn't access instructor functions
- Each role has specific permissions

### 3. Defense in Depth
- Multiple layers of security checks
- Don't rely on a single mechanism
- Client-side validation is not enough

### 4. Test Coverage
- Automated tests verify security controls
- Test both positive cases (allowed) and negative cases (denied)
- Run tests in CI/CD pipeline

### 5. Code Architecture
- Use decorators/middleware for consistent checking
- Don't repeat authorization logic in each endpoint
- Centralize auth logic for easier maintenance

---

## Appendix: Custom Test Cases

Create additional tests by modifying `test_authorization_bypass.py`:

```python
# Add this test case
def test_instructor_cannot_access_admin():
    """Ensure instructors cannot access admin endpoints."""
    status, resp, err = make_request(
        SECURE_URL,
        "/api/admin/action",
        payload={"query": "SELECT * FROM users"},
        user_role="instructor"
    )
    # Should return 403 Forbidden
    assert status == 403
    assert "Access denied" in str(resp)
```

---

## Presentation Checklist

- [ ] Both backends running on different ports
- [ ] Test script ready to run
- [ ] cURL commands ready to copy-paste
- [ ] Screenshots or recording prepared
- [ ] Explanations prepared for each attack vector
- [ ] Questions ready for audience engagement
- [ ] Time allocation verified (should be 15-20 min total)

---

## Q&A Preparation

**Q: Why didn't you use JWT tokens?**
A: For this demo, we use headers to simulate JWT claims. In production, you'd:
1. Extract JWT from Authorization header
2. Validate signature
3. Extract role from claims
4. Perform authorization check

**Q: How does this scale?**
A: Use a decorator/middleware pattern so you don't repeat code:
```python
@require_role("instructor", "admin")
def protected_endpoint():
    ...
```

**Q: What about complex permissions?**
A: Consider using a policy engine like Casbin or Rego for complex rules.

**Q: How do you test this?**
A: Write automated tests for each role/endpoint combination, as shown in our test script.

---

## Success Metrics

After this presentation, stakeholders should understand:
- ✓ What the vulnerability is
- ✓ How it can be exploited
- ✓ How the fix works
- ✓ Why it's important
- ✓ How to test similar issues in other parts of the code
