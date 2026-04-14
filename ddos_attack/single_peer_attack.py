"""
Single-peer login flood simulator.

Unlike ddos_simulator.py, this script does NOT send an X-Forwarded-For header.
It is meant to exercise the direct-client path in the middleware, where the
backend rate-limits based on the real TCP peer IP.
"""

import asyncio
import aiohttp
import os
import random
import sys
import time


TARGET_URL = os.getenv("TARGET_URL", "http://127.0.0.1:8000/api/login")

# Tuned to demonstrate the "one peer, no XFF" behavior.
BATCH_SIZE = int(os.getenv("SINGLE_PEER_BATCH_SIZE", "50"))
WORKERS = int(os.getenv("SINGLE_PEER_WORKERS", "4"))
PAUSE_BETWEEN_BATCHES_SECONDS = float(os.getenv("SINGLE_PEER_BATCH_PAUSE", "0.02"))
REQUEST_TIMEOUT_SECONDS = float(os.getenv("SINGLE_PEER_REQUEST_TIMEOUT", "2.0"))


async def send_batch(session: aiohttp.ClientSession, worker_id: int):
    while True:
        tasks = []
        for _ in range(BATCH_SIZE):
            payload = {
                "username": f"single_peer_flood_{random.randint(1, 999999)}",
                "password": f"pwd_flood_{random.randint(1, 999999)}",
            }
            tasks.append(session.post(TARGET_URL, json=payload))

        try:
            start = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            latency = time.time() - start

            status_codes = {}
            for response in responses:
                if isinstance(response, Exception):
                    status_codes["Error"] = status_codes.get("Error", 0) + 1
                else:
                    status_codes[response.status] = status_codes.get(response.status, 0) + 1
                    response.release()

            print(
                f"[Worker-{worker_id}] Sent {BATCH_SIZE} direct requests in "
                f"{latency:.2f}s | Statuses: {status_codes}"
            )
            if PAUSE_BETWEEN_BATCHES_SECONDS > 0:
                await asyncio.sleep(PAUSE_BETWEEN_BATCHES_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"[Worker-{worker_id}] Failed to send batch: {exc}")


async def main():
    print("=" * 60)
    print("WARNING: INITIATING SINGLE-PEER LOGIN FLOOD")
    print(f"Targeting: {TARGET_URL}")
    print(
        f"Workers: {WORKERS} | Batch size: {BATCH_SIZE} | "
        f"Pause: {PAUSE_BETWEEN_BATCHES_SECONDS}s"
    )
    print("Mode: direct client traffic (no X-Forwarded-For header)")
    print("=" * 60)
    print("Press Ctrl+C to stop the flood.\n")

    await asyncio.sleep(2)

    connection_limit = max(50, WORKERS * BATCH_SIZE)
    connector = aiohttp.TCPConnector(limit=connection_limit, limit_per_host=connection_limit)
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    session = aiohttp.ClientSession(connector=connector, timeout=timeout)

    workers = [asyncio.create_task(send_batch(session, i)) for i in range(WORKERS)]

    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        print("\n[FLOOD ABORTED] Shutting down simulation...")
    except KeyboardInterrupt:
        print("\n[FLOOD ABORTED] Shutting down simulation...")
    finally:
        for worker in workers:
            worker.cancel()
        await session.close()
        print("Simulation terminated.")


if __name__ == "__main__":
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
