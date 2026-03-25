"""
Enhanced DDoS Shield with Intelligent Caching and Geolocation

Features:
- Full result caching (exact query match)
- Mid-AST caching (superset query matching with in-memory filtering)
- IP-based rate limiting with progressive penalties
- AST-based rate limiting
- Request validation
- Worker pool for parallel execution
- IP geolocation with spoofing detection
- Multi-tier priority system
"""

import asyncio
import time
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config import (
    RATE_LIMIT_THRESHOLD,
    RATE_LIMIT_WINDOW,
    METRO_CITIES,
    TIER2_CITIES,
    PRIORITY_METRO_VERIFIED,
    PRIORITY_METRO_CLAIMED,
    PRIORITY_TIER2_CITY,
    PRIORITY_STANDARD,
    PRIORITY_SUSPICIOUS,
)
from rate_limiter import IPRateLimiter, BoundedQueryHistory, RequestValidator
from cache import (
    FullResultCache,
    IntermediateResultCache,
    QuerySupersetDetector,
    InMemoryFilter,
    compute_full_cache_key,
    normalize_and_hash,
)
from workers import WorkerPool
from geolocation import geolocation_service, GeolocationResult, GeolocationSource


# --- Global Instances ---
ip_limiter = IPRateLimiter()
request_validator = RequestValidator()
full_cache = FullResultCache()
intermediate_cache = IntermediateResultCache()
query_history = BoundedQueryHistory()
worker_pool = WorkerPool()
query_parser = QuerySupersetDetector()
memory_filter = InMemoryFilter()


# --- Priority Computation ---
def _compute_priority(geo_result: GeolocationResult) -> int:
    city = geo_result.city.lower() if geo_result.city else ""

    if geo_result.is_spoofing:
        return PRIORITY_SUSPICIOUS

    if geo_result.source in (
        GeolocationSource.IP_VERIFIED,
        GeolocationSource.HEADER_VERIFIED,
        GeolocationSource.IP_ONLY
    ):
        if city in METRO_CITIES:
            return PRIORITY_METRO_VERIFIED
        if city in TIER2_CITIES:
            return PRIORITY_TIER2_CITY
        return PRIORITY_STANDARD

    if geo_result.source in (
        GeolocationSource.HEADER_ONLY,
        GeolocationSource.LOCAL_IP
    ):
        if city in METRO_CITIES:
            return PRIORITY_METRO_CLAIMED
        if city in TIER2_CITIES:
            return PRIORITY_TIER2_CITY
        return PRIORITY_STANDARD

    return PRIORITY_STANDARD


# --- Background Tasks ---
async def periodic_cleanup():
    while True:
        await asyncio.sleep(60)
        await full_cache.cleanup_expired()
        await intermediate_cache.cleanup_expired()


# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    await worker_pool.start()
    cleanup_task = asyncio.create_task(periodic_cleanup())
    print("[SHIELD] DDoS Shield initialized with intelligent caching and geolocation")

    yield

    cleanup_task.cancel()
    await worker_pool.stop()
    await geolocation_service.close()
    print("[SHIELD] Shutdown complete")


app = FastAPI(
    title="DDoS Shield API",
    description="SQL query execution with DDoS protection and intelligent caching",
    lifespan=lifespan
)


# --- Main Endpoint ---
@app.post("/execute-query")
async def execute_query(
    request: Request,
    x_user_city: Optional[str] = Header(default="unknown")
):
    start_time = time.time()

    # --- LAYER 1: IP Validation ---
    # Allow simulator to spoof IPs via X-Forwarded-For header to test distributed attacks properly
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")

    is_allowed, block_reason = await ip_limiter.check_ip(client_ip)
    if not is_allowed:
        print(f"[BLOCKED] IP {client_ip}: {block_reason}")
        raise HTTPException(status_code=429, detail=block_reason)

    # --- LAYER 2: Request Validation ---
    try:
        body = await request.body()
        body_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    raw_query = body_json.get("query", "")

    is_valid, error = request_validator.validate(raw_query, len(body))
    if not is_valid:
        print(f"[REJECTED] Invalid request from {client_ip}: {error}")
        raise HTTPException(status_code=400, detail=error)

    # --- LAYER 3: Full Cache Lookup ---
    full_cache_key = compute_full_cache_key(raw_query)

    cached_result = await full_cache.get(full_cache_key)
    if cached_result is not None:
        latency = time.time() - start_time
        print(f"[CACHE HIT] Full cache | IP: {client_ip} | Latency: {latency:.4f}s")
        return {
            "status": "cached",
            "cache_type": "full",
            "result": cached_result,
            "latency_ms": round(latency * 1000, 2)
        }

    # --- LAYER 4: Mid-AST Cache Lookup ---
    parsed_query = query_parser.parse_query(raw_query)

    if parsed_query:
        reusable = await intermediate_cache.find_reusable_cache(parsed_query)
        if reusable:
            base_result, additional_conditions = reusable
            filtered_result = memory_filter.filter_results(base_result, additional_conditions)

            await full_cache.set(full_cache_key, filtered_result)

            latency = time.time() - start_time
            print(f"[CACHE HIT] Mid-AST | IP: {client_ip} | Filtered {len(base_result)} -> {len(filtered_result)} | Latency: {latency:.4f}s")
            return {
                "status": "cached",
                "cache_type": "intermediate_filtered",
                "result": filtered_result,
                "filtered_from": len(base_result),
                "conditions_applied": len(additional_conditions),
                "latency_ms": round(latency * 1000, 2)
            }

    # --- LAYER 5: AST Rate Limiting ---
    ast_hash = normalize_and_hash(raw_query)

    is_limited = await query_history.record_and_check(
        ast_hash,
        threshold=RATE_LIMIT_THRESHOLD,
        window=RATE_LIMIT_WINDOW
    )
    if is_limited:
        print(f"[BLOCKED] AST rate limit | IP: {client_ip} | Hash: {ast_hash[:16]}...")
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for this query structure"
        )

    # --- LAYER 6: Geolocation & Priority Assignment ---
    geo_result = await geolocation_service.get_location(client_ip, x_user_city)
    city_normalized = geo_result.city.lower() if geo_result.city else "unknown"
    priority = _compute_priority(geo_result)

    if geo_result.is_spoofing:
        print(f"[SPOOFING] IP {client_ip} claimed '{geo_result.claimed_city}', actual: '{geo_result.city}'")

    try:
        result = await worker_pool.submit(raw_query, priority, city_normalized)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

    # --- LAYER 7: Populate Caches ---
    await full_cache.set(full_cache_key, result)

    if parsed_query:
        await intermediate_cache.set(parsed_query, result)

    latency = time.time() - start_time
    print(f"[EXECUTED] IP: {client_ip} | City: {city_normalized} | Priority: {priority} | Latency: {latency:.4f}s")

    return {
        "status": "executed",
        "result": result,
        "priority": priority,
        "city": city_normalized,
        "geo_source": geo_result.source.value,
        "is_spoofing": geo_result.is_spoofing,
        "latency_ms": round(latency * 1000, 2)
    }


# --- Health & Stats Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/stats")
async def get_stats():
    full_cache_stats = await full_cache.get_stats()
    intermediate_cache_stats = await intermediate_cache.get_stats()
    query_history_stats = await query_history.get_stats()
    ip_limiter_stats = await ip_limiter.get_stats()
    worker_stats = await worker_pool.get_stats()
    geolocation_stats = await geolocation_service.get_stats()

    return {
        "full_cache": full_cache_stats,
        "intermediate_cache": intermediate_cache_stats,
        "query_history": query_history_stats,
        "ip_rate_limiter": ip_limiter_stats,
        "workers": worker_stats,
        "geolocation": geolocation_stats,
    }


# --- Blacklist Management ---

@app.post("/blacklist/{ip}")
async def add_to_blacklist(ip: str):
    await ip_limiter.add_to_blacklist(ip)
    return {"status": "success", "message": f"IP {ip} added to blacklist"}


@app.delete("/blacklist/{ip}")
async def remove_from_blacklist(ip: str):
    await ip_limiter.remove_from_blacklist(ip)
    return {"status": "success", "message": f"IP {ip} removed from blacklist"}


# --- Error Handlers ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)