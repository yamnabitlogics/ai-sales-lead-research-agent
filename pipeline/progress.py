"""In-memory job progress tracking for the web UI."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


AGENT_STEPS = [
    {"id": "research", "label": "Research Agent", "detail": "Gathering company intelligence"},
    {"id": "technology", "label": "Technology Agent", "detail": "Detecting tech stack"},
    {"id": "decision_makers", "label": "Decision Maker Agent", "detail": "Finding key contacts"},
    {"id": "opportunities", "label": "Opportunity Agent", "detail": "Identifying sales angles"},
    {"id": "email", "label": "Email Agent", "detail": "Crafting outreach email"},
    {"id": "report", "label": "Report Agent", "detail": "Compiling final report"},
    {"id": "finalize", "label": "Finalizing", "detail": "Saving report and PDF"},
]


@dataclass
class JobState:
    job_id: str
    status: str = "running"
    current_step: int = 0
    message: str = "Starting research pipeline..."
    error: str | None = None
    result: dict[str, Any] | None = None
    company: str = ""
    website: str = ""


class ProgressTracker:
    def __init__(self) -> None:
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def create_job(self, company: str, website: str) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = JobState(job_id=job_id, company=company, website=website)
        return job_id

    def advance(self, job_id: str, message: str | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status != "running":
                return
            if job.current_step < len(AGENT_STEPS) - 1:
                job.current_step += 1
            if message:
                job.message = message
            else:
                step = AGENT_STEPS[min(job.current_step, len(AGENT_STEPS) - 1)]
                job.message = f"{step['label']} — {step['detail']}"

    def set_message(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.message = message

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "complete"
            job.current_step = len(AGENT_STEPS) - 1
            job.message = "Research complete!"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "error"
            job.error = error
            job.message = error

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            total = len(AGENT_STEPS)
            pct = int(((job.current_step + (1 if job.status == "complete" else 0)) / total) * 100)
            if job.status == "complete":
                pct = 100
            steps = []
            for i, step in enumerate(AGENT_STEPS):
                state = "pending"
                if job.status == "complete" or i < job.current_step:
                    state = "done"
                elif i == job.current_step and job.status == "running":
                    state = "active"
                elif job.status == "error" and i == job.current_step:
                    state = "error"
                steps.append({**step, "state": state})
            return {
                "job_id": job.job_id,
                "status": job.status,
                "current_step": job.current_step,
                "total_steps": total,
                "percent": min(pct, 100),
                "message": job.message,
                "error": job.error,
                "steps": steps,
                "company": job.company,
                "website": job.website,
            }

    def get_result(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status == "complete":
                return job.result
            return None


progress_tracker = ProgressTracker()
