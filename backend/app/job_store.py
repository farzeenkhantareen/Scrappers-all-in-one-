"""
In-memory job store and manager — no Redis required.
Jobs are stored in process memory and run as asyncio tasks.
"""

import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    """Thread-safe in-memory job store backed by a dict."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._results: dict[str, Any] = {}
        self._logs: dict[str, list] = {}
        self._ws_callbacks: dict[str, list[Callable]] = {}

    # ─── Job CRUD ─────────────────────────────────────────────────────────────
    def create(self, job_type: str, url: str, config: dict) -> dict:
        job_id = str(uuid.uuid4())
        job = {
            "id": job_id,
            "type": job_type,
            "status": "queued",
            "target_url": url,
            "config": config,
            "progress_pct": 0.0,
            "scraped_pages": 0,
            "total_pages": 0,
            "items_found": 0,
            "current_url": "",
            "elapsed_seconds": 0.0,
            "created_at": _now(),
            "started_at": None,
            "completed_at": None,
            "error_message": None,
        }
        self._jobs[job_id] = job
        self._logs[job_id] = []
        return job

    def get(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def list_all(self, status: str = None, type_: str = None) -> list[dict]:
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j["status"] == status]
        if type_:
            jobs = [j for j in jobs if j["type"] == type_]
        return sorted(jobs, key=lambda x: x["created_at"], reverse=True)

    def update(self, job_id: str, **kwargs):
        if job_id in self._jobs:
            self._jobs[job_id].update(kwargs)
            self._broadcast(job_id, {**self._jobs[job_id], "type": "status"})

    def set_status(self, job_id: str, status: str, **extra):
        self.update(job_id, status=status, **extra)

    def set_result(self, job_id: str, result: Any):
        self._results[job_id] = result

    def get_result(self, job_id: str) -> Any:
        return self._results.get(job_id)

    def delete(self, job_id: str):
        self._jobs.pop(job_id, None)
        self._results.pop(job_id, None)
        self._logs.pop(job_id, None)
        self._ws_callbacks.pop(job_id, None)

    # ─── Progress ─────────────────────────────────────────────────────────────
    def update_progress(self, job_id: str, progress: dict):
        if job_id in self._jobs:
            self._jobs[job_id].update({
                "progress_pct": progress.get("progress_pct", 0),
                "scraped_pages": progress.get("scraped_pages", 0),
                "total_pages": progress.get("total_pages", 0),
                "items_found": progress.get("items_found", 0),
                "current_url": progress.get("current_url", ""),
                "elapsed_seconds": progress.get("elapsed_seconds", 0),
            })
            self._broadcast(job_id, {"type": "progress", **progress})

    # ─── Logs ─────────────────────────────────────────────────────────────────
    def add_log(self, job_id: str, level: str, message: str, context: dict = None):
        entry = {
            "job_id": job_id,
            "level": level,
            "message": message,
            "context": context or {},
            "timestamp": _now(),
        }
        logs = self._logs.setdefault(job_id, [])
        logs.insert(0, entry)
        if len(logs) > 500:
            logs.pop()
        self._broadcast(job_id, {"type": "log", **entry})

    def get_logs(self, job_id: str, level: str = None, limit: int = 200) -> list:
        logs = self._logs.get(job_id, [])
        if level:
            logs = [l for l in logs if l.get("level") == level]
        return logs[:limit]

    def get_all_logs(self, level: str = None, limit: int = 200) -> list:
        all_logs = []
        for logs in self._logs.values():
            all_logs.extend(logs)
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        if level:
            all_logs = [l for l in all_logs if l.get("level") == level]
        return all_logs[:limit]

    # ─── Stats ────────────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        jobs = list(self._jobs.values())
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for job in jobs:
            s = job["status"]
            t = job["type"]
            by_status[s] = by_status.get(s, 0) + 1
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_jobs": len(jobs),
            "active_jobs": by_status.get("running", 0),
            "completed_jobs": by_status.get("completed", 0),
            "failed_jobs": by_status.get("failed", 0),
            "queued_jobs": by_status.get("queued", 0),
            "total_pages_scraped": sum(j.get("scraped_pages", 0) for j in jobs),
            "total_businesses": 0,
            "total_reviews": 0,
            "total_social_profiles": sum(
                1 for j in jobs if j["type"] in ("instagram", "linkedin", "facebook")
                and j["status"] == "completed"
            ),
            "jobs_by_type": by_type,
            "jobs_by_status": by_status,
            "recent_jobs": sorted(jobs, key=lambda x: x["created_at"], reverse=True)[:10],
        }

    # ─── WebSocket callbacks ───────────────────────────────────────────────────
    def register_ws(self, job_id: str, callback: Callable):
        self._ws_callbacks.setdefault(job_id, []).append(callback)

    def unregister_ws(self, job_id: str, callback: Callable):
        cbs = self._ws_callbacks.get(job_id, [])
        if callback in cbs:
            cbs.remove(callback)

    def _broadcast(self, job_id: str, data: dict):
        for cb in self._ws_callbacks.get(job_id, []):
            try:
                asyncio.create_task(cb(data))
            except Exception:
                pass


# Global singleton
job_store = JobStore()
