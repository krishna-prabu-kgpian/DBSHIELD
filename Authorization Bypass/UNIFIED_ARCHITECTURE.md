# Authorization Bypass Demonstration - Complete System

## 🎯 Unified Architecture

Both versions now use **Bearer token authentication** but differ in **authorization checks**:

```
┌──────────────────────────────────────────────────────────────────┐
│                      CLIENT REQUEST                              │
│  "I want to view other student's grades"                         │
└──────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
    ┌───────────▼──────────┐       ┌──────────▼────────────┐
    │ VULNERABLE SERVER    │       │ SECURE SERVER         │
    │ (Port 8001)          │       │ (Port 8002)           │
    └──────────┬───────────┘       └───────────┬───────────┘
               │                               │
    ┌──────────▼──────────────┐   ┌──────────▼─────────────┐
    │ Step 1: AUTHENTICATE    │   │ Step 1: AUTHENTICATE   │
    │ ✅ Token validation     │   │ ✅ Token validation    │
    │    - Token exists?      │   │    - Token exists?     │
    │    - Valid format?      │   │    - Valid format?     │
    │    - Lookup in store    │   │    - Lookup in store   │
    │ Result: PASS ✅         │   │ Result: PASS ✅        │
    └──────────┬──────────────┘   └──────────┬────────────┘
               │                              │
    ┌──────────▼──────────────┐   ┌──────────▼─────────────┐
    │ Step 2: AUTHORIZE       │   │ Step 2: AUTHORIZE      │
    │ ❌ NO ROLE CHECK        │   │ ✅ ROLE CHECK          │
    │    - Ignore role in     │   │    - Token role?       │
    │      token              │   │      "student"         │
    │    - Execute endpoint   │   │    - Endpoint needs?   │
    │      anyway             │   │      "student"         │
    │ Result: PASS ❌         │   │ Result: FAIL ✅        │
    └──────────┬──────────────┘   └──────────┬────────────┘
               │                              │
    ┌──────────▼──────────────┐   ┌──────────▼─────────────┐
    │ RESPONSE: 200 OK        │   │ RESPONSE: 403 FORBIDDEN│
    │                         │   │                        │
    │ grades: [               │   │ detail: "Access denied │
    │   {...},                │   │  Only students can     │
    │   {...}                 │   │  view their own grades"│
    │ ]                       │   │                        │
    └─────────────────────────┘   └────────────────────────┘

    ❌ VULNERABLE               ✅ SECURE
```

---

## 📊 Request Flow Comparison

### Unauthenticated Request

```bash
curl -X POST http://localhost:8001/api/student/view-grades \
  -d '{"student_username": "alice"}'
```

| Stage | Vulnerable | Secure |
|-------|---|---|
| 1. Check Authorization header | ❌ Missing | ❌ Missing |
| 2. Validate token | ❌ FAIL | ❌ FAIL |
| Response | **401 UNAUTHORIZED** | **401 UNAUTHORIZED** |

**Result:** Same! Both reject unauthenticated requests ✅

---

### Authenticated + Unauthorized Request (Student accessing instructor endpoint)

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/login \
  -d '{"username":"student1","password":"pass1"}' | jq -r '.token')

curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username":"target","course_code":"CS101"}'
```

| Stage | Vulnerable | Secure |
|-------|---|---|
| 1. Check Authorization header | ✅ Present | ✅ Present |
| 2. Validate token | ✅ Valid | ✅ Valid |
| 3. Extract role from token | ✅ role="student" | ✅ role="student" |
| 4. Check role matches endpoint | ❌ SKIPPED | ✅ CHECKS: role != "instructor" |
| 5. Response | **200 OK** | **403 FORBIDDEN** |

**Result:** Vulnerable accepts, Secure blocks! ✅

---

### Authenticated + Authorized Request (Instructor accessing instructor endpoint)

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/api/login \
  -d '{"username":"instructor1","password":"inst123"}' | jq -r '.token')

curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username":"target","course_code":"CS101"}'
```

| Stage | Vulnerable | Secure |
|-------|---|---|
| 1. Check Authorization header | ✅ Present | ✅ Present |
| 2. Validate token | ✅ Valid | ✅ Valid |
| 3. Extract role from token | ✅ role="instructor" | ✅ role="instructor" |
| 4. Check role matches endpoint | ❌ SKIPPED | ✅ CHECKS: role == "instructor" ✅ |
| 5. Response | **200 OK** | **200 OK** |

**Result:** Both accept! ✅

---

## 🧪 Complete Test Scenarios

### Test Matrix (9 scenarios)

| User | Endpoint | Vulnerable | Secure | Reason |
|------|----------|---|---|---|
| Unauthenticated | student/view-grades | ❌ 401 | ❌ 401 | No token |
| Student | student/view-own-grades | ✅ 200 | ✅ 200 | Allowed |
| Student | student/view-other-grades | ✅ 200 | ❌ 403 | No role check |
| Student | instructor/admit-student | ✅ 200 | ❌ 403 | No role check |
| Student | instructor/assign-grade | ✅ 200 | ❌ 403 | No role check |
| Student | admin/action | ✅ 200 | ❌ 403 | No role check |
| Instructor | instructor/admit-student | ✅ 200 | ✅ 200 | Role matches |
| Admin | admin/action | ✅ 200 | ✅ 200 | Role matches |

**Key insight:** Vulnerable version treats all authenticated requests the same. Secure version enforces role-based access.

---

## 🔐 Security Layers

### Layer 1: Network Level
```
Both versions use HTTP (localhost only for demo)
Production would use HTTPS/TLS
```

### Layer 2: Authentication Level
```
✅ BOTH ENFORCE:
- Username/password required
- Bearer token generated
- Token lookup required for all endpoints
```

### Layer 3: Authorization Level
```
❌ VULNERABLE: No checks
   if (has_token) { execute() }

✅ SECURE: Role-based checks
   if (has_token) {
       if (token_role == endpoint_role) {
           execute()
       } else {
           forbidden()
       }
   }
```

### Layer 4: Data Ownership Level
```
❌ VULNERABLE: No checks
   return get_student_grades(requested_username)

✅ SECURE: Verify ownership
   if (requested_username == token_username) {
       return get_student_grades(requested_username)
   } else {
       forbidden()
   }
```

---

## 📋 Running the System

### Setup
```bash
# Initialize database
cd database/
python3 seed_data.py --rows 20000
# Creates: 1 admin, 2 instructors, 19997 students

# Verify data
sqlite3 dbshield.sqlite3 "SELECT COUNT(*), role FROM users GROUP BY role;"
# admin|1
# instructor|2  
# student|19997
```

### Terminal 1: Vulnerable Version
```bash
cd Authorization\ Bypass/
python3 app_vulnerable.py --port 8001

# Output:
# Uvicorn running on http://0.0.0.0:8001
```

### Terminal 2: Secure Version
```bash
cd Authorization\ Bypass/
python3 app_secure.py --port 8002

# Output:
# Uvicorn running on http://0.0.0.0:8002
```

### Terminal 3: Automated Tests
```bash
cd Authorization\ Bypass/
python3 test_authorization_bypass.py --target both

# Output:
# VULNERABLE VERSION: ✓all attacks work
# SECURE VERSION: ✓all attacks blocked
```

---

## 🎓 Teaching Narrative

### Part 1: Setup (5 min)
"We have a university ERP system. Students can view grades, instructors can assign grades, admins manage the system."

### Part 2: Authentication (5 min)
"First, we require login - username and password. The system returns a token proving 'I am john_smith'."

Show: Both versions require Bearer token on all endpoints.

### Part 3: The Vulnerability (10 min)
"But just because you're logged in doesn't mean you should access everything!"

Show vulnerable version:
```bash
# Student logs in, gets token
TOKEN=$(... login student1 ...)

# Student tries to assign failing grade
curl -X POST :8001/api/instructor/assign-grade \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username": "rival", "course_code": "CS101", "grade": "F"}'

# Result: ✅ 200 OK - STUDENT CHANGED SOMEONE'S GRADE!
```

"Notice: The system checked the token was valid, but never checked the role!"

### Part 4: The Fix (10 min)
"What if we add a simple role check?"

Show secure version:
```bash
# Same student with same token
curl -X POST :8002/api/instructor/assign-grade \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username": "rival", "course_code": "CS101", "grade": "F"}'

# Result: ❌ 403 FORBIDDEN - ACCESS DENIED
# "Access denied. Only instructors can assign grades. You have role: student"
```

"Now it works! The system checks: 'This endpoint needs role=instructor, but token says role=student, so DENIED.'"

### Part 5: The Pattern (5 min)
"Every endpoint must answer two questions:
1. 'Are you who you claim to be?' (authentication)
2. 'Do you have permission to do this?' (authorization)

If either answer is NO, access is DENIED."

---

## 🔍 Code Architecture

### Vulnerable Version Structure

```
app_vulnerable.py
├── extract_user_role(request) 
│   ├── Get Authorization header
│   ├── Extract token
│   └── Verify token exists ✅
│
├── /api/login
│   ├── Check username/password ✅
│   ├── Create token ✅
│   └── Return token
│
└── Protected endpoints
    ├── /api/student/view-grades
    ├── /api/instructor/admit-student
    ├── /api/instructor/assign-grade
    └── /api/admin/action
    
    Each endpoint:
    ├─ Calls extract_user_role() ✅
    ├─ Gets username, role ✅
    └─ Executes action (ignores role) ❌
```

### Secure Version Structure

```
app_secure.py
├── extract_user_role(request)
│   ├── Get Authorization header
│   ├── Extract token
│   ├── Verify token exists ✅
│   └── Get role from token ✅
│
├── require_role(*allowed_roles) [Decorator]
│   ├── Calls extract_user_role() ✅
│   ├── Checks role in allowed_roles ✅
│   └── Raises 403 if not allowed
│
├── /api/login
│   ├── Check username/password ✅
│   ├── Create token ✅
│   └── Return token
│
└── Protected endpoints
    ├── @require_role("student")
    │   └── /api/student/view-grades
    │
    ├── @require_role("instructor")
    │   ├── /api/instructor/admit-student
    │   ├── /api/instructor/assign-grade
    │   └── /api/instructor/create-assignment
    │
    └── @require_role("admin")
        └── /api/admin/action
    
    Each endpoint:
    ├─ Decorator checks role ✅
    ├─ Only correct roles proceed
    └─ Executes action ✅
```

---

## ✅ Verification Checklist

- [x] Both versions require Bearer tokens
- [x] Vulnerable version has NO role checks
- [x] Secure version has role checks
- [x] Test suite demonstrates attacks on vulnerable version
- [x] Test suite shows attacks blocked on secure version
- [x] Documentation explains the difference
- [x] Code is commented explaining vulnerabilities
- [x] All scenarios are testable with curl

---

## 📚 Documentation Files

1. **AUTHENTICATION_VS_AUTHORIZATION.md** - This new file explaining the key difference
2. **AUTHENTICATION_FIX.md** - Token-based authentication explanation
3. **COMPLETE_IMPLEMENTATION_GUIDE.md** - Full system details
4. **PROFESSORS_PRESENTATION_GUIDE.md** - Teaching materials
5. **BEARER_TOKEN_QUICK_START.md** - Quick reference guide

---

## 🎬 Live Demo Flow

```bash
# Show both servers starting with auth required
Terminal 1 & 2: python3 app_*.py --port 800X

# Attempt unauthenticated request
curl http://localhost:8001/api/student/view-grades
# Results: Both return 401 (good!)

# Login and get token  
TOKEN=$(curl -X POST http://localhost:8001/api/login \
  -d '{"username":"student1","password":"pass1"}' | jq -r '.token')

# Try unauthorized action (vulnerable)
curl -X POST http://localhost:8001/api/instructor/assign-grade \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username":"target", "grade":"F", "course_code":"CS101"}'
# Result: 200 OK - VULNERABLE! ❌

# Same request (secure)
curl -X POST http://localhost:8002/api/instructor/assign-grade \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username":"target", "grade":"F", "course_code":"CS101"}'
# Result: 403 FORBIDDEN - SECURE! ✅

# Run full test suite
python3 test_authorization_bypass.py --target both
```

---

**Version:** 3.0 (With Authentication & Authorization Separation)  
**Status:** ✅ Complete & Ready for Production Demo  
**Last Updated:** 2024  
**Tested:** ✅ All scenarios verified
