# DBSHIELD - Database Systems Handling for Injection, Exploitation, Leakage, and DoS

---

## Overview

DBSHIELD is an advanced, high-performance middleware layer designed to protect backend database systems from Layer 7 Denial-of-Service (DoS) attacks while ensuring Quality of Service (QoS) for prioritized geographic regions.

Built for a mock Student ERP portal, this shield intercepts traffic between the application backend and the database, normalizing and filtering requests before they can exhaust database connection pools or CPU resources.

---

## Defense-in-Depth Architecture

The middleware implements a multi-tiered defense strategy based on three core principles: **Prevention, Containment, and Recovery**.

### Layer 1: Distributed IP Rate Limiting

To mitigate basic volumetric spam, the shield tracks request frequencies and active connection counts per IP address. It supports `X-Forwarded-For` headers to identify true client IPs behind proxies and applies a progressive penalty system:

- Temporary bans for first-time offenders
- Escalating penalties for repeat violations
- Permanent blacklisting capability for persistent attackers

### Layer 2: AST-Based Semantic Rate Limiting

Standard string-matching Web Application Firewalls (WAFs) fail when distributed botnets randomize query parameters across thousands of IPs. DBSHIELD addresses this vulnerability using `sqlparse` to generate an Abstract Syntax Tree (AST) of incoming SQL queries.

**How it works:**

1. Strips variable literals from queries (e.g., `WHERE id = 123` becomes `WHERE id = ?`)
2. Hashes the underlying query structure
3. Tracks frequency of identical structures regardless of source IP
4. Blocks requests when structural frequency exceeds threshold with `429 Too Many Requests`

This approach detects coordinated attacks even when attackers randomize both parameters and IP addresses.

### Layer 3: Full Result Caching

Exact query matching with in-memory result storage:

- Eliminates redundant database queries
- Reduces latency by up to 87.8% for repeated queries
- Automatic cache expiration and cleanup

### Layer 4: Mid-AST Superset Caching

To optimize read-heavy ERP workloads, the shield detects when an incoming query is a strict superset of a previously cached query.

**Example:**
- Query A: `SELECT * FROM students WHERE major = 'CS'` (cached)
- Query B: `SELECT * FROM students WHERE major = 'CS' AND grade > 80` (superset)

Instead of executing Query B against the database, the shield:

1. Retrieves Query A's results from cache
2. Applies additional filters in-memory using pre-compiled regex
3. Returns filtered results

This dramatically reduces database latency and CPU load while mitigating ReDoS (Regex Denial of Service) vulnerabilities.

### Layer 5: Geographic Priority Queuing

During volumetric attacks, database connections become scarce. DBSHIELD implements an asynchronous priority queue based on the `X-User-City` header, cross-referenced with GeoIP spoofing detection.

**Priority Tiers:**

- Priority 1: Verified metro city locations (highest)
- Priority 2: Claimed metro city locations
- Priority 3: Tier-2 cities
- Priority 4: Standard locations
- Priority 5: Suspected spoofed locations (lowest)

This ensures low-latency access for critical demographics even under heavy load.

---

## Project Structure

```
Dos/
├── shield.py              # Core FastAPI middleware application
├── config.py              # Configuration constants (rate limits, cache TTLs, priority tiers)
├── rate_limiter.py        # O(1) IP and AST rate limiting, request validation
├── cache.py               # Exact-match and Mid-AST superset caching
├── geolocation.py         # IP location service with spoofing detection
├── workers.py             # Asynchronous worker pool with priority queues
├── dos_simulator.py       # Layer 7 botnet simulation and test suite
├── requirements.txt       # Python dependencies
└── Performance_Report.md  # Detailed performance analysis
```

---

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment support

### Step 1: Create Virtual Environment

**macOS/Linux:**
```bash
cd /path/to/Dos
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
cd \path\to\Dos
python -m venv venv
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- **fastapi**: Web framework for the API
- **uvicorn**: ASGI server for FastAPI
- **aiohttp**: Asynchronous HTTP client for testing
- **sqlparse**: SQL parsing library for AST generation

---

## Running the Demonstration

The demonstration requires two terminal windows. Ensure your virtual environment is activated in both.

### Terminal 1: Start the Shield

Start the middleware server on port 8000:

```bash
python shield.py
```

Or alternatively:

```bash
uvicorn shield:app --reload --port 8000
```

**Expected output:**
```
[WORKERS] Started 4 workers
[SHIELD] DDoS Shield initialized with intelligent caching and geolocation
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2: Run the Test Suite

Execute the comprehensive test suite and Layer 7 DoS simulation:

```bash
python dos_simulator.py
```

This script uses `aiohttp` to send hundreds of structurally identical (but parameter-randomized) queries while dynamically rotating spoofed IP addresses to simulate a distributed botnet attack.

---

## Understanding the Results

### Phase 1: Initial Requests

The first batch of requests will pass through all defense layers and execute successfully. The cache begins warming up during this phase.

### Phase 2: Containment

Once the structural rate-limit threshold is breached, the AST parser identifies the attack signature, completely bypassing the IP rotation tactics. Subsequent malicious requests are instantly blocked with a `429 Too Many Requests` status code.

### Phase 3: Analysis

After the simulation completes, the test suite outputs:

- Total throughput (requests/second)
- Request distribution (blocked, cached, executed)
- Average latency for successful queries
- Cache hit rates (full and mid-AST)
- Pass/fail status for all test categories

This demonstrates that the database remained highly responsive despite attack volume.

---

## Performance Summary

For detailed performance metrics and analysis, see [Performance_Report.md](Performance_Report.md).

**Key Highlights:**

| Metric | Value | Impact |
|--------|-------|--------|
| Cache Hit Latency Reduction | 87.8% | 55.1ms to 6.7ms |
| Database Load Reduction | 33% | Via cache layer |
| Attack Mitigation Rate | 6.5% blocked + 33% cached | Total 39.5% |
| System Throughput Under Attack | 118.7 req/sec | Stable performance |
| SQL Injection Prevention | 100% | All malicious keywords blocked |

---

## API Endpoints

### Query Execution

**POST** `/execute-query`

Executes a SQL query with full protection stack.

**Headers:**
- `X-User-City` (optional): User's city for priority assignment
- `X-Forwarded-For` (optional): Client IP for proxy support

**Request Body:**
```json
{
  "query": "SELECT * FROM students WHERE id = 123"
}
```

**Response:**
```json
{
  "status": "executed",
  "result": [...],
  "priority": 2,
  "city": "mumbai",
  "geo_source": "header_only",
  "is_spoofing": false,
  "latency_ms": 45.67
}
```

### Health Check

**GET** `/health`

Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1234567890.123
}
```

### System Statistics

**GET** `/stats`

Returns comprehensive system statistics including cache performance, rate limiting metrics, worker pool status, and geolocation data.

### Blacklist Management

**POST** `/blacklist/{ip}`

Adds an IP address to the permanent blacklist.

**DELETE** `/blacklist/{ip}`

Removes an IP address from the blacklist.

---

## Testing Categories

The test suite validates seven categories of functionality:

1. **Priority System Tests**: Verifies geolocation-based priority assignment
2. **City Header Edge Cases**: Tests various header formats and encoding
3. **Request Validation**: Confirms SQL injection prevention
4. **Caching Tests**: Validates full and mid-AST cache functionality
5. **Rate Limiting Tests**: Confirms IP and AST-based rate limiting
6. **Worker Pool Tests**: Verifies concurrent request handling
7. **Edge Cases**: Tests Unicode, special characters, and error handling

---

## Troubleshooting

### Error: ModuleNotFoundError

**Cause:** Virtual environment not activated or dependencies not installed.

**Solution:**
```bash
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### Error: Address already in use

**Cause:** Another process is using port 8000.

**Solution:**

Find and kill the process:
```bash
lsof -ti:8000 | xargs kill -9
```

Or change the port in `shield.py` (line 320) and `dos_simulator.py` (line 15).

### Error: Cannot connect to server

**Cause:** Server is not running in Terminal 1.

**Solution:** Ensure `python shield.py` is running and showing "Uvicorn running on..." before executing tests.

### Corrupted Virtual Environment

**Cause:** Timeout errors or import failures.

**Solution:**
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration

All configuration parameters are centralized in `config.py`:

- **Rate Limits**: IP and AST frequency thresholds
- **Cache Settings**: TTL values and cleanup intervals
- **Geographic Priorities**: City classifications and priority levels
- **Worker Pool**: Number of concurrent workers and queue sizes

Modify these values to adjust system behavior for your deployment environment.

---

## Security Considerations

### SQL Injection Prevention

The system blocks all dangerous SQL keywords at the validation layer:
- DROP, DELETE, TRUNCATE, ALTER
- EXEC, GRANT, REVOKE
- Additional keywords configurable in `config.py`

Context-aware filtering prevents false positives (e.g., "Water Drop" in data values).

### Query Size Limits

Maximum query size: 10KB (configurable)

Prevents resource exhaustion from oversized queries.

### Cache Security

- Cache keys use cryptographic hashing (SHA-256)
- Automatic expiration prevents stale data
- Memory-bounded to prevent exhaustion attacks

---

## System Requirements

**Minimum:**
- Python 3.8+
- 512MB RAM
- 2 CPU cores

**Recommended:**
- Python 3.10+
- 2GB RAM
- 4+ CPU cores

---

## Future Enhancements

Potential improvements for production deployment:

1. **Persistent Storage**: Redis integration for distributed caching
2. **Monitoring**: Prometheus metrics and Grafana dashboards
3. **Advanced Geolocation**: Integration with MaxMind GeoIP2 database
4. **Query Analysis**: Machine learning-based anomaly detection
5. **Load Balancing**: Multi-instance deployment with shared state

---

## License and Acknowledgments

This project was developed as a demonstration of Layer 7 DoS mitigation techniques for database-backed applications. It illustrates the importance of defense-in-depth architecture and intelligent request handling in high-traffic scenarios.

**Technologies Used:**
- FastAPI (Web framework)
- SQLParse (SQL parsing and AST generation)
- Uvicorn (ASGI server)
- Python asyncio (Asynchronous execution)


---
