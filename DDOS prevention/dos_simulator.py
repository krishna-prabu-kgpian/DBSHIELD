"""
Comprehensive Test Suite for DDoS Shield

Tests all functionality:
1. Priority System (geolocation, spoofing detection)
2. City Header Edge Cases
3. Request Validation (blocked keywords, size limits)
4. Rate Limiting (IP and AST based)
5. Caching (full and mid-AST)
6. Worker Pool
7. Edge Cases
8. Full DDoS Simulation
"""

import asyncio
import aiohttp
import time
import random
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
TARGET_URL = f"{BASE_URL}/execute-query"
STATS_URL = f"{BASE_URL}/stats"
HEALTH_URL = f"{BASE_URL}/health"


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str
    duration_ms: float = 0


class TestRunner:
    """Test runner with result tracking."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None

    async def setup(self):
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession()

    async def teardown(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()

    def record(self, name: str, passed: bool, message: str, duration_ms: float = 0):
        """Record a test result."""
        result = TestResult(name, passed, message, duration_ms)
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {message}")

    async def post(self, query: str, headers: Dict[str, str] = None) -> tuple:
        """Send POST request and return (status, json_data, latency_ms)."""
        start = time.time()
        try:
            hdrs = {"Content-Type": "application/json"}
            if headers:
                hdrs.update(headers)
            async with self.session.post(TARGET_URL, json={"query": query}, headers=hdrs) as resp:
                data = await resp.json()
                latency = (time.time() - start) * 1000
                return resp.status, data, latency
        except Exception as e:
            return 0, {"error": str(e)}, (time.time() - start) * 1000

    async def post_raw(self, body: Any, headers: Dict[str, str] = None) -> tuple:
        """Send POST with raw body."""
        start = time.time()
        try:
            hdrs = {"Content-Type": "application/json"}
            if headers:
                hdrs.update(headers)
            async with self.session.post(TARGET_URL, data=body, headers=hdrs) as resp:
                try:
                    data = await resp.json()
                except:
                    data = {"raw": await resp.text()}
                latency = (time.time() - start) * 1000
                return resp.status, data, latency
        except Exception as e:
            return 0, {"error": str(e)}, (time.time() - start) * 1000

    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total: {total} | Passed: {passed} | Failed: {failed}")

        if failed > 0:
            print("\nFailed Tests:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")

        print("=" * 60)


# =============================================================================
# TEST CATEGORIES
# =============================================================================

async def test_priority_system(runner: TestRunner):
    """Test the priority assignment system."""
    print("\n" + "=" * 60)
    print("PRIORITY SYSTEM TESTS")
    print("=" * 60)

    # Test 1: Metro city in header should work (local IP trusts header)
    status, data, latency = await runner.post(
        "SELECT * FROM grades WHERE id = 1",
        {"X-User-City": "Mumbai"}
    )
    if status == 200:
        priority = data.get("priority")
        # Local IPs trust header, so should get PRIORITY_METRO_CLAIMED (2)
        passed = priority in (1, 2)  # Either verified or claimed
        runner.record(
            "test_metro_city_header",
            passed,
            f"Priority={priority} for Mumbai (expected 1 or 2)"
        )
    else:
        runner.record("test_metro_city_header", False, f"Request failed: {status}")

    # Test 2: Tier 2 city
    status, data, latency = await runner.post(
        "SELECT * FROM grades WHERE id = 2",
        {"X-User-City": "Ahmedabad"}
    )
    if status == 200:
        priority = data.get("priority")
        passed = priority == 3  # PRIORITY_TIER2_CITY
        runner.record(
            "test_tier2_city",
            passed,
            f"Priority={priority} for Ahmedabad (expected 3)"
        )
    else:
        runner.record("test_tier2_city", False, f"Request failed: {status}")

    # Test 3: Standard city
    status, data, latency = await runner.post(
        "SELECT * FROM grades WHERE id = 3",
        {"X-User-City": "SmallTown"}
    )
    if status == 200:
        priority = data.get("priority")
        passed = priority == 4  # PRIORITY_STANDARD
        runner.record(
            "test_standard_city",
            passed,
            f"Priority={priority} for SmallTown (expected 4)"
        )
    else:
        runner.record("test_standard_city", False, f"Request failed: {status}")

    # Test 4: Missing header should default
    status, data, latency = await runner.post(
        "SELECT * FROM grades WHERE id = 4",
        {}  # No X-User-City header
    )
    if status == 200:
        city = data.get("city", "")
        passed = city == "unknown" or city == ""
        runner.record(
            "test_missing_city_header",
            passed,
            f"City='{city}' without header (expected 'unknown')"
        )
    else:
        runner.record("test_missing_city_header", False, f"Request failed: {status}")

    # Test 5: Response includes geo_source field
    status, data, latency = await runner.post(
        "SELECT * FROM grades WHERE id = 5",
        {"X-User-City": "Delhi"}
    )
    if status == 200:
        has_geo_source = "geo_source" in data
        runner.record(
            "test_geo_source_in_response",
            has_geo_source,
            f"geo_source field present: {has_geo_source}"
        )
    else:
        runner.record("test_geo_source_in_response", False, f"Request failed: {status}")


async def test_city_header_edge_cases(runner: TestRunner):
    """Test various city header formats and edge cases."""
    print("\n" + "=" * 60)
    print("CITY HEADER EDGE CASES")
    print("=" * 60)

    # Test case insensitivity
    test_cases = [
        ("MUMBAI", "uppercase"),
        ("mumbai", "lowercase"),
        ("Mumbai", "mixed case"),
        ("  mumbai  ", "with whitespace"),
    ]

    for city_value, description in test_cases:
        status, data, latency = await runner.post(
            f"SELECT * FROM test WHERE x = '{random.randint(1,1000)}'",
            {"X-User-City": city_value}
        )
        if status == 200:
            result_city = data.get("city", "").lower().strip()
            passed = result_city == "mumbai"
            runner.record(
                f"test_city_{description.replace(' ', '_')}",
                passed,
                f"'{city_value}' -> '{result_city}'"
            )
        else:
            runner.record(f"test_city_{description}", False, f"Status: {status}")

    # Test empty header
    status, data, latency = await runner.post(
        "SELECT * FROM test WHERE x = 1",
        {"X-User-City": ""}
    )
    runner.record(
        "test_empty_city_header",
        status == 200,
        f"Empty header handled, status={status}"
    )


async def test_request_validation(runner: TestRunner):
    """Test request validation (blocked keywords, size limits)."""
    print("\n" + "=" * 60)
    print("REQUEST VALIDATION TESTS")
    print("=" * 60)

    # Test blocked SQL keywords
    blocked_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "EXEC", "GRANT"]

    for keyword in blocked_keywords:
        query = f"{keyword} TABLE users"
        status, data, latency = await runner.post(query)
        passed = status == 400 and "Blocked" in str(data.get("detail", ""))
        runner.record(
            f"test_blocked_{keyword.lower()}",
            passed,
            f"'{keyword}' blocked: status={status}"
        )

    # Test that keyword in value is allowed
    status, data, latency = await runner.post(
        "SELECT * FROM items WHERE name = 'Water Drop'"
    )
    runner.record(
        "test_keyword_in_value_allowed",
        status == 200,
        f"'DROP' in value allowed: status={status}"
    )

    # Test empty query
    status, data, latency = await runner.post("")
    passed = status == 400
    runner.record(
        "test_empty_query",
        passed,
        f"Empty query rejected: status={status}"
    )

    # Test whitespace-only query
    status, data, latency = await runner.post("   ")
    passed = status == 400
    runner.record(
        "test_whitespace_query",
        passed,
        f"Whitespace query rejected: status={status}"
    )

    # Test invalid JSON
    status, data, latency = await runner.post_raw("not json at all")
    passed = status == 400
    runner.record(
        "test_invalid_json",
        passed,
        f"Invalid JSON rejected: status={status}"
    )

    # Test query length limit (10KB)
    long_query = "SELECT * FROM test WHERE data = '" + "x" * 11000 + "'"
    status, data, latency = await runner.post(long_query)
    passed = status == 400
    runner.record(
        "test_query_over_10kb",
        passed,
        f"Query >10KB rejected: status={status}"
    )


async def test_rate_limiting(runner: TestRunner):
    """Test IP and AST rate limiting."""
    print("\n" + "=" * 60)
    print("RATE LIMITING TESTS")
    print("=" * 60)

    # Test IP rate limiting (10/second)
    # Send 15 requests rapidly
    print("  Testing IP rate limiting (sending 15 rapid requests)...")
    results = []
    for i in range(15):
        status, data, latency = await runner.post(
            f"SELECT * FROM test WHERE unique_id = {random.randint(100000, 999999)}"
        )
        results.append(status)
        await asyncio.sleep(0.05)  # 50ms between requests

    blocked = sum(1 for s in results if s == 429)
    runner.record(
        "test_ip_rate_limiting",
        blocked > 0,
        f"Blocked {blocked}/15 requests (expected >0 if limit is 10/sec)"
    )

    # Wait for rate limit to reset
    print("  Waiting 2s for rate limit reset...")
    await asyncio.sleep(2)

    # Test AST rate limiting (50 identical structures in 10 seconds)
    print("  Testing AST rate limiting (sending 60 same-structure queries)...")
    results = []
    for i in range(60):
        # Same structure, different literal value
        status, data, latency = await runner.post(
            f"SELECT * FROM ast_test WHERE value = {i + 5000}"
        )
        results.append(status)

    ast_blocked = sum(1 for s in results if s == 429)
    runner.record(
        "test_ast_rate_limiting",
        ast_blocked > 0,
        f"AST blocked {ast_blocked}/60 requests (threshold is 50)"
    )


async def test_blacklist(runner: TestRunner):
    """Test blacklist management endpoints."""
    print("\n" + "=" * 60)
    print("BLACKLIST TESTS")
    print("=" * 60)

    test_ip = "192.168.100.100"

    # Add to blacklist
    try:
        async with runner.session.post(f"{BASE_URL}/blacklist/{test_ip}") as resp:
            status = resp.status
            runner.record(
                "test_blacklist_add",
                status == 200,
                f"Add IP to blacklist: status={status}"
            )
    except Exception as e:
        runner.record("test_blacklist_add", False, str(e))

    # Remove from blacklist
    try:
        async with runner.session.delete(f"{BASE_URL}/blacklist/{test_ip}") as resp:
            status = resp.status
            runner.record(
                "test_blacklist_remove",
                status == 200,
                f"Remove IP from blacklist: status={status}"
            )
    except Exception as e:
        runner.record("test_blacklist_remove", False, str(e))


async def test_caching(runner: TestRunner):
    """Test full cache and mid-AST cache."""
    print("\n" + "=" * 60)
    print("CACHING TESTS")
    print("=" * 60)

    # Wait for any rate limits to reset
    await asyncio.sleep(2)

    # Test 1: Full cache hit
    unique_id = random.randint(100000, 999999)
    query = f"SELECT * FROM grades WHERE student_id = {unique_id}"

    # First request - should execute
    status1, data1, latency1 = await runner.post(query, {"X-User-City": "Pune"})

    # Second request - should hit cache
    status2, data2, latency2 = await runner.post(query, {"X-User-City": "Pune"})

    if status1 == 200 and status2 == 200:
        cache_type = data2.get("cache_type", "")
        passed = cache_type == "full"
        runner.record(
            "test_full_cache_hit",
            passed,
            f"Second request cache_type='{cache_type}' (expected 'full'), latency: {latency1:.1f}ms -> {latency2:.1f}ms"
        )
    else:
        runner.record("test_full_cache_hit", False, f"Status: {status1}, {status2}")

    # Test 2: Mid-AST cache (superset matching)
    base_id = random.randint(200000, 299999)

    # Base query
    base_query = f"SELECT * FROM grades WHERE student_id = {base_id}"
    status1, data1, latency1 = await runner.post(base_query, {"X-User-City": "Delhi"})

    # Superset query (adds condition)
    superset_query = f"SELECT * FROM grades WHERE student_id = {base_id} AND grade > 80"
    status2, data2, latency2 = await runner.post(superset_query, {"X-User-City": "Delhi"})

    if status1 == 200 and status2 == 200:
        cache_type = data2.get("cache_type", "")
        passed = cache_type == "intermediate_filtered"
        filtered_from = data2.get("filtered_from", 0)
        result_count = len(data2.get("result", []))
        runner.record(
            "test_midast_cache_hit",
            passed,
            f"Superset cache_type='{cache_type}', filtered {filtered_from} -> {result_count}"
        )
    else:
        runner.record("test_midast_cache_hit", False, f"Status: {status1}, {status2}")

    # Test 3: Cache latency improvement
    if status2 == 200 and latency2 < latency1:
        runner.record(
            "test_cache_latency_improvement",
            True,
            f"Cached: {latency2:.1f}ms vs Executed: {latency1:.1f}ms"
        )
    else:
        runner.record(
            "test_cache_latency_improvement",
            False,
            f"No improvement: {latency2:.1f}ms vs {latency1:.1f}ms"
        )


async def test_workers(runner: TestRunner):
    """Test worker pool functionality."""
    print("\n" + "=" * 60)
    print("WORKER POOL TESTS")
    print("=" * 60)

    # Test parallel execution - send 4 requests (matching worker count)
    print("  Testing parallel execution (4 concurrent requests)...")

    async def send_request(i):
        start = time.time()
        status, data, latency = await runner.post(
            f"SELECT * FROM parallel_test WHERE id = {random.randint(300000, 399999) + i}"
        )
        return time.time() - start, status

    tasks = [send_request(i) for i in range(4)]
    results = await asyncio.gather(*tasks)

    all_success = all(r[1] == 200 for r in results)
    max_time = max(r[0] for r in results)

    runner.record(
        "test_parallel_execution",
        all_success,
        f"4 concurrent requests completed, max time: {max_time:.2f}s"
    )


async def test_edge_cases(runner: TestRunner):
    """Test edge cases and special scenarios."""
    print("\n" + "=" * 60)
    print("EDGE CASE TESTS")
    print("=" * 60)

    # Test Unicode in query
    status, data, latency = await runner.post(
        "SELECT * FROM users WHERE name = 'Test User'"
    )
    runner.record(
        "test_unicode_in_query",
        status == 200,
        f"Unicode in query: status={status}"
    )

    # Test quotes in query
    status, data, latency = await runner.post(
        "SELECT * FROM test WHERE name = 'John''s Data'"
    )
    runner.record(
        "test_quotes_in_query",
        status in (200, 400),  # Either works or is rejected safely
        f"Quotes in query handled: status={status}"
    )

    # Test health endpoint
    try:
        async with runner.session.get(HEALTH_URL) as resp:
            data = await resp.json()
            passed = resp.status == 200 and data.get("status") == "healthy"
            runner.record(
                "test_health_endpoint",
                passed,
                f"Health check: {data.get('status')}"
            )
    except Exception as e:
        runner.record("test_health_endpoint", False, str(e))

    # Test stats endpoint
    try:
        async with runner.session.get(STATS_URL) as resp:
            data = await resp.json()
            has_all_stats = all(k in data for k in ["full_cache", "workers", "geolocation"])
            runner.record(
                "test_stats_endpoint",
                resp.status == 200 and has_all_stats,
                f"Stats endpoint has all sections: {has_all_stats}"
            )
    except Exception as e:
        runner.record("test_stats_endpoint", False, str(e))


async def run_ddos_simulation(runner: TestRunner):
    """Full DDoS simulation."""
    print("\n" + "=" * 60)
    print("DDOS SIMULATION (200 requests)")
    print("=" * 60)

    total_requests = 200
    results = []
    start_time = time.time()

    tasks = []
    for i in range(total_requests):
        # Mix of patterns
        patterns = [
            ("SELECT * FROM grades WHERE student_id = 12345", "Mumbai"),
            ("SELECT * FROM grades WHERE student_id = 12345 AND grade > 80", "Delhi"),
            (f"SELECT * FROM users WHERE id = {random.randint(1, 10000)}", "Unknown"),
        ]
        query, city = random.choice(patterns)
        tasks.append(runner.post(query, {"X-User-City": city}))

    responses = await asyncio.gather(*tasks)

    for status, data, latency in responses:
        results.append({
            "status": status,
            "cache_type": data.get("cache_type", "executed" if status == 200 else "blocked"),
            "latency": latency
        })

    total_time = time.time() - start_time

    # Analyze results
    status_counts = Counter(r["status"] for r in results)
    cache_counts = Counter(r["cache_type"] for r in results)

    print(f"\n  Total time: {total_time:.2f}s")
    print(f"  Throughput: {total_requests / total_time:.1f} req/s")
    print(f"  Status codes: {dict(status_counts)}")
    print(f"  Cache breakdown: {dict(cache_counts)}")

    success_rate = status_counts.get(200, 0) / total_requests * 100
    runner.record(
        "test_ddos_simulation",
        success_rate > 50,  # At least 50% should succeed (some rate limited)
        f"Success rate: {success_rate:.1f}%, throughput: {total_requests / total_time:.1f} req/s"
    )


async def main():
    """Run all tests."""
    print("=" * 60)
    print("DDoS Shield Comprehensive Test Suite")
    print("=" * 60)
    print("\nEnsure server is running: uvicorn shield:app --reload\n")

    runner = TestRunner()
    await runner.setup()

    try:
        # Check server is running
        try:
            async with runner.session.get(HEALTH_URL) as resp:
                if resp.status != 200:
                    print("ERROR: Server not responding. Start it first!")
                    return
        except:
            print("ERROR: Cannot connect to server at", BASE_URL)
            print("Start the server with: uvicorn shield:app --reload")
            return

        print("Server is running. Starting tests...\n")

        # Run all test categories
        await test_priority_system(runner)
        await test_city_header_edge_cases(runner)
        await test_request_validation(runner)
        await test_caching(runner)
        await test_blacklist(runner)
        await test_workers(runner)
        await test_edge_cases(runner)

        # Wait before rate limiting tests
        print("\nWaiting 3s before rate limiting tests...")
        await asyncio.sleep(3)

        await test_rate_limiting(runner)

        # Wait before DDoS simulation
        print("\nWaiting 3s before DDoS simulation...")
        await asyncio.sleep(3)

        await run_ddos_simulation(runner)

        # Print summary
        runner.print_summary()

    finally:
        await runner.teardown()


if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
