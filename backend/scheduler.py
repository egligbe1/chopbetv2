import os
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from gemini_engine import generate_predictions
from results_checker import check_results

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _scheduler_enabled() -> bool:
    return os.getenv("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")


def start_scheduler():
    """Starts the background scheduler with daily jobs.

    Disabled when ENABLE_SCHEDULER is falsy — used on Render's free tier where
    the service sleeps (an in-process scheduler can't fire while asleep). There,
    an external scheduler (QStash) calls /admin/cron/* to run the jobs instead.
    """
    if not _scheduler_enabled():
        logger.info("In-process scheduler disabled (ENABLE_SCHEDULER=false). Expecting external triggers (QStash) at /admin/cron/*.")
        return

    # These jobs are long-running (scraping + multiple Gemini calls). Guard against
    # overlap and missed fires so a slow run or a restart near the trigger can't
    # spawn concurrent runs or silently skip.
    job_guards = dict(coalesce=True, max_instances=1, misfire_grace_time=3600)

    # 7:00 AM UTC: Run prediction engine for football
    scheduler.add_job(
        generate_predictions,
        trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
        id="prediction_job_football",
        name="Generate Daily Football Predictions",
        replace_existing=True,
        **job_guards
    )


    # Results checker at 07:00, 17:00, 23:00 UTC. The 07:00 run catches
    # late-finishing fixtures from the previous night (e.g. Brazilian Serie A
    # that ends after the 23:00 check). The checker only touches still-pending
    # predictions, so these runs are cheap.
    scheduler.add_job(
        check_results,
        trigger=CronTrigger(hour="7,17,23", minute=0, timezone="UTC"),
        id="results_job_football",
        name="Check Football Results (07/17/23 UTC)",
        replace_existing=True,
        **job_guards
    )


    scheduler.start()
    logger.info("Scheduler started: predictions at 07:00 UTC, results check at 07:00/17:00/23:00 UTC.")

def shutdown_scheduler():
    """Shuts down the scheduler if it was started."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
