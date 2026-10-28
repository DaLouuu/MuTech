"""Asynchronous Job Manager for Long File Transcription.

Implements Checklist Phase 1.4:
- 1.4.2 In-memory job store with TTL cleanup
- Asynchronous polling endpoints support
"""

import time
import uuid
import threading
from typing import Any, Optional, Literal

JobStatus = Literal["pending", "processing", "completed", "failed"]

JOB_TTL_SECONDS = 30 * 60  # 30 minutes
MAX_ACTIVE_JOBS = 20        # Maximum concurrent pending/processing jobs
MAX_STORED_JOBS = 200       # Maximum total jobs in memory before forced eviction


class JobLimitExceededError(Exception):
    """Raised when job queue capacity is saturated."""
    pass


class Job:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status: JobStatus = "pending"
        self.progress: float = 0.0  # 0 to 100%
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None
        self.result: Optional[dict[str, Any]] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "job_id": self.job_id,
            "status": self.status,
            "progress": round(self.progress, 1),
            "created_at": self.created_at,
        }
        if self.completed_at:
            data["completed_at"] = self.completed_at
        if self.error:
            data["error"] = self.error
        if self.result:
            data["result"] = self.result
        return data


class JobManager:
    def __init__(self, ttl_seconds: int = JOB_TTL_SECONDS):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds

    def active_job_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status in ("pending", "processing"))

    def create_job(self) -> Job:
        with self._lock:
            self._cleanup_expired()
            
            # Check active queue limits to prevent memory exhaustion DoS
            active_count = sum(1 for j in self._jobs.values() if j.status in ("pending", "processing"))
            if active_count >= MAX_ACTIVE_JOBS:
                raise JobLimitExceededError(
                    f"Job queue is saturated ({active_count} active jobs). Please retry shortly."
                )

            # Evict oldest completed/failed jobs if stored limit is exceeded
            if len(self._jobs) >= MAX_STORED_JOBS:
                finished = [
                    (j.created_at, jid) for jid, j in self._jobs.items()
                    if j.status in ("completed", "failed")
                ]
                finished.sort()
                for _, jid in finished[:len(self._jobs) - MAX_STORED_JOBS + 10]:
                    del self._jobs[jid]

            job_id = str(uuid.uuid4())
            job = Job(job_id)
            self._jobs[job_id] = job
            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(self, job_id: str, progress: float, status: JobStatus = "processing"):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = max(0.0, min(100.0, progress))
                job.status = status

    def complete_job(self, job_id: str, result: dict[str, Any]):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "completed"
                job.progress = 100.0
                job.completed_at = time.time()
                job.result = result

    def fail_job(self, job_id: str, error_message: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "failed"
                job.completed_at = time.time()
                job.error = error_message

    def cleanup_expired(self) -> int:
        """Prune expired jobs exceeding TTL. Returns number of removed jobs."""
        with self._lock:
            return self._cleanup_expired()

    def _cleanup_expired(self) -> int:
        now = time.time()
        expired_ids = [
            jid for jid, job in self._jobs.items()
            if (now - job.created_at) > self._ttl_seconds
        ]
        for jid in expired_ids:
            del self._jobs[jid]
        return len(expired_ids)


# Global singleton instance
job_manager = JobManager()
