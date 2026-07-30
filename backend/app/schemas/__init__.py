"""
Pydantic schemas for request validation and response serialization.
"""

from pydantic import BaseModel, HttpUrl, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Enums (mirrored from models for API use)
# ─────────────────────────────────────────────────────────────────────────────
class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    GENERAL = "general"
    WEBSITE = "website"
    GOOGLE_MAPS = "google_maps"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


class ExportFormat(str, Enum):
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    XML = "xml"
    PDF = "pdf"
    ZIP = "zip"


class SortOrder(str, Enum):
    NEWEST = "newest"
    HIGHEST = "highest"
    LOWEST = "lowest"
    RELEVANT = "relevant"


# ─────────────────────────────────────────────────────────────────────────────
# General Scraper
# ─────────────────────────────────────────────────────────────────────────────
class GeneralScrapeRequest(BaseModel):
    url: str = Field(..., description="Target website URL to crawl")
    max_pages: int = Field(default=100, ge=1, le=10000)
    max_depth: int = Field(default=5, ge=1, le=20)
    auto_launch_social: bool = Field(default=True)
    download_images: bool = Field(default=False)
    download_pdfs: bool = Field(default=False)
    respect_robots: bool = Field(default=True)


# ─────────────────────────────────────────────────────────────────────────────
# Website Scraper
# ─────────────────────────────────────────────────────────────────────────────
class WebsiteScrapeRequest(BaseModel):
    url: str = Field(..., description="Target website URL")
    max_pages: int = Field(default=100, ge=1, le=10000)
    max_depth: int = Field(default=5, ge=1, le=20)
    follow_redirects: bool = True
    download_images: bool = False
    download_pdfs: bool = False
    extract_emails: bool = True
    extract_phones: bool = True
    extract_addresses: bool = True
    extract_schema_org: bool = True
    extract_open_graph: bool = True
    extract_social_links: bool = True
    extract_headings: bool = True
    extract_blog_articles: bool = True
    extract_products: bool = True
    extract_services: bool = True
    extract_faqs: bool = True
    extract_testimonials: bool = True
    extract_contacts: bool = True
    respect_robots: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Google Maps Scraper
# ─────────────────────────────────────────────────────────────────────────────
class GoogleMapsScrapeRequest(BaseModel):
    url: str = Field(..., description="Google Maps URL")
    business_name: Optional[str] = None
    place_id: Optional[str] = None
    max_reviews: int = Field(default=100, ge=1, le=5000)
    sort_order: SortOrder = SortOrder.NEWEST
    include_owner_replies: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Instagram Scraper
# ─────────────────────────────────────────────────────────────────────────────
class InstagramScrapeRequest(BaseModel):
    url: str = Field(..., description="Instagram profile URL")
    max_posts: int = Field(default=50, ge=1, le=500)
    download_media: bool = False
    include_reels: bool = True
    include_tagged: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# LinkedIn Scraper
# ─────────────────────────────────────────────────────────────────────────────
class LinkedInScrapeRequest(BaseModel):
    url: str = Field(..., description="LinkedIn company page URL")
    max_posts: int = Field(default=20, ge=1, le=200)
    include_jobs: bool = True
    include_employees: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Facebook Scraper
# ─────────────────────────────────────────────────────────────────────────────
class FacebookScrapeRequest(BaseModel):
    url: str = Field(..., description="Facebook page URL")
    max_posts: int = Field(default=30, ge=1, le=300)
    include_reviews: bool = True
    include_events: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Job Responses
# ─────────────────────────────────────────────────────────────────────────────
class JobProgress(BaseModel):
    job_id: str
    status: JobStatus
    type: JobType
    target_url: str
    progress_pct: float
    scraped_pages: int
    total_pages: int
    items_found: int
    current_url: Optional[str]
    elapsed_seconds: float
    started_at: Optional[datetime]

    class Config:
        from_attributes = True


class JobSummary(BaseModel):
    id: str
    type: JobType
    status: JobStatus
    target_url: str
    progress_pct: float
    items_found: int
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class JobDetail(JobSummary):
    config: Dict[str, Any]
    scraped_pages: int
    total_pages: int
    elapsed_seconds: float
    celery_task_id: Optional[str]
    child_jobs: List["JobSummary"] = []

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# Export Request
# ─────────────────────────────────────────────────────────────────────────────
class ExportRequest(BaseModel):
    format: ExportFormat
    job_ids: Optional[List[str]] = None   # None = all jobs
    include_logs: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_pages_scraped: int
    total_businesses: int
    total_reviews: int
    total_social_profiles: int
    jobs_by_type: Dict[str, int]
    jobs_by_status: Dict[str, int]
    recent_jobs: List[JobSummary]


# ─────────────────────────────────────────────────────────────────────────────
# Log Entry
# ─────────────────────────────────────────────────────────────────────────────
class LogEntry(BaseModel):
    id: str
    job_id: str
    level: str
    message: str
    context: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────────────────────────────────────
# API Response Wrapper
# ─────────────────────────────────────────────────────────────────────────────
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
