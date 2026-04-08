# Authorization Bypass - Getting Started

## What You Got

I've created a complete **Authorization Bypass** attack demonstration project, similar to your DDOS prevention module structure. This includes:

✅ Vulnerable Backend (`app_vulnerable.py`) - Shows the flaw  
✅ Secure Backend (`app_secure.py`) - Shows the fix  
✅ Authorization Utilities (`auth.py`) - Reusable code  
✅ Automated Tests (`test_authorization_bypass.py`) - Verify everything  
✅ Documentation - Full guides for presenting  

## The Vulnerability (30 seconds)

Currently, your ERP system:
- ✅ Checks who you are (Authentication)
- ❌ **DOESN'T check what you can do** (Authorization)

**Result:** A student can:
- View other student's grades
- Modify anyone's grades
- Admit/reject students from courses
- Execute admin commands

## Get Started in 5 Minutes

### 1. Open Three Terminal Windows

**Terminal 1: Run Vulnerable Version**
```bash
cd "Authorization Bypass"
python3 -m uvicorn app_vulnerable:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2: Run Secure Version**
```bash
cd "Authorization Bypass"
python3 -m uvicorn app_secure:app --host 0.0.0.0 --port 8002 --reload
```

**Terminal 3: Run Tests**
```bash
cd "Authorization Bypass"
python3 test_authorization_bypass.py --target both
```

### 2. Quick Live Demo

Open a 4th terminal and run this:

```bash
# Show vulnerability: Student viewing other student's grades
curl http://localhost:8001/api/student/view-grades \
  -H "Content-Type: application/json" \
  -d '{"student_username": "other_student"}'
```

**Vulnerable response (WRONG):**
```json
{"grades": [{"course": "CS101", "grade": "A"}]}
```

**Now try on secure version:**
```bash
curl http://localhost:8002/api/student/view-grades \
  -H "Content-Type: application/json" \
  -H "X-User: student1" \
  -H "X-Role: student" \
  -d '{"student_username": "other_student"}'
```

**Secure response (CORRECT):**
```json
{"detail": "Access denied. Users can only view their own grades."}
```

## File Structure

```
Authorization Bypass/
├── README.md                    ← Start here for full tech details
├── QUICK_START.md              ← 30-second overview
├── DEMONSTRATION_GUIDE.md      ← How to present to others
├── app_vulnerable.py           ← ❌ Current (broken)
├── app_secure.py               ← ✅ Fixed version
├── auth.py                     ← Authorization code
└── test_authorization_bypass.py ← Automated tests
```

## Three Attack Scenarios to Show

### Attack 1: Data Theft
```bash
# Student accesses other_student's grades
POST /api/student/view-grades
Payload: {"student_username": "other_student"}
Vulnerable: WORKS ❌
Secure: BLOCKED ✓
```

### Attack 2: Privilege Escalation
```bash
# Student changes a grade (instructor-only action)
POST /api/instructor/assign-grade
Payload: {"student_username": "john", "course_code": "CS101", "grade": "F"}
Vulnerable: WORKS ❌
Secure: BLOCKED ✓
```

### Attack 3: System Compromise
```bash
# Student calls admin endpoint
POST /api/admin/action
Payload: {"query": "DROP TABLE users;"}
Vulnerable: WORKS ❌
Secure: BLOCKED ✓
```

## The Core Fix

In vulnerable version:
```python
@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload):
    # ❌ WRONG: Accepts anyone
    return assign_grade_placeholder(...)
```

In secure version:
```python
@app.post("/api/instructor/assign-grade")
def instructor_assign_grade(payload, request: Request):
    # ✅ RIGHT: Check role first
    username, role = extract_user_role(request)
    
    if role != "instructor":
        raise HTTPException(status_code=403, detail="Instructors only")
    
    return assign_grade_placeholder(...)
```

**That's it!** Just add role verification before executing sensitive operations.

## How to Demonstrate to Others

### Quick Demo (5 minutes)
1. Show the vulnerable endpoint accepting a student's instructor request
2. Show the secure endpoint blocking the same request
3. Show a legitimate instructor request working on secure version

### Full Presentation (15-20 minutes)
See `DEMONSTRATION_GUIDE.md` for step-by-step script with:
- Introduction
- Three attack demonstrations
- How the fix works
- Test results

### For Stakeholders
- **Technical**: Explain RBAC, middleware, and defense layers
- **Non-Technical**: "It's like a check that verifies not just 'are you here?' but 'are you supposed to be here?'"

## Testing

Run automated tests to verify:
```bash
python3 test_authorization_bypass.py --target both
```

This will:
- ✓ Confirm vulnerabilities in `app_vulnerable.py`
- ✓ Verify fixes in `app_secure.py`
- ✓ Show side-by-side comparison

## Key Learning Points

1. **Authentication** (Login) ≠ **Authorization** (Permissions)
2. Need **BOTH** for security
3. Use **Role-Based Access Control (RBAC)**
4. **Fail securely** - return 403 Forbidden, not 200 OK
5. **Test everything** - automated tests catch regressions

## Next Steps

### To Deepen Your Knowledge:
1. Read `README.md` for technical details
2. Study `app_secure.py` to see actual implementation
3. Modify `test_authorization_bypass.py` to create custom tests
4. Try more complex authorization rules

### To Extend the Project:
1. Add JWT token support instead of X-User/X-Role headers
2. Implement more granular permissions (can't just "student")
3. Add audit logging for failed authorization attempts
4. Implement role hierarchies (admin > instructor > student)

### To Present to Your Class:
1. Use `DEMONSTRATION_GUIDE.md`
2. Have both backends running
3. Have test commands ready
4. Prepare slides with the attack scenarios
5. Practice the live demo beforehand

## Important Notes

- ✅ This is an **educational project** for understanding security
- ✅ Shows **real vulnerabilities** that exist in actual systems
- ❌ **NOT for production use** without proper hardening:
  - Use real JWT tokens, not headers
  - Add database access controls
  - Implement HTTPS/TLS
  - Add rate limiting
  - Enable detailed logging

## Questions?

Refer to the relevant document:
- **How does it work?** → `README.md`
- **30-second version?** → `QUICK_START.md`  
- **How to present?** → `DEMONSTRATION_GUIDE.md`
- **See working code?** → `app_secure.py`
- **Test it?** → Run `test_authorization_bypass.py`

Good luck with your presentation and learning! This is an excellent hands-on example of a critical real-world vulnerability.
