"""
SQLAlchemy ORM models for all scraper entities.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text,
    DateTime, ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────
class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    GENERAL = "general"
    WEBSITE = "website"
    GOOGLE_MAPS = "google_maps"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Platform(str, enum.Enum):
    WEBSITE = "website"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    GOOGLE_MAPS = "google_maps"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


# ─────────────────────────────────────────────────────────────────────────────
# Job
# ─────────────────────────────────────────────────────────────────────────────
class Job(Base):
    """Represents a single scraping job."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_uuid)
    type = Column(SAEnum(JobType), nullable=False)
    status = Column(SAEnum(JobStatus), default=JobStatus.QUEUED, nullable=False)

    # Input
    target_url = Column(String, nullable=False)
    config = Column(JSON, default=dict)              # Scraper-specific options

    # Progress
    total_pages = Column(Integer, default=0)
    scraped_pages = Column(Integer, default=0)
    items_found = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    current_url = Column(String, nullable=True)

    # Timing
    created_at = Column(DateTime(timezone=True), default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    elapsed_seconds = Column(Float, default=0.0)

    # Error info
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String, nullable=True)

    # Parent job (for sub-jobs spawned by general scraper)
    parent_job_id = Column(String, ForeignKey("jobs.id"), nullable=True)

    # Relationships
    child_jobs = relationship("Job", backref="parent_job", remote_side=[id])
    logs = relationship("ScraperLog", back_populates="job", cascade="all, delete-orphan")
    scraped_pages_rel = relationship("ScrapedPage", back_populates="job", cascade="all, delete-orphan")
    social_profiles = relationship("SocialProfile", back_populates="job", cascade="all, delete-orphan")
    businesses = relationship("Business", back_populates="job", cascade="all, delete-orphan")
    exports = relationship("ExportRecord", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_type", "type"),
        Index("ix_jobs_created_at", "created_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scraped Page (Website content)
# ─────────────────────────────────────────────────────────────────────────────
class ScrapedPage(Base):
    """Represents a single page scraped from a website."""
    __tablename__ = "scraped_pages"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)

    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    h1 = Column(String, nullable=True)
    headings = Column(JSON, default=list)        # [{level, text}]
    body_text = Column(Text, nullable=True)
    word_count = Column(Integer, default=0)

    # Contact
    emails = Column(JSON, default=list)
    phones = Column(JSON, default=list)
    addresses = Column(JSON, default=list)

    # Social
    social_links = Column(JSON, default=dict)   # {platform: [urls]}

    # Media
    images = Column(JSON, default=list)          # [{src, alt, title}]
    pdfs = Column(JSON, default=list)            # [url]

    # Structured
    schema_org = Column(JSON, default=list)
    open_graph = Column(JSON, default=dict)
    canonical = Column(String, nullable=True)

    # Status
    status_code = Column(Integer, nullable=True)
    crawl_depth = Column(Integer, default=0)
    scraped_at = Column(DateTime(timezone=True), default=utcnow)

    job = relationship("Job", back_populates="scraped_pages_rel")

    __table_args__ = (
        Index("ix_scraped_pages_job_id", "job_id"),
        Index("ix_scraped_pages_url", "url"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Social Profile
# ─────────────────────────────────────────────────────────────────────────────
class SocialProfile(Base):
    """Social media profile data scraped from any platform."""
    __tablename__ = "social_profiles"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    platform = Column(SAEnum(Platform), nullable=False)

    profile_url = Column(String, nullable=False)
    username = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    followers = Column(Integer, nullable=True)
    following = Column(Integer, nullable=True)
    posts_count = Column(Integer, nullable=True)
    profile_picture = Column(String, nullable=True)
    website = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    category = Column(String, nullable=True)
    verified = Column(Boolean, default=False)

    # Platform-specific extra data
    extra_data = Column(JSON, default=dict)

    # Posts/content
    posts = Column(JSON, default=list)

    scraped_at = Column(DateTime(timezone=True), default=utcnow)
    job = relationship("Job", back_populates="social_profiles")

    __table_args__ = (
        Index("ix_social_profiles_job_id", "job_id"),
        Index("ix_social_profiles_platform", "platform"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Business (Google Maps)
# ─────────────────────────────────────────────────────────────────────────────
class Business(Base):
    """Business/place data from Google Maps."""
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)

    name = Column(String, nullable=True)
    place_id = Column(String, nullable=True)
    category = Column(String, nullable=True)
    rating = Column(Float, nullable=True)
    total_reviews = Column(Integer, nullable=True)

    address = Column(Text, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    maps_url = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    opening_hours = Column(JSON, default=dict)
    photos = Column(JSON, default=list)

    reviews = relationship("Review", back_populates="business", cascade="all, delete-orphan")
    scraped_at = Column(DateTime(timezone=True), default=utcnow)
    job = relationship("Job", back_populates="businesses")

    __table_args__ = (
        Index("ix_businesses_job_id", "job_id"),
        Index("ix_businesses_place_id", "place_id"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Review
# ─────────────────────────────────────────────────────────────────────────────
class Review(Base):
    """Individual review from Google Maps."""
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=gen_uuid)
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False)

    reviewer_name = Column(String, nullable=True)
    reviewer_profile = Column(String, nullable=True)
    reviewer_photo = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)
    text = Column(Text, nullable=True)
    review_date = Column(String, nullable=True)
    owner_reply = Column(Text, nullable=True)
    owner_reply_date = Column(String, nullable=True)
    likes = Column(Integer, default=0)
    images = Column(JSON, default=list)

    scraped_at = Column(DateTime(timezone=True), default=utcnow)
    business = relationship("Business", back_populates="reviews")


# ─────────────────────────────────────────────────────────────────────────────
# Log
# ─────────────────────────────────────────────────────────────────────────────
class ScraperLog(Base):
    """Structured log entry for a scraping job."""
    __tablename__ = "scraper_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    level = Column(SAEnum(LogLevel), nullable=False, default=LogLevel.INFO)
    message = Column(Text, nullable=False)
    context = Column(JSON, default=dict)     # URL, scraper type, etc.
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    job = relationship("Job", back_populates="logs")

    __table_args__ = (
        Index("ix_logs_job_id", "job_id"),
        Index("ix_logs_level", "level"),
        Index("ix_logs_timestamp", "timestamp"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Export Record
# ─────────────────────────────────────────────────────────────────────────────
class ExportRecord(Base):
    """Tracks exported files."""
    __tablename__ = "export_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)
    format = Column(String, nullable=False)       # csv, json, excel, pdf, zip
    scope = Column(String, nullable=False)        # job, all, selected
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    row_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    job = relationship("Job", back_populates="exports")
