from __future__ import annotations

from abc import ABC, abstractmethod


class ISchedulerAdapter(ABC):
    @abstractmethod
    def list(self) -> list[dict]:
        """Returns [{id, name, trigger, next_run_time, func_name}, ...]"""


class ServiceSchedulerAdapter(ISchedulerAdapter):
    def __init__(self, scheduler=None):
        self._scheduler = scheduler

    def list(self) -> list[dict]:
        if self._scheduler is None:
            return []
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "func_name": getattr(job.func, "__name__", str(job.func)),
            }
            for job in jobs
        ]
