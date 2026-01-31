from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def sync_job():
    try:
        # We suppress stdout to avoid cluttering the console too much
        # But for debugging, maybe we want to log it?
        # For now, let's trust the command's internal logging or add explicit logging here.
        call_command('sync_status', stdout=None) 
    except Exception as e:
        logger.error(f"Scheduler Job Error: {e}")

def start():
    scheduler = BackgroundScheduler()
    # Run every 1 minute
    scheduler.add_job(sync_job, 'interval', minutes=1, id='sync_twilio_status', replace_existing=True)
    scheduler.start()
    logger.info("Background Scheduler Started: Syncing Twilio Status every 1 minute.")
