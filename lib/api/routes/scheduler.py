"""GET /v1/scheduler/jobs — list running APScheduler jobs."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/scheduler", tags=["scheduler"])

_scheduler = None


def set_scheduler(scheduler) -> None:
    """Called from main.py after scheduler.start()."""
    global _scheduler
    _scheduler = scheduler


@router.get("/jobs")
def list_jobs() -> list[dict]:
    """Return all scheduled jobs. Returns [] if no scheduler is running."""
    if _scheduler is None:
        return []
    return [
        {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "func_name": getattr(job.func, "__name__", str(job.func)),
        }
        for job in _scheduler.get_jobs()
    ]
