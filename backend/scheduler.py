import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from gemini_engine import generate_predictions
from results_checker import check_results

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def start_scheduler():
    """Starts the background scheduler with daily jobs."""
    
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


    # Every 4 hours: run the football results checker. A single daily run missed
    # late-finishing fixtures (e.g. Brazilian Serie A kicks off ~22:30 UTC and
    # finishes after a 23:00 check), leaving them pending for ~24h. Running at
    # 00/04/08/12/16/20 UTC settles any finished match within a few hours. The
    # checker only touches still-pending predictions, so extra runs are cheap.
    scheduler.add_job(
        check_results,
        trigger=CronTrigger(hour="0,4,8,12,16,20", minute=0, timezone="UTC"),
        id="results_job_football",
        name="Check Football Results (every 4h)",
        replace_existing=True,
        **job_guards
    )


    scheduler.start()
    logger.info("Scheduler started: football predictions at 07:00 UTC, results check every 4h (00/04/08/12/16/20 UTC).")

def shutdown_scheduler():
    """Shuts down the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
