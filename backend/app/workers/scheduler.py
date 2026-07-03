"""
APScheduler scheduled jobs for market-aware task execution.

Schedules:
  - market_pre_open: runs before market open (8:30 ET)
  - post_market_screener: runs after market close (16:30 ET)
  - portfolio_snapshot: every 5 minutes during market hours
  - risk_check: every minute
  - order_reconciliation: every minute

For MVP, jobs use mock data and log their execution.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.time import now_eastern

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def job_market_pre_open() -> None:
    logger.info("Scheduled: market pre-open refresh at %s", now_eastern().isoformat())


async def job_post_market_screener() -> None:
    logger.info("Scheduled: post-market screener run at %s", now_eastern().isoformat())


async def job_portfolio_snapshot() -> None:
    logger.info("Scheduled: portfolio snapshot at %s", now_eastern().isoformat())


async def job_risk_check() -> None:
    logger.info("Scheduled: risk check at %s", now_eastern().isoformat())


async def job_order_reconciliation() -> None:
    logger.info("Scheduled: order reconciliation at %s", now_eastern().isoformat())


def setup_scheduler() -> None:
    scheduler.add_job(job_market_pre_open, CronTrigger(hour=8, minute=30, timezone="US/Eastern"), id="pre_open")
    scheduler.add_job(job_post_market_screener, CronTrigger(hour=16, minute=30, timezone="US/Eastern"), id="post_market")
    scheduler.add_job(job_portfolio_snapshot, IntervalTrigger(minutes=5), id="portfolio_snapshot")
    scheduler.add_job(job_risk_check, IntervalTrigger(minutes=1), id="risk_check")
    scheduler.add_job(job_order_reconciliation, IntervalTrigger(minutes=1), id="order_reconciliation")
    logger.info("Scheduler configured with %d jobs", len(scheduler.get_jobs()))


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
