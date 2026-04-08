# Authorization Bypass Attack & Prevention

---

## Overview

Authorization Bypass attacks occur when an attacker circumvents role-based access controls (RBAC) by directly accessing endpoints meant for specific user roles without proper verification. In the current DBSHIELD system, **ANY authenticated user can call ANY endpoint regardless of their role**.

**Impact Severity: CRITICAL**
- Students can modify grades
- Students can admit/reject other students from courses
- Students can execute admin-level actions
- Instructors can perform admin operations

---

## The Vulnerability: Lack of Authorization Checks

### Current Vulnerable Pattern

The backend has **authentication** (login) but **NO authorization** (role verification).

```python
@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload) -> dict[str, str]:
    # ❌ NO CHECK: Is the caller actually an instructor?
    return admit_student_placeholder(payload.student_username, payload.course_code)
```

A student can call this endpoint and admit themselves to courses, or modify other students' status.

---

## How to Demonstrate the Vulnerability

### Step 1: Login as a Student

```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "student_user",
    "password": "password123"
  }'
```

**Expected Response:**
```json
{
  "message": "Login successful.",
  "username": "student_user",
  "role": "student",
  "name": "John Student"
}
```

### Step 2: Use Student Role to Call Instructor Endpoint

As a student user, attempt to admit another student (should be INSTRUCTOR ONLY):

```bash
curl -X POST http://localhost:8000/api/instructor/admit-student \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "target_student",
    "course_code": "CS101"
  }'
```

**Vulnerable Response (SHOULD FAIL BUT DOESN'T):**
```json
{
  "message": "Instructor admitted target_student to CS101."
}
```

### Step 3: Student Views Other Students' Grades

```bash
curl -X POST http://localhost:8000/api/student/view-grades \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "other_student"  # Access someone else's grades
  }'
```

**Vulnerable Response (Privacy Breach):**
```json
{
  "grades": [
    {"course": "CS101", "grade": "A"},
    {"course": "MA201", "grade": "B+"}
  ]
}
```

---

## The Fix: Role-Based Authorization

The secure version implements **middleware-based authorization** that:

1. **Extracts user role from request** (via JWT token or session)
2. **Validates role against endpoint requirements** before executing
3. **Prevents unauthorized cross-role data access**

See `auth.py` for secure implementation and `app_secure.py` for the fixed backend.

---

## Key Authorization Principles

### 1. Verify User Identity & Role
- Every protected endpoint must know WHO is calling
- Extract from JWT token, session, or request context

### 2. Check Role Before Execution
- Student endpoints: Only for role="student"
- Instructor endpoints: Only for role="instructor"  
- Admin endpoints: Only for role="admin"

### 3. Enforce Data Isolation
- Students can only view/modify their own data
- No cross-student data access without authorization

### 4. Fail Securely
- Return `403 Forbidden` for insufficient permissions
- Never expose internal logic or data in error messages

---

## Testing Checklist

Use the `test_authorization_bypass.py` script to verify vulnerabilities and fixes:

```bash
# Test vulnerable version
python3 test_authorization_bypass.py --target vulnerable

# Test secure version
python3 test_authorization_bypass.py --target secure
```

---

## Files Structure

```
Authorization Bypass/
├── README.md                         # This file
├── auth.py                          # Secure authorization utilities
├── app_vulnerable.py                # ❌ Vulnerable backend (current)
├── app_secure.py                    # ✅ Fixed backend with RBAC
├── test_authorization_bypass.py     # Automated vulnerability demo
└── DEMONSTRATION_GUIDE.md           # Step-by-step tutorial
```
