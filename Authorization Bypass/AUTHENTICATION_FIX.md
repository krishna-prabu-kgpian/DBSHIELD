# Bearer Token Authentication Fix
## Authorization Bypass → Authorization Enforcement

---

## Problem: Header Spoofing Vulnerability

### ❌ VULNERABLE VERSION (Original)
The vulnerable version uses only header-based authentication:
```bash
curl -X POST http://localhost:8001/api/instructor/admit-student \
  -H "X-User: student1" \
  -H "X-Role: instructor" \
  -H "Content-Type: application/json" \
  -d '{"student_username": "target", "course_code": "CS101"}'
```

**Problem:** An attacker can simply SET headers to any role. No verification of actual identity.
- ❌ No proof user actually logged in
- ❌ No cryptographic validation
- ❌ Any user can claim any role

---

## Solution: Bearer Token Authentication

### ✅ SECURE VERSION (Fixed)

#### 1️⃣ **LOGIN PHASE** - User proves identity
```bash
curl -X POST http://localhost:8002/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "student1", "password": "pass1"}'
```

**Response:**
```json
{
  "message": "Login successful.",
  "token": "your_secure_token_here",
  "username": "student1",
  "role": "student",
  "name": "John Doe"
}
```

#### 2️⃣ **AUTHENTICATED REQUEST PHASE** - User proves they have valid token
```bash
STUDENT_TOKEN="your_secure_token_here"

curl -X POST http://localhost:8002/api/instructor/admit-student \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_username": "target", "course_code": "CS101"}'
```

**Result:** ✅ **403 FORBIDDEN** (Properly blocked!)
```json
{
  "detail": "Access denied. This endpoint requires role: instructor. You have role: student"
}
```

---

## Technical Implementation

### **Token Generation** (`auth_database.py`)
```python
_token_store = {}  # In-memory token storage

def create_session_token(username: str, role: str) -> str:
    """Generate a secure, unique token after successful login."""
    token = secrets.token_urlsafe(32)
    _token_store[token] = {"username": username, "role": role}
    return token
```

### **Token Validation** (`auth_database.py`)
```python
def verify_session_token(token: str) -> dict:
    """Verify token is valid and return user data."""
    return _token_store.get(token)  # Returns None or user_data
```

### **Token Extraction** (`app_secure.py`)
```python
def extract_user_role(request: Request) -> tuple[str, str]:
    """Extract and validate Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing/invalid Authorization header")
    
    token = auth_header.replace("Bearer ", "").strip()
    user_data = verify_session_token(token)  # Must exist
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user_data["username"], user_data["role"]
```

### **Role Enforcement** (All Secured Endpoints)
```python
@app.post("/api/instructor/admit-student")
def instructor_admit_student(payload: AdmitStudentPayload, request: Request):
    username, role = extract_user_role(request)  # Get role from token
    
    # Verify role matches endpoint requirements
    if role != "instructor":
        raise HTTPException(status_code=403, detail="Instructors only")
    
    return admit_student_to_course_db(...)
```

---

## Security Guarantees

| Security Aspect | Vulnerable | Secure |
|---|---|---|
| **Authentication** | Headers only (no proof) | Bearer token (cryptographic proof) |
| **Header Spoofing** | ❌ Possible | ✅ Blocked (token required) |
| **Role Verification** | ❌ No database check | ✅ Token tied to user identity |
| **Replay Attacks** | ❌ Headers can be replayed | ⚠️ Token can be replayed (see mitigation below) |
| **Data Ownership** | ❌ No isolation | ✅ Username from token verified |

---

## Demonstration Flow

### Test Vulnerable Version
```bash
python3 test_authorization_bypass.py --target vulnerable
```
Expected output:
```
✗ Student blocked from viewing other_student's grades: PASS (should PASS = vulnerability confirmed!)
✗ Student denied from instructor endpoint: PASS
✗ Student denied from admin endpoint: PASS
```
All attacks show **PASS** = Security is broken ❌

### Test Secure Version
```bash
python3 test_authorization_bypass.py --target secure
```
Expected output:
```
✓ Student blocked from viewing other_student's grades: PASS (vulnerability fixed!)
✓ Student denied from instructor endpoint: PASS
✓ Student denied from admin endpoint: PASS
✓ Instructor allowed to admit student: PASS
✓ Admin allowed to execute admin action: PASS
```
All attacks show **PASS** = Security is enforced ✅

---

## Security Improvements Checklist

✅ **Authentication**
- [x] Users must provide valid username/password
- [x] Credentials verified against database
- [x] No credentials transmitted in requests after login

✅ **Authorization**
- [x] Token proves user identity
- [x] Role extracted from token, not user-controlled headers
- [x] Each endpoint verifies role matches requirements
- [x] 403 Forbidden returned for unauthorized access

✅ **Data Isolation**
- [x] Students can only view their own grades (username from token)
- [x] Instructors can only manage courses (role from token)
- [x] Admins isolated to admin endpoints (role from token)

---

## Future Enhancements

For production deployment, consider:

1. **Token Expiration**
   ```python
   _token_store[token] = {
       "username": username,
       "role": role,
       "expires_at": time.time() + 3600  # 1 hour
   }
   ```

2. **Persistent Token Storage**
   - Replace in-memory `_token_store` with database
   - Survive server restarts
   - Enable token revocation

3. **HTTPS/TLS**
   - Encrypt tokens in transit
   - Prevent man-in-the-middle attacks

4. **JWT Tokens**
   ```python
   import jwt
   token = jwt.encode(
       {"username": username, "role": role},
       secret_key,
       algorithm="HS256"
   )
   ```

5. **Secure Session Management**
   - Token refresh mechanism
   - Logout endpoint to revoke tokens
   - Rate limiting on login attempts

---

## File Changes Summary

| File | Change | Impact |
|---|---|---|
| `auth_database.py` | Added `create_session_token()`, `verify_session_token()` | Token generation & validation |
| `app_secure.py` | Updated `login()` to return token | Returns token after authentication |
| `app_secure.py` | Updated `extract_user_role()` for Bearer token | Validates token instead of headers |
| `app_secure.py` | All endpoints verify role from token | Enforces authorization |
| `test_authorization_bypass.py` | Updated to obtain token before tests | Tests real authentication flow |

---

## Running the Complete Demo

```bash
# Terminal 1: Start vulnerable version
python3 Authorization\ Bypass/app_vulnerable.py --port 8001

# Terminal 2: Start secure version  
python3 Authorization\ Bypass/app_secure.py --port 8002

# Terminal 3: Run tests
python3 Authorization\ Bypass/test_authorization_bypass.py --target both
```

Expected result:
- **Vulnerable:** All attacks succeed (headers accepted)
- **Secure:** All attacks blocked (tokens required)

---

## Key Takeaway

**The Fix:** Replace user-controlled headers with server-authenticated tokens.

Before: `X-User: attacker` → Accepted ❌  
After: `Authorization: Bearer <token>` → Validated against database ✅
