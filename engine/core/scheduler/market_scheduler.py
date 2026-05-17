from apscheduler.schedulers.asyncio import AsyncIOScheduler


class MarketScheduler:
    """Scheduler that runs jobs on a configurable interval."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs = {}

    def register_job(self, job_id: str, func, trigger: str = "interval", **trigger_kwargs):
        """Register a job. trigger_kwargs: e.g. seconds=60, minutes=5."""
        self._jobs[job_id] = (func, trigger, trigger_kwargs)

    def start(self):
        for job_id, (func, trigger, kwargs) in self._jobs.items():
            self.scheduler.add_job(
                func, trigger=trigger, id=job_id, replace_existing=True, **kwargs
            )
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()

    def get_job_count(self) -> int:
        return len(self.scheduler.get_jobs())


scheduler = MarketScheduler()
