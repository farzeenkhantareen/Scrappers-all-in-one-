"""
Base scraper class with shared utilities: rate limiting, retry logic,
progress tracking, logging, and Playwright browser management.
"""

import asyncio
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from urllib.parse import urljoin, urlparse

import httpx
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


class ScraperProgress:
    """Tracks and reports scraping progress."""

    def __init__(self, job_id: str, progress_callback: Optional[Callable] = None):
        self.job_id = job_id
        self.total_pages = 0
        self.scraped_pages = 0
        self.items_found = 0
        self.current_url = ""
        self.start_time = time.time()
        self._callback = progress_callback

    @property
    def progress_pct(self) -> float:
        if self.total_pages == 0:
            return 0.0
        return min(round((self.scraped_pages / self.total_pages) * 100, 1), 100.0)

    @property
    def elapsed_seconds(self) -> float:
        return round(time.time() - self.start_time, 1)

    def update(self, current_url: str = "", items_delta: int = 0):
        self.scraped_pages += 1
        self.items_found += items_delta
        self.current_url = current_url
        if self._callback:
            self._callback(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "progress_pct": self.progress_pct,
            "scraped_pages": self.scraped_pages,
            "total_pages": self.total_pages,
            "items_found": self.items_found,
            "current_url": self.current_url,
            "elapsed_seconds": self.elapsed_seconds,
        }


class BaseScraper(ABC):
    """
    Abstract base class for all scraper modules.

    Provides:
    - Browser management (Playwright)
    - Rate limiting and delays
    - Retry logic with exponential backoff
    - User-agent rotation
    - Proxy support
    - Progress tracking
    - Structured logging
    """

    # Social media URL patterns for detection
    SOCIAL_PATTERNS = {
        "instagram": r"(?:https?://)?(?:www\.)?instagram\.com/[\w.]+/?",
        "facebook": r"(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.com)/[\w./-]+/?",
        "linkedin": r"(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in|pub)/[\w-]+/?",
        "twitter": r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/[\w]+/?",
        "youtube": r"(?:https?://)?(?:www\.)?youtube\.com/(?:channel|c|user|@)[\w/-]+/?",
        "tiktok": r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.]+/?",
        "pinterest": r"(?:https?://)?(?:www\.)?pinterest\.com/[\w]+/?",
        "threads": r"(?:https?://)?(?:www\.)?threads\.net/@[\w.]+/?",
        "whatsapp": r"(?:https?://)?(?:wa\.me|api\.whatsapp\.com)/\d+/?",
        "telegram": r"(?:https?://)?(?:www\.)?t\.me/[\w]+/?",
        "google_maps": r"(?:https?://)?(?:www\.)?(?:maps\.google\.com|goo\.gl/maps|maps\.app\.goo\.gl)[\w/?=&%.-]*",
    }

    # Contact info patterns
    EMAIL_PATTERN = re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE
    )
    PHONE_PATTERN = re.compile(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
        r"|(?:\+\d{1,3}[-.\s]?)?\d{10,14}"
        r"|\+\d{1,3}\s\d{1,4}\s\d{4,10}",
        re.VERBOSE,
    )

    def __init__(
        self,
        job_id: str,
        config: dict,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None,
    ):
        self.job_id = job_id
        self.config = config
        self.progress = ScraperProgress(job_id, progress_callback)
        self._log_callback = log_callback
        self._ua = UserAgent()
        self._cancelled = False
        self._paused = False
        self._browser = None
        self._context = None
        self._page = None

    # ─────────────────────────────────────────────────────────────
    # Abstract interface
    # ─────────────────────────────────────────────────────────────
    @abstractmethod
    async def run(self) -> dict:
        """Execute the scraping job and return structured results."""
        ...

    # ─────────────────────────────────────────────────────────────
    # Browser management
    # ─────────────────────────────────────────────────────────────
    async def _init_browser(self):
        """Start a Playwright Chromium browser."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.HEADLESS_BROWSER,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
            ],
        )
        proxy = None
        if settings.PROXY_URL:
            proxy = {"server": settings.PROXY_URL}
            if settings.PROXY_USERNAME:
                proxy["username"] = settings.PROXY_USERNAME
                proxy["password"] = settings.PROXY_PASSWORD

        self._context = await self._browser.new_context(
            user_agent=self._ua.random,
            viewport={"width": 1920, "height": 1080},
            proxy=proxy,
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        # Remove automation flags
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self._page = await self._context.new_page()

    async def _close_browser(self):
        """Gracefully close Playwright browser."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if hasattr(self, "_playwright"):
                await self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    async def _goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000):
        """Navigate to a URL with retry logic."""
        await self._page.goto(url, wait_until=wait_until, timeout=timeout)
        await self._delay()

    # ─────────────────────────────────────────────────────────────
    # Rate limiting
    # ─────────────────────────────────────────────────────────────
    async def _delay(self, extra_ms: int = 0):
        """Enforce configured delay between requests."""
        delay_ms = self.config.get("delay_ms", settings.DEFAULT_DELAY_MS) + extra_ms
        await asyncio.sleep(delay_ms / 1000)

    async def _check_pause(self):
        """Block execution if job is paused."""
        while self._paused and not self._cancelled:
            await asyncio.sleep(0.5)

    # ─────────────────────────────────────────────────────────────
    # Social link detection
    # ─────────────────────────────────────────────────────────────
    def detect_social_links(self, html: str, base_url: str = "") -> dict[str, list[str]]:
        """Extract all social media links from HTML content."""
        found: dict[str, list[str]] = {}
        for platform, pattern in self.SOCIAL_PATTERNS.items():
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                found[platform] = list(set(matches))
        return found

    # ─────────────────────────────────────────────────────────────
    # Contact extraction
    # ─────────────────────────────────────────────────────────────
    def extract_emails(self, text: str) -> list[str]:
        return list(set(self.EMAIL_PATTERN.findall(text)))

    def extract_phones(self, text: str) -> list[str]:
        return list(set(self.PHONE_PATTERN.findall(text)))

    # ─────────────────────────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────────────────────────
    def log(self, level: str, message: str, context: dict = None):
        """Emit a structured log entry."""
        entry = {
            "job_id": self.job_id,
            "level": level,
            "message": message,
            "context": context or {},
        }
        getattr(logger, level, logger.info)(message, extra={"context": context})
        if self._log_callback:
            self._log_callback(entry)

    def log_info(self, msg: str, **ctx):
        self.log("info", msg, ctx)

    def log_warn(self, msg: str, **ctx):
        self.log("warning", msg, ctx)

    def log_error(self, msg: str, **ctx):
        self.log("error", msg, ctx)

    # ─────────────────────────────────────────────────────────────
    # URL utilities
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def normalize_url(url: str, base: str = "") -> str:
        """Resolve relative URLs against base and normalize."""
        if url.startswith("//"):
            scheme = urlparse(base).scheme or "https"
            url = f"{scheme}:{url}"
        elif url.startswith("/"):
            parsed = urlparse(base)
            url = f"{parsed.scheme}://{parsed.netloc}{url}"
        elif not url.startswith("http"):
            url = urljoin(base, url)
        return url.rstrip("/")

    @staticmethod
    def same_domain(url1: str, url2: str) -> bool:
        """Check if two URLs share the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc

    # ─────────────────────────────────────────────────────────────
    # Cancel / Pause control
    # ─────────────────────────────────────────────────────────────
    def cancel(self):
        self._cancelled = True

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
