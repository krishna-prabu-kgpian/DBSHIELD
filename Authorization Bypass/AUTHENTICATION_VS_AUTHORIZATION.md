# Vulnerable vs Secure: Authentication vs Authorization

## 🎯 Key Concept

**Authentication** ≠ **Authorization**

### Authentication
- "Are you who you claim to be?"
- Verified by: username + password
- Proof: Bearer token
- **Both versions now REQUIRE this**

### Authorization
- "Are you ALLOWED to do this?"
- Verified by: Role check
- Proof: Role matches endpoint requirements
- **Only secure version ENFORCES this**

---

## Architecture Update

### BEFORE (Original Vulnerable Version)
```
❌ NO Authentication
❌ NO Authorization
→ ANYONE could call ANY endpoint
```

### AFTER (Updated Vulnerable Version)
```
✅ AUTHENTICATION: Bearer token required (login first)
❌ AUTHORIZATION: NO role checks on endpoints
→ ONLY logged-in users can call endpoints
→ BUT logged-in users can call ANY endpoint
```

### SECURE Version (Unchanged)
```
✅ AUTHENTICATION: Bearer token required (login first)
✅ AUTHORIZATION: Role checked for each endpoint
→ ONLY logged-in users can call endpoints
→ AND only users with matching role can proceed
```

---

## How It Works Now

### Step 1: Login (Both Versions)
```bash
curl -X POST http://localhost:8001/api/login \
  -d '{"username": "student1", "password": "pass1"}'

Response:
{
  "token": "VzHF_k5x...",
  "role": "student",
  "username": "student1"
}
```

### Step 2: Vulnerable Version Request
```bash
TOKEN="VzHF_k5x..."

# ✅ Student CAN access instructor endpoint
curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username": "target", "course_code": "CS101"}'

# ✅ Response: 200 SUCCESS
# Endpoint executes even though token says role="student"!
```

### Step 3: Secure Version Request (Same Request)
```bash
TOKEN="VzHF_k5x..."

# ❌ Student CANNOT access instructor endpoint
curl -X POST http://localhost:8002/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username": "target", "course_code": "CS101"}'

# ❌ Response: 403 FORBIDDEN
# Endpoint checks role in token, sees "student", blocks request
```

---

## Code Comparison

### Vulnerable Version: Validates Token, Ignores Role

```python
@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request):
    """
    ✅ Authenticate (check if logged in)
    ❌ Do NOT authorize (ignore role)
    """
    username, role = extract_user_role(request)  # ✅ Verify token exists
    
    # ❌ MISSING: if role != "instructor": raise 403
    # ❌ Just execute the action
    return admit_student_to_course_db(...)
```

### Secure Version: Validates Token AND Checks Role

```python
@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request):
    """
    ✅ Authenticate (check if logged in)
    ✅ Authorize (check role matches endpoint)
    """
    username, role = extract_user_role(request)  # ✅ Verify token exists
    
    # ✅ PRESENT: Check role
    if role != "instructor":
        raise HTTPException(403, "Instructors only!")
    
    # ✅ Safe to execute
    return admit_student_to_course_db(...)
```

---

## Test Scenarios

### Scenario 1: Unauthenticated Request
```bash
# No token at all
curl -X POST http://localhost:8001/api/student/view-grades \
  -d '{"student_username": "alice"}'
```

**Both versions:** ❌ 401 UNAUTHORIZED (not logged in)

---

### Scenario 2: Authenticated But Unauthorized (Vulnerable)
```bash
# Student with valid token tries instructor action
TOKEN=$(curl -s -X POST http://localhost:8001/api/login \
  -d '{"username": "student1", "password": "pass1"}' | jq -r '.token')

curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username": "target", "course_code": "CS101"}'
```

**Vulnerable version:** ✅ 200 SUCCESS (no role check!)  
**Secure version:** ❌ 403 FORBIDDEN (role check fails)

---

### Scenario 3: Authenticated AND Authorized (Both)
```bash
# Instructor with valid token tries instructor action
TOKEN=$(curl -s -X POST http://localhost:8001/api/login \
  -d '{"username": "instructor1", "password": "inst123"}' | jq -r '.token')

curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"student_username": "target", "course_code": "CS101"}'
```

**Both versions:** ✅ 200 SUCCESS (role check passes)

---

## Key Difference

| Request Type | Vulnerable | Secure |
|---|---|---|
| **No auth** (no token) | ❌ 401 | ❌ 401 |
| **Student token** → Student endpoint | ✅ 200 | ✅ 200 |
| **Student token** → Instructor endpoint | ✅ 200 | ❌ 403 |
| **Instructor token** → Instructor endpoint | ✅ 200 | ✅ 200 |
| **Admin token** → Admin endpoint | ✅ 200 | ✅ 200 |

---

## Why This Matters

### Common Real-World Mistake
```
"We added login! Now it's secure!"
```

❌ **Wrong.** Login only proves identity, not permissions.

### The Reality
```
✅ Authentication: "I am John Smith" (password proves this)
❌ Authorization: "John Smith is allowed to change grades" (not checked!)

Result: Anyone can log in and do anything!
```

### What's Needed
```
✅ Authentication + Authorization

1. Verify identity (login with username/password)
2. Verify permissions (check role for each action)
3. Verify ownership (only access your own data)
```

---

## Teaching Point for Professors

**"Notice:**
1. **Original vulnerable version:** No checks at all
2. **Updated vulnerable version:** Authentication ✅ but Authorization ❌
3. **Secure version:** Both Authentication ✅ and Authorization ✅

This shows that simply adding login is NOT enough!  
You must also check permissions on EVERY endpoint."

---

## Test Output Interpretation

### Vulnerable Version Test
```
✓ Student access to other_student's grades: PASS (bad!)
✓ Student admits another student: PASS (bad!)
✓ Student assigns grades: PASS (bad!)
✓ Student executes admin action: PASS (bad!)
```

Interpretation: "All attacks succeeded because we don't check roles!"

### Secure Version Test
```
✓ Student blocked from other_student's grades: PASS (good!)
✓ Student blocked from instructor endpoint: PASS (good!)
✓ Student blocked from admin endpoint: PASS (good!)
✓ Instructor allowed on instructor endpoint: PASS (good!)
✓ Admin allowed on admin endpoint: PASS (good!)
```

Interpretation: "Attacks blocked because we check roles!"

---

## Files Changed

### 1. Authorization Bypass/app_vulnerable.py
- ✅ Added `extract_user_role()` function (validates token)
- ✅ Updated login to return Bearer token
- ✅ ALL endpoints now call `extract_user_role(request)` at start
- ❌ NO role checking in any endpoint (vulnerability remains)

### 2. Authorization Bypass/test_authorization_bypass.py
- ✅ Updated `make_request()` to always use Bearer tokens
- ✅ Both test_vulnerable_version() and test_secure_version() use tokens
- ✅ Vulnerable version shows auth ✅ authz ❌ 
- ✅ Secure version shows auth ✅ authz ✅

---

## Deployment

```bash
# Terminal 1: Vulnerable Version
python3 app_vulnerable.py --port 8001

# Terminal 2: Secure Version
python3 app_secure.py --port 8002

# Terminal 3: Run Tests
python3 test_authorization_bypass.py --target both
```

---

## Key Learning Outcomes

After this demonstration, students should understand:

1. ✅ **Authentication** = Proving who you are
2. ✅ **Authorization** = Proving you have permission
3. ✅ Both are needed for security
4. ✅ Login alone is NOT enough
5. ✅ Every endpoint must verify role
6. ✅ This is a common real-world mistake

---

## Common Student Questions

**Q: "If the vulnerable version requires a token, isn't it secure?"**  
A: "No! The token proves identity, but the endpoint doesn't check if that identity has permission. It's like showing your ID at a restricted area - the guard checks it's really you, but forgets to check if you're allowed in."

**Q: "Why check the role if we already have a token?"**  
A: "Because different users have different permissions. A student token lets you login, but it doesn't let you assign grades. We need to check the role to know what you're allowed to do."

**Q: "Couldn't we just check role once at login?"**  
A: "No. Different endpoints have different role requirements. A student can view grades but not assign them. An instructor can assign grades but not delete users. We must check role for each endpoint."

---

**Version:** 2.1 (Authentication Required, Authorization Optional)  
**Status:** ✅ Ready for Demonstration
