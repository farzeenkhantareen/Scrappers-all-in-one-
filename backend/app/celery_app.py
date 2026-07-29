"""
Celery application factory.
"""

from celery import Celery
from app.config import settings


celery_app = Celery(
    "scrappers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scrape_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "tasks.run_general_scraper": {"queue": "general"},
        "tasks.run_website_scraper": {"queue": "website"},
        "tasks.run_google_maps_scraper": {"queue": "maps"},
        "tasks.run_instagram_scraper": {"queue": "social"},
        "tasks.run_linkedin_scraper": {"queue": "social"},
        "tasks.run_facebook_scraper": {"queue": "social"},
    },
    task_soft_time_limit=1800,   # 30 min
    task_time_limit=3600,        # 1 hour hard limit
)
