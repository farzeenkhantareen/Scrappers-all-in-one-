"""
Celery task definitions for all scraper modules.
Each task wraps its scraper, updates job status in DB, and publishes
progress/log events to Redis pub/sub for real-time WebSocket delivery.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis as sync_redis
from celery import Task

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

# Synchronous Redis client for pub/sub (Celery tasks are sync)
_redis = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)


def _publish_event(channel: str, event: dict):
    """Publish a JSON event to a Redis pub/sub channel."""
    try:
        _redis.publish(channel, json.dumps(event, default=str))
    except Exception as e:
        logger.warning(f"Redis publish failed: {e}")


def _update_job_status(job_id: str, status: str, **kwargs):
    """Store job status update in Redis (for fast lookups)."""
    key = f"job:{job_id}"
    data = {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    data.update(kwargs)
    _redis.hset(key, mapping={k: json.dumps(v, default=str) for k, v in data.items()})
    _redis.expire(key, 86400)  # 24 hour TTL

    _publish_event(f"job:{job_id}", {"type": "status", "job_id": job_id, **data})


def _make_progress_callback(job_id: str):
    """Create a progress callback that publishes to Redis."""
    def callback(progress: dict):
        _publish_event(f"job:{job_id}", {"type": "progress", **progress})
    return callback


def _make_log_callback(job_id: str):
    """Create a log callback that publishes to Redis and stores in DB."""
    def callback(entry: dict):
        _publish_event(f"job:{job_id}:logs", {"type": "log", **entry})
    return callback


def _run_async(coro):
    """Run an async coroutine synchronously inside Celery task."""
    import sys
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# General Scraper Task
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_general_scraper", max_retries=3)
def run_general_scraper(self: Task, job_id: str, url: str, config: dict) -> dict:
    """Celery task: Run the general orchestrator scraper."""
    from app.scrapers.general import GeneralScraper

    logger.info(f"[{job_id}] Starting general scraper: {url}")
    _update_job_status(job_id, "running", celery_task_id=self.request.id)

    try:
        scraper = GeneralScraper(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=_make_progress_callback(job_id),
            log_callback=_make_log_callback(job_id),
        )
        result = _run_async(scraper.run())
        _update_job_status(job_id, "completed", result_summary={
            "pages": len(result.get("website", {}).get("pages", [])),
            "platforms": result.get("detected_platforms", []),
        })
        return result

    except Exception as exc:
        logger.error(f"[{job_id}] General scraper failed: {exc}")
        _update_job_status(job_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# ─────────────────────────────────────────────────────────────────────────────
# Website Scraper Task
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_website_scraper", max_retries=3)
def run_website_scraper(self: Task, job_id: str, url: str, config: dict) -> dict:
    """Celery task: Run the website crawler."""
    from app.scrapers.website import WebsiteScraper

    logger.info(f"[{job_id}] Starting website scraper: {url}")
    _update_job_status(job_id, "running", celery_task_id=self.request.id)

    try:
        scraper = WebsiteScraper(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=_make_progress_callback(job_id),
            log_callback=_make_log_callback(job_id),
        )
        result = _run_async(scraper.run())
        _update_job_status(job_id, "completed")
        return result

    except Exception as exc:
        logger.error(f"[{job_id}] Website scraper failed: {exc}")
        _update_job_status(job_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


# ─────────────────────────────────────────────────────────────────────────────
# Google Maps Task
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_google_maps_scraper", max_retries=3)
def run_google_maps_scraper(self: Task, job_id: str, url: str, config: dict) -> dict:
    """Celery task: Run the Google Maps review scraper."""
    from app.scrapers.google_maps import GoogleMapsScraper

    logger.info(f"[{job_id}] Starting Google Maps scraper: {url}")
    _update_job_status(job_id, "running", celery_task_id=self.request.id)

    try:
        scraper = GoogleMapsScraper(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=_make_progress_callback(job_id),
            log_callback=_make_log_callback(job_id),
        )
        result = _run_async(scraper.run())
        _update_job_status(job_id, "completed")
        return result

    except Exception as exc:
        logger.error(f"[{job_id}] Google Maps scraper failed: {exc}")
        _update_job_status(job_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


# ─────────────────────────────────────────────────────────────────────────────
# Instagram Task
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_instagram_scraper", max_retries=2)
def run_instagram_scraper(self: Task, job_id: str, url: str, config: dict) -> dict:
    from app.scrapers.instagram import InstagramScraper

    logger.info(f"[{job_id}] Starting Instagram scraper: {url}")
    _update_job_status(job_id, "running", celery_task_id=self.request.id)

    try:
        scraper = InstagramScraper(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=_make_progress_callback(job_id),
            log_callback=_make_log_callback(job_id),
        )
        result = _run_async(scraper.run())
        _update_job_status(job_id, "completed")
        return result

    except Exception as exc:
        logger.error(f"[{job_id}] Instagram scraper failed: {exc}")
        _update_job_status(job_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Task
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_linkedin_scraper", max_retries=2)
def run_linkedin_scraper(self: Task, job_id: str, url: str, config: dict) -> dict:
    from app.scrapers.linkedin import LinkedInScraper

    logger.info(f"[{job_id}] Starting LinkedIn scraper: {url}")
    _update_job_status(job_id, "running", celery_task_id=self.request.id)

    try:
        scraper = LinkedInScraper(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=_make_progress_callback(job_id),
            log_callback=_make_log_callback(job_id),
        )
        result = _run_async(scraper.run())
        _update_job_status(job_id, "completed")
        return result

    except Exception as exc:
        logger.error(f"[{job_id}] LinkedIn scraper failed: {exc}")
        _update_job_status(job_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


# ─────────────────────────────────────────────────────────────────────────────
# Facebook Task
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="tasks.run_facebook_scraper", max_retries=2)
def run_facebook_scraper(self: Task, job_id: str, url: str, config: dict) -> dict:
    from app.scrapers.facebook import FacebookScraper

    logger.info(f"[{job_id}] Starting Facebook scraper: {url}")
    _update_job_status(job_id, "running", celery_task_id=self.request.id)

    try:
        scraper = FacebookScraper(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=_make_progress_callback(job_id),
            log_callback=_make_log_callback(job_id),
        )
        result = _run_async(scraper.run())
        _update_job_status(job_id, "completed")
        return result

    except Exception as exc:
        logger.error(f"[{job_id}] Facebook scraper failed: {exc}")
        _update_job_status(job_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)
