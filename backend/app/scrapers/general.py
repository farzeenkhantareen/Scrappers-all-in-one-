"""
General Scraper Orchestrator.

Crawls a website, detects all social media links,
and automatically launches the appropriate sub-scrapers.
"""

import asyncio
from typing import Any, Callable, Optional

from app.scrapers.base import BaseScraper
from app.scrapers.website import WebsiteScraper
from app.scrapers.google_maps import GoogleMapsScraper
from app.scrapers.instagram import InstagramScraper
from app.scrapers.linkedin import LinkedInScraper
from app.scrapers.facebook import FacebookScraper
from app.config import settings


class GeneralScraper(BaseScraper):
    """
    Master orchestrator that:
    1. Crawls the entire target website
    2. Detects all social media & platform links
    3. Automatically launches sub-scrapers for each detected platform
    4. Aggregates all results into a unified project
    """

    PLATFORM_SCRAPERS = {
        "google_maps": GoogleMapsScraper,
        "instagram": InstagramScraper,
        "linkedin": LinkedInScraper,
        "facebook": FacebookScraper,
    }

    def __init__(self, job_id: str, url: str, config: dict,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None,
                 sub_job_callback: Optional[Callable] = None):
        super().__init__(job_id, config, progress_callback, log_callback)
        self.start_url = url
        self._sub_job_callback = sub_job_callback

    async def run(self) -> dict:
        """
        Full pipeline:
        Website crawl → Social detection → Sub-scraper launch → Aggregate
        """
        self.log_info("🚀 Starting General Scraper", url=self.start_url)

        result = {
            "website": None,
            "social_profiles": {},
            "detected_platforms": [],
            "sub_jobs": [],
        }

        # ── Step 1: Website Crawl ──────────────────────────────────────────
        self.log_info("Step 1/3: Crawling website...")
        website_scraper = WebsiteScraper(
            job_id=f"{self.job_id}_website",
            url=self.start_url,
            config=self.config,
            progress_callback=self._forward_progress,
            log_callback=self._log_callback,
        )
        website_result = await website_scraper.run()
        result["website"] = website_result

        # ── Step 2: Aggregate social links from all pages ──────────────────
        self.log_info("Step 2/3: Detecting social media links...")
        all_social: dict[str, set] = {}

        for page in website_result.get("pages", []):
            for platform, links in page.get("social_links", {}).items():
                all_social.setdefault(platform, set()).update(links)

        # Also from summary
        summary_social = website_result.get("summary", {}).get("total_social_links", {})
        for platform, links in summary_social.items():
            all_social.setdefault(platform, set()).update(links)

        result["detected_platforms"] = list(all_social.keys())
        self.log_info(
            f"Detected {len(all_social)} platforms",
            platforms=list(all_social.keys())
        )

        # ── Step 3: Launch sub-scrapers ────────────────────────────────────
        if self.config.get("auto_launch_social", True):
            self.log_info("Step 3/3: Launching sub-scrapers...")

            tasks = []
            for platform, urls in all_social.items():
                scraper_cls = self.PLATFORM_SCRAPERS.get(platform)
                if not scraper_cls:
                    self.log_info(f"No scraper for platform: {platform}")
                    continue

                # Take the first (best) URL for this platform
                best_url = next(iter(urls))
                self.log_info(f"Launching {platform} scraper", url=best_url)

                # Notify parent about sub-job creation
                sub_job_id = f"{self.job_id}_{platform}"
                if self._sub_job_callback:
                    self._sub_job_callback({
                        "sub_job_id": sub_job_id,
                        "platform": platform,
                        "url": best_url,
                    })

                scraper = scraper_cls(
                    job_id=sub_job_id,
                    url=best_url,
                    config=self.config,
                    progress_callback=self._forward_progress,
                    log_callback=self._log_callback,
                )
                tasks.append(self._run_sub_scraper(platform, scraper))

            # Run all sub-scrapers concurrently
            sub_results = await asyncio.gather(*tasks, return_exceptions=True)
            for sub_result in sub_results:
                if isinstance(sub_result, Exception):
                    self.log_error(f"Sub-scraper error: {sub_result}")
                elif sub_result:
                    platform_name, data = sub_result
                    result["social_profiles"][platform_name] = data
                    result["sub_jobs"].append({"platform": platform_name, "status": "completed"})

        self.log_info("✅ General Scraper complete", url=self.start_url)
        return result

    async def _run_sub_scraper(self, platform: str, scraper: BaseScraper):
        """Run a sub-scraper and return (platform, result)."""
        try:
            data = await scraper.run()
            return (platform, data)
        except Exception as e:
            self.log_error(f"{platform} scraper failed: {e}")
            return (platform, {"error": str(e)})

    def _forward_progress(self, progress: dict):
        """Forward sub-scraper progress to parent callback."""
        if self.progress._callback:
            self.progress._callback(progress)
