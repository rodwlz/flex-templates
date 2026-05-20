"""Background task scheduler powered by APScheduler."""
from apscheduler.schedulers.background import BackgroundScheduler


class TaskScheduler:
    """Thin wrapper around APScheduler for background jobs.

    Wire into main.py start/stop lifecycle:
        scheduler = TaskScheduler()
        scheduler.add_job(my_func, "interval", hours=24)
        scheduler.start()   # before ft.run() / _stop.wait()
        # ... app runs ...
        scheduler.stop()    # in finally block

    Trigger types (APScheduler):
        "interval"  — recurring on fixed interval (seconds=, minutes=, hours=)
        "cron"      — cron-style scheduling (hour=9, minute=0, day_of_week="mon-fri")
        "date"      — run once at a specific datetime
    """

    def __init__(self):
        self._scheduler = BackgroundScheduler()

    def add_job(self, func, trigger: str = "interval", **kwargs):
        """Schedule *func* with *trigger* and APScheduler kwargs.

        Examples:
            scheduler.add_job(send_report, "cron", hour=9, minute=0)
            scheduler.add_job(cleanup_temp, "interval", hours=6)
        """
        return self._scheduler.add_job(func, trigger, **kwargs)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
