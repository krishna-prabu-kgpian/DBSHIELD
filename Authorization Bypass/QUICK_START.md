# Quick Reference Guide

## The Vulnerability in 30 Seconds

**Authorization Bypass** = Users can access endpoints they shouldn't

**Current Problem:**
```python
@app.post("/api/instructor/assign-grade")
def assign_grade(payload):
    # ❌ Anyone can call this, not just instructors!
    return modify_student_grade(payload)
```

**Current Impact:**
- Student A can view Student B's grades
- Student A can assign themselves an 'A' in any course
- Student A can admit/reject other students
- Student A can execute admin commands

---

## The Fix in 30 Seconds

```python
@app.post("/api/instructor/assign-grade")
def assign_grade(payload, request: Request):
    # ✅ Check the user's role first
    username, role = extract_user_role(request)
    
    if role != "instructor":
        raise HTTPException(status_code=403, detail="Instructors only")
    
    return modify_student_grade(payload)
```

---

## Quick Demo (5 minutes)

### Step 1: Login as Student
```bash
curl http://localhost:8001/api/login -d '{"username":"student1","password":"pass1"}'
```

### Step 2: Attempt Instructor Action (Vulnerable - WORKS)
```bash
curl http://localhost:8001/api/instructor/assign-grade \
  -d '{"student_username":"john","course_code":"CS101","grade":"F"}'
```
**Result: Success ❌ (BAD - should fail)**

### Step 3: Same Attack on Secure Version (BLOCKED)
```bash
curl http://localhost:8002/api/instructor/assign-grade \
  -H "X-User: student1" \
  -H "X-Role: student" \
  -d '{"student_username":"john","course_code":"CS101","grade":"F"}'
```
**Result: 403 Forbidden ✓ (GOOD - blocked)**

---

## Files You Need

| File | Purpose |
|------|---------|
| `app_vulnerable.py` | Demonstrates the vulnerability |
| `app_secure.py` | Shows the fixed version |
| `auth.py` | Authorization utilities |
| `test_authorization_bypass.py` | Automated attack + verification tests |
| `README.md` | Full technical documentation |
| `DEMONSTRATION_GUIDE.md` | How to present to stakeholders |

---

## Three Attack Scenarios to Demonstrate

### Attack 1: Data Theft (View Other Student's Grades)
```bash
# As student, view other_student's grades
POST /api/student/view-grades
{"student_username": "other_student"}

# Vulnerable: Returns grades ❌
# Secure: 403 Forbidden ✓
```

### Attack 2: Privilege Escalation (Assign Grades)
```bash
# As student, call instructor endpoint
POST /api/instructor/assign-grade
{"student_username": "rival", "course_code": "CS101", "grade": "F"}

# Vulnerable: Grade assigned ❌
# Secure: 403 Forbidden ✓
```

### Attack 3: System-Level Access (Admin Commands)
```bash
# As student, call admin endpoint
POST /api/admin/action
{"query": "DROP TABLE users;"}

# Vulnerable: Command accepted ❌
# Secure: 403 Forbidden ✓
```

---

## Testing Results

**Run automated tests:**
```bash
python3 test_authorization_bypass.py --target both
```

**Expected Output:**
- Vulnerable version: "5/5 tests PASSED" (= vulnerability confirmed)
- Secure version: "5/5 tests PASSED" (= vulnerability fixed)

---

## Key Authorization Concepts

### 1. Defense Layers
```
Request comes in
    ↓
[Authentication] - Who are you?
    ↓
[Authorization] - What can you do?
    ↓
[Execution] - Do your action
```

### 2. Role-Based Access Control (RBAC)
```
Student Role: Can view own grades, search courses, enroll
Instructor Role: Can assign grades, admit students, create assignments
Admin Role: Can do anything
```

### 3. Fail Securely
```
Always respond with 403 Forbidden (not 500 Internal Server Error)
Never expose internal logic in error messages
```

---

## Before/After Comparison

| Aspect | Vulnerable | Secure |
|--------|-----------|--------|
| Authentication | ✓ (Login works) | ✓ (Login works) |
| Authorization | ✗ (No checks) | ✓ (Role verified) |
| Data Isolation | ✗ (Anyone can see anything) | ✓ (Users see own data) |
| Endpoint Protection | ✗ (All endpoints open) | ✓ (Role-restricted) |
| Error Responses | 200 OK (wrong!) | 403 Forbidden (right!) |

---

## Learning Outcomes

After understanding this vulnerability, you should know:

1. **What** authorization bypass is
2. **Why** it's dangerous (data theft, privilege escalation, system compromise)
3. **How** to identify it (no role checks in code)
4. **What** the fix is (add authorization middleware)
5. **How** to test it (automated tests)
6. **How** to present it (clear attack + defense demos)

---

## Production Checklist

Before deploying authorization in real systems:

- [ ] Use industry-standard token format (JWT, OAuth2)
- [ ] Validate token signature cryptographically
- [ ] Check token expiration
- [ ] Implement role-based access control
- [ ] Test ALL role combinations
- [ ] Use secure headers (HTTPS, secure cookies)
- [ ] Implement audit logging for failed attempts
- [ ] Use security scanning in CI/CD
- [ ] Conduct security code review
- [ ] Perform penetration testing

---

## Resources for Deeper Learning

- OWASP: Authorization and Access Control
- JWT.io: Understanding JWT tokens
- Role-Based Access Control (RBAC) patterns
- Authorization failures in real-world breaches

---

## Support

For questions about this implementation:
1. Check `README.md` for technical details
2. Review `DEMONSTRATION_GUIDE.md` for presentation tips
3. Study `app_secure.py` for proper implementation
4. Run tests to see working examples
