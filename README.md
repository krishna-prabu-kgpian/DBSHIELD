# DBSHIELD Project Report

## Quick Start

### 1. Load the backend

Install the backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The backend will run at `http://localhost:8000`.

### 2. Open the frontend

Install the frontend dependencies:

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
- `student1 / pass1`
- `student2 / pass2`

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
