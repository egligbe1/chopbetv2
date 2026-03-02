import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from gemini_engine import generate_predictions
from results_checker import check_results

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def start_scheduler():
    """Starts the background scheduler with daily jobs."""
    
    # 7:00 AM UTC: Run prediction engine for football
    scheduler.add_job(
        generate_predictions,
        trigger=CronTrigger(hour=7, minute=0, timezone="UTC"),
        id="prediction_job_football",
        name="Generate Daily Football Predictions",
        replace_existing=True
    )
    
    
    # 11:00 PM UTC: Run football results checker
    scheduler.add_job(
        check_results,
        trigger=CronTrigger(hour=23, minute=0, timezone="UTC"),
        id="results_job_football",
        name="Check Daily Football Results",
        replace_existing=True
    )
    
    
    scheduler.start()
    logger.info("Scheduler started with daily jobs: football predictions at 07:00 UTC, football results at 23:00 UTC.")

def shutdown_scheduler():
    """Shuts down the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
