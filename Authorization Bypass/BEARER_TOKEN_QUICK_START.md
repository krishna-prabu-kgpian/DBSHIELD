# Quick Start - Bearer Token Authentication Demo

## Test Credentials

Use these credentials to test the authentication system:

```
Student:      username: student1    password: pass1
Student:      username: student2    password: pass2
Instructor:   username: instructor1 password: inst123
Admin:        username: admin       password: admin123
```

---

## Demo Script

### Step 1: Start Both Servers

```bash
# Terminal 1 - Vulnerable Version (Port 8001)
cd Authorization\ Bypass/
python3 app_vulnerable.py --port 8001

# Terminal 2 - Secure Version (Port 8002)
cd Authorization\ Bypass/
python3 app_secure.py --port 8002
```

### Step 2: Manual Header Spoofing Test (Vulnerable)

```bash
# ❌ This WORKS in vulnerable version (bad!)
curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "X-User: student1" \
  -H "X-Role: instructor" \
  -H "Content-Type: application/json" \
  -d '{"student_username": "target_student", "course_code": "CS101"}'
```

**Expected Result:** Success - Student data changed! ❌

---

### Step 3: Automatic Test Suite

```bash
# Test both versions
python3 Authorization\ Bypass/test_authorization_bypass.py --target both

# Or individually:
python3 Authorization\ Bypass/test_authorization_bypass.py --target vulnerable
python3 Authorization\ Bypass/test_authorization_bypass.py --target secure
```

**Expected Results:**
- Vulnerable: All attacks show ✓ (exploited)
- Secure: All attacks show ✓ (blocked)

---

## Manual Bearer Token Test (Secure)

### Step 1: Login and Get Token
```bash
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8002/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "student1", "password": "pass1"}')

echo $LOGIN_RESPONSE

# Extract token from response (depending on your shell)
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)
echo "Token: $TOKEN"
```

### Step 2: Try to Access Instructor Endpoint with Student Token
```bash
# ✅ This FAILS in secure version (good!)
curl -X POST http://localhost:8002/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_username": "target_student", "course_code": "CS101"}'
```

**Expected Result:** 403 Forbidden ✅

### Step 3: Login as Instructor and Try Again
```bash
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8002/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "instructor1", "password": "inst123"}')

INST_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)

# ✅ This WORKS for instructor (good!)
curl -X POST http://localhost:8002/api/instructor/admit-student \
  -H "Authorization: Bearer $INST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_username": "target_student", "course_code": "CS101"}'
```

**Expected Result:** Success - Properly authorized! ✅

---

## Code Files Reference

### Key Implementation Files

1. **auth_database.py**
   - `create_session_token()` - Generate token after login
   - `verify_session_token()` - Validate token on each request

2. **app_secure.py**
   - `/api/login` - Returns token
   - `extract_user_role()` - Validates Bearer token
   - All endpoints verify role from token

3. **test_authorization_bypass.py**
   - Tests both vulnerable and secure versions
   - Demonstrates role-based access control

---

## Demonstration Points for Students

### 1. Header Spoofing Attack (Vulnerable)
- Show how X-User/X-Role headers can be set by anyone
- No verification that user actually logged in
- Any client can claim any role

### 2. Bearer Token Solution (Secure)
- Show login returns a cryptographic token
- Token proves user identity (not just headers)
- Server validates token before checking role
- Role comes from token (user can't change it)

### 3. Data Isolation
- Student can view other students' data (vulnerable)
- Student blocked from viewing other students' data (secure)
- Authorization happens at application level

### 4. Role-Based Access Control (RBAC)
- Different endpoints require different roles
- Secure version enforces role matching
- 403 Forbidden on unauthorized access

---

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process on port 8001
lsof -ti:8001 | xargs kill -9
lsof -ti:8002 | xargs kill -9
```

### Token Format Wrong
The format must be exactly: `Authorization: Bearer <token>`
- ❌ Wrong: `Authorization: Token xyz`
- ❌ Wrong: `Bearer xyz` (missing header name)
- ✅ Correct: `Authorization: Bearer xyz`

### Login Returns Error
- Verify username/password in credentials list above
- Check database is initialized (seed_data.py run)
- Ensure auth_database.py can connect to database

### Tests Show Connection Error
- Verify both servers are running on correct ports
- Check firewall isn't blocking ports
- Verify no typos in localhost URLs

---

## Educational Goals

After this demonstration, students should understand:

1. ✅ Why headers alone are not sufficient for authentication
2. ✅ How tokens provide cryptographic proof of identity
3. ✅ The difference between authentication and authorization
4. ✅ How to implement role-based access control
5. ✅ Common authorization bypass vulnerabilities
