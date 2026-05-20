"""Tests for TaskScheduler background job scheduling."""
import time


def test_scheduler_runs_job_at_interval():
    from lib.tasks.scheduler import TaskScheduler
    results = []
    scheduler = TaskScheduler()
    scheduler.add_job(lambda: results.append(1), "interval", seconds=0.05)
    scheduler.start()
    time.sleep(0.2)
    scheduler.stop()
    assert len(results) >= 2, "Job should have run at least twice in 200ms"


def test_scheduler_start_is_idempotent():
    from lib.tasks.scheduler import TaskScheduler
    scheduler = TaskScheduler()
    scheduler.start()
    scheduler.start()  # second call must not raise or double-start
    scheduler.stop()


def test_scheduler_stop_is_idempotent():
    from lib.tasks.scheduler import TaskScheduler
    scheduler = TaskScheduler()
    scheduler.start()
    scheduler.stop()
    scheduler.stop()  # second call must not raise


def test_scheduler_add_job_before_start():
    from lib.tasks.scheduler import TaskScheduler
    scheduler = TaskScheduler()
    job = scheduler.add_job(lambda: None, "interval", seconds=60)
    assert job is not None
    scheduler.start()
    scheduler.stop()
