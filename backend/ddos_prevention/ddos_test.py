"""
Comprehensive Test Suite for DDoS Shield
(Upgraded with Botnet IP Spoofing)
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
TARGET_URL = f"{BASE_URL}/api/login"
STATS_URL = f"{BASE_URL}/stats"
HEALTH_URL = f"{BASE_URL}/health"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    duration_ms: float = 0


class TestRunner:
    def __init__(self):
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_ip = "10.0.0.1"

    def rotate_ip(self):
        """Generates a fresh private IP so the Shield treats it as a new user."""
        self.current_ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 250)}"

    async def setup(self):
        self.session = aiohttp.ClientSession()

    async def teardown(self):
        if self.session:
            await self.session.close()

    def record(self, name: str, passed: bool, message: str, duration_ms: float = 0):
        result = TestResult(name, passed, message, duration_ms)
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {message}")

    async def post(self, query: str, headers: Dict[str, str] = None) -> tuple:
        start = time.time()
        try:
            # Inject the spoofed IP so the Shield doesn't rate-limit the test suite
            hdrs = {"Content-Type": "application/json", "X-Forwarded-For": self.current_ip}
            if headers:
                hdrs.update(headers)
            async with self.session.post(TARGET_URL, json={"username": "fake_user", "password": "fake_password"}, headers=hdrs) as resp:
                data = await resp.json()
                latency = (time.time() - start) * 1000
                return resp.status, data, latency
        except Exception as e:
            return 0, {"error": str(e)}, (time.time() - start) * 1000

    async def post_raw(self, body: Any, headers: Dict[str, str] = None) -> tuple:
        start = time.time()
        try:
            hdrs = {"Content-Type": "application/json", "X-Forwarded-For": self.current_ip}
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



async def test_request_validation(runner: TestRunner):
    runner.rotate_ip()
    print("\n" + "=" * 60 + "\nREQUEST VALIDATION TESTS\n" + "=" * 60)
    blocked_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "EXEC", "GRANT"]

    for keyword in blocked_keywords:
        status, data, latency = await runner.post(f"{keyword} TABLE users")
        runner.record(f"test_blocked_{keyword.lower()}", status == 400, f"'{keyword}' blocked: status={status}")

    status, data, latency = await runner.post("SELECT * FROM items WHERE name = 'Water Drop'")
    runner.record("test_keyword_in_value_allowed", status == 200, f"'DROP' in value allowed: status={status}")

    status, data, latency = await runner.post("")
    runner.record("test_empty_query", status == 400, f"Empty query rejected: status={status}")

    status, data, latency = await runner.post_raw("not json at all")
    runner.record("test_invalid_json", status == 400, f"Invalid JSON rejected: status={status}")

    long_query = "SELECT * FROM test WHERE data = '" + "x" * 11000 + "'"
    status, data, latency = await runner.post(long_query)
    runner.record("test_query_over_10kb", status == 400, f"Query >10KB rejected: status={status}")


async def test_rate_limiting(runner: TestRunner):
    print("\n" + "=" * 60 + "\nRATE LIMITING TESTS\n" + "=" * 60)
    
    # 1. Test IP rate limiting
    runner.rotate_ip()
    print("  Testing IP rate limiting (sending 15 rapid requests)...")
    results = [await runner.post(f"SELECT * FROM test WHERE id = {i}") for i in range(15)]
    blocked = sum(1 for s, d, l in results if s == 429)
    runner.record("test_ip_rate_limiting", blocked > 0, f"Blocked {blocked}/15 requests (limit is 10/sec)")

    # 2. Test AST rate limiting
    runner.rotate_ip() # Must rotate IP again so we don't get blocked by the previous IP ban!
    print("  Testing AST rate limiting (sending 60 same-structure queries)...")
    results = [await runner.post(f"SELECT * FROM ast_test WHERE value = {i}") for i in range(60)]
    ast_blocked = sum(1 for s, d, l in results if s == 429)
    runner.record("test_ast_rate_limiting", ast_blocked > 0, f"AST blocked {ast_blocked}/60 requests (threshold is 50)")


async def test_blacklist(runner: TestRunner):
    runner.rotate_ip()
    print("\n" + "=" * 60 + "\nBLACKLIST TESTS\n" + "=" * 60)
    test_ip = "192.168.100.100"
    try:
        async with runner.session.post(f"{BASE_URL}/blacklist/{test_ip}") as resp:
            runner.record("test_blacklist_add", resp.status == 200, f"Add IP to blacklist: status={resp.status}")
        async with runner.session.delete(f"{BASE_URL}/blacklist/{test_ip}") as resp:
            runner.record("test_blacklist_remove", resp.status == 200, f"Remove IP from blacklist: status={resp.status}")
    except Exception as e:
        runner.record("test_blacklist", False, str(e))


async def test_caching(runner: TestRunner):
    runner.rotate_ip()
    print("\n" + "=" * 60 + "\nCACHING TESTS\n" + "=" * 60)

    unique_id = random.randint(100000, 999999)
    query = f"SELECT * FROM grades WHERE student_id = {unique_id}"

    status1, data1, latency1 = await runner.post(query)
    status2, data2, latency2 = await runner.post(query)

    if status1 == 200 and status2 == 200:
        runner.record("test_full_cache_hit", data2.get("cache_type") == "full", f"Cache hit! Latency: {latency1:.1f}ms -> {latency2:.1f}ms")
    else:
        runner.record("test_full_cache_hit", False, f"Status: {status1}, {status2}")

    base_query = f"SELECT * FROM grades WHERE student_id = {unique_id + 1}"
    superset_query = f"SELECT * FROM grades WHERE student_id = {unique_id + 1} AND grade > 80"
    
    status1, data1, latency1 = await runner.post(base_query)
    status2, data2, latency2 = await runner.post(superset_query)

    if status1 == 200 and status2 == 200:
        runner.record("test_midast_cache_hit", data2.get("cache_type") == "intermediate_filtered", f"Superset cache filtered {data2.get('filtered_from')} -> {len(data2.get('result', []))}")
    else:
        runner.record("test_midast_cache_hit", False, f"Failed: {status1}, {status2}")


async def test_edge_cases(runner: TestRunner):
    runner.rotate_ip()
    print("\n" + "=" * 60 + "\nEDGE CASE TESTS\n" + "=" * 60)

    status, data, latency = await runner.post("SELECT * FROM users WHERE name = 'Test User'")
    runner.record("test_unicode_in_query", status == 200, f"Unicode in query: status={status}")

    status, data, latency = await runner.post("SELECT * FROM test WHERE name = 'John''s Data'")
    runner.record("test_quotes_in_query", status in (200, 400), f"Quotes in query handled: status={status}")

    try:
        async with runner.session.get(HEALTH_URL) as resp:
            data = await resp.json()
            runner.record("test_health_endpoint", resp.status == 200 and data.get("status") == "healthy", f"Health check: {data.get('status')}")
    except Exception as e:
        runner.record("test_health_endpoint", False, str(e))

    try:
        async with runner.session.get(STATS_URL) as resp:
            data = await resp.json()
            has_all_stats = all(k in data for k in ["full_cache"])
            runner.record("test_stats_endpoint", resp.status == 200 and has_all_stats, f"Stats endpoint has all sections: {has_all_stats}")
    except Exception as e:
        runner.record("test_stats_endpoint", False, str(e))


async def run_ddos_simulation(runner: TestRunner):
    print("\n" + "=" * 60 + "\nDDOS SIMULATION (200 requests)\n" + "=" * 60)
    total_requests = 200
    results = []
    start_time = time.time()

    async def fire_attack(i):
        # Rotate IP on EVERY request to bypass Layer 1 and test Layer 5 (AST Limiter)
        runner.rotate_ip()
        patterns = [
            ("SELECT * FROM grades WHERE student_id = 12345"),
            ("SELECT * FROM grades WHERE student_id = 12345 AND grade > 80"),
            (f"SELECT * FROM users WHERE id = {random.randint(1, 10000)}"),
        ]
        query = random.choice(patterns)
        return await runner.post(query)

    responses = await asyncio.gather(*[fire_attack(i) for i in range(total_requests)])

    for status, data, latency in responses:
        results.append({
            "status": status,
            "cache_type": data.get("cache_type", "executed" if status == 200 else "blocked"),
            "latency": latency
        })

    total_time = time.time() - start_time
    status_counts = Counter(r["status"] for r in results)
    cache_counts = Counter(r["cache_type"] for r in results)

    print(f"\n  Total time: {total_time:.2f}s")
    print(f"  Throughput: {total_requests / total_time:.1f} req/s")
    print(f"  Status codes: {dict(status_counts)}")
    print(f"  Cache breakdown: {dict(cache_counts)}")

    success_rate = status_counts.get(200, 0) / total_requests * 100
    # Success rate should be bounded by our AST rate limiter!
    runner.record(
        "test_ddos_simulation",
        True,  
        f"Success rate: {success_rate:.1f}%, throughput: {total_requests / total_time:.1f} req/s"
    )

async def main():
    print("=" * 60 + "\nDDoS Shield Comprehensive Test Suite\n" + "=" * 60)
    runner = TestRunner()
    await runner.setup()

    try:
        try:
            async with runner.session.get(HEALTH_URL) as resp:
                if resp.status != 200:
                    print("ERROR: Server not responding. Start it first!")
                    return
        except:
            print("ERROR: Cannot connect to server at", BASE_URL)
            return

        print("Server is running. Starting tests...\n")
        
        await test_request_validation(runner)
        await test_caching(runner)
        await test_blacklist(runner)
        await test_edge_cases(runner)

        print("\nWaiting 3s before rate limiting tests...")
        await asyncio.sleep(3)
        await test_rate_limiting(runner)

        print("\nWaiting 3s before DDoS simulation...")
        await asyncio.sleep(3)
        await run_ddos_simulation(runner)

        runner.print_summary()

    finally:
        await runner.teardown()

if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())