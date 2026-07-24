"""
API router: Scraping endpoints — POST to create new scraping jobs.
"""

import asyncio
from datetime import datetime, timezone
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.job_store import job_store
from app.schemas import (
    GeneralScrapeRequest, WebsiteScrapeRequest, GoogleMapsScrapeRequest,
    InstagramScrapeRequest, LinkedInScrapeRequest, FacebookScrapeRequest,
    APIResponse
)
from app.scrapers.general import GeneralScraper
from app.scrapers.website import WebsiteScraper
from app.scrapers.google_maps import GoogleMapsScraper
from app.scrapers.instagram import InstagramScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.facebook import FacebookScraper

logger = logging.getLogger(__name__)
router = APIRouter()

# Dict to store references to running asyncio task objects so they are not garbage collected
_running_tasks = {}

def _make_progress_callback(job_id: str):
    def callback(progress: dict):
        job_store.update_progress(job_id, progress)
    return callback

def _make_log_callback(job_id: str):
    def callback(entry: dict):
        job_store.add_log(job_id, entry.get("level", "info"), entry.get("message", ""), entry.get("context"))
    return callback

async def _run_scraper_task(job_id: str, scraper_class, url: str, config: dict):
    """Asynchronous worker task that executes the scraper and updates job status/results."""
    job_store.set_status(job_id, "running", started_at=datetime.now(timezone.utc).isoformat())
    job_store.add_log(job_id, "info", f"Started scraper of type: {scraper_class.__name__}", {"url": url})
    
    try:
        # Create callback wrappers
        progress_cb = _make_progress_callback(job_id)
        log_cb = _make_log_callback(job_id)
        
        # Instantiate scraper
        scraper = scraper_class(
            job_id=job_id,
            url=url,
            config=config,
            progress_callback=progress_cb,
            log_callback=log_cb
        )
        
        # Run scraper
        result = await scraper.run()
        
        # Save results & update status
        job_store.set_result(job_id, result)
        job_store.set_status(
            job_id, 
            "completed", 
            completed_at=datetime.now(timezone.utc).isoformat(),
            progress_pct=100.0
        )
        job_store.add_log(job_id, "info", "Scraper completed successfully.")
        
    except asyncio.CancelledError:
        job_store.set_status(job_id, "cancelled", completed_at=datetime.now(timezone.utc).isoformat())
        job_store.add_log(job_id, "warning", "Scraper task was cancelled.")
    except Exception as e:
        logger.exception(f"Error in scraper task {job_id}")
        job_store.set_status(
            job_id, 
            "failed", 
            completed_at=datetime.now(timezone.utc).isoformat(),
            error_message=str(e)
        )
        job_store.add_log(job_id, "error", f"Scraper failed: {str(e)}")
    finally:
        _running_tasks.pop(job_id, None)

def _start_scraping_job(job_type: str, url: str, config: dict, scraper_class) -> dict:
    # 1. Create record in job store
    job = job_store.create(job_type, url, config)
    job_id = job["id"]
    
    # 2. Spawn async task
    task = asyncio.create_task(_run_scraper_task(job_id, scraper_class, url, config))
    _running_tasks[job_id] = task
    
    return job

@router.post("/general", summary="Start General Orchestrator Scraper")
async def scrape_general(request: GeneralScrapeRequest) -> APIResponse:
    job = _start_scraping_job("general", request.url, request.model_dump(), GeneralScraper)
    return APIResponse(success=True, message="General scraper job started.", data=job)

@router.post("/website", summary="Start Website Crawler")
async def scrape_website(request: WebsiteScrapeRequest) -> APIResponse:
    job = _start_scraping_job("website", request.url, request.model_dump(), WebsiteScraper)
    return APIResponse(success=True, message="Website scraper job started.", data=job)

@router.post("/google-maps", summary="Start Google Maps Review Scraper")
async def scrape_google_maps(request: GoogleMapsScrapeRequest) -> APIResponse:
    job = _start_scraping_job("google_maps", request.url, request.model_dump(), GoogleMapsScraper)
    return APIResponse(success=True, message="Google Maps scraper job started.", data=job)

@router.post("/instagram", summary="Start Instagram Profile Scraper")
async def scrape_instagram(request: InstagramScrapeRequest) -> APIResponse:
    job = _start_scraping_job("instagram", request.url, request.model_dump(), InstagramScraper)
    return APIResponse(success=True, message="Instagram scraper job started.", data=job)

@router.post("/linkedin", summary="Start LinkedIn Company Scraper")
async def scrape_linkedin(request: LinkedInScrapeRequest) -> APIResponse:
    job = _start_scraping_job("linkedin", request.url, request.model_dump(), LinkedInScraper)
    return APIResponse(success=True, message="LinkedIn scraper job started.", data=job)

@router.post("/facebook", summary="Start Facebook Page Scraper")
async def scrape_facebook(request: FacebookScrapeRequest) -> APIResponse:
    job = _start_scraping_job("facebook", request.url, request.model_dump(), FacebookScraper)
    return APIResponse(success=True, message="Facebook scraper job started.", data=job)
