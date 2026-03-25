"""
Worker pool for database query execution.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional

from config import NUM_WORKERS, WORKER_TIMEOUT_SECONDS


class WorkerPool:
    """
    Pool of async workers for database query execution.

    Features:
    - Priority queue (metro cities get priority)
    - Multiple workers for parallelism
    - Graceful shutdown
    - Timeout handling
    """

    def __init__(self, num_workers: int = NUM_WORKERS):
        self.num_workers = num_workers
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.workers: List[asyncio.Task] = []
        self.results: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self.processed_count = 0

    async def start(self):
        """Start the worker pool."""
        self._running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker(i))
            self.workers.append(task)
        print(f"[WORKERS] Started {self.num_workers} workers")

    async def stop(self):
        """Gracefully stop all workers."""
        self._running = False

        # Send shutdown signals
        for _ in self.workers:
            await self.queue.put((float('inf'), 0, None, None, None))

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        print("[WORKERS] All workers stopped")

    async def _worker(self, worker_id: int):
        """Worker coroutine that processes queue items."""
        while self._running:
            try:
                # Get item from queue
                priority, timestamp, request_id, city, query = await self.queue.get()

                # Check for shutdown signal
                if request_id is None:
                    self.queue.task_done()
                    break

                try:
                    # Execute the query
                    result = await self._execute_query(query)

                    # Store result
                    async with self._lock:
                        if request_id in self.results:
                            self.results[request_id].set_result(result)
                        self.processed_count += 1

                    print(f"[WORKER-{worker_id}] Executed | Priority: {priority} | City: {city}")

                except Exception as e:
                    async with self._lock:
                        if request_id in self.results:
                            self.results[request_id].set_exception(e)
                    print(f"[WORKER-{worker_id}] Error: {e}")

                finally:
                    self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WORKER-{worker_id}] Unexpected error: {e}")

    async def submit(
        self,
        query: str,
        priority: int,
        city: str
    ) -> Any:
        """
        Submit query and wait for result.

        Args:
            query: SQL query to execute
            priority: Priority level (lower = higher priority)
            city: City for logging

        Returns:
            Query result
        """
        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()

        async with self._lock:
            self.results[request_id] = future

        # Put in queue with priority and timestamp for FIFO within same priority
        await self.queue.put((priority, time.time(), request_id, city, query))

        try:
            result = await asyncio.wait_for(future, timeout=WORKER_TIMEOUT_SECONDS)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Query execution timed out after {WORKER_TIMEOUT_SECONDS}s")
        finally:
            async with self._lock:
                self.results.pop(request_id, None)

    async def _execute_query(self, query: str) -> List[Dict]:
        """
        Execute query against database.

        This is a MOCK implementation. Replace with actual database execution.
        """
        # Simulate DB execution time
        await asyncio.sleep(0.05)

        # Return mock data based on query pattern
        # In production, this would execute against a real database
        mock_result = self._generate_mock_result(query)
        return mock_result

    def _generate_mock_result(self, query: str) -> List[Dict]:
        """Generate mock results for testing."""
        # Extract student_id if present
        import re
        student_match = re.search(r'student_id\s*=\s*(\d+)', query, re.IGNORECASE)
        student_id = int(student_match.group(1)) if student_match else 12345

        # Generate mock grades
        results = [
            {"student_id": student_id, "grade": 95, "subject": "Math", "attendance": 92},
            {"student_id": student_id, "grade": 88, "subject": "Science", "attendance": 88},
            {"student_id": student_id, "grade": 72, "subject": "History", "attendance": 95},
            {"student_id": student_id, "grade": 65, "subject": "Art", "attendance": 80},
        ]

        return results

    async def get_stats(self) -> dict:
        """Get worker pool statistics."""
        return {
            "num_workers": self.num_workers,
            "active_workers": len([w for w in self.workers if not w.done()]),
            "queue_size": self.queue.qsize(),
            "pending_results": len(self.results),
            "processed_count": self.processed_count,
        }
