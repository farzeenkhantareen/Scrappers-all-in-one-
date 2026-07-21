"""
LinkedIn Company Page Scraper using Playwright.
Extracts company info, followers, posts, and job listings.

LinkedIn blocks headless browsers aggressively, so we use:
  1. OG / JSON-LD meta tags first (no JS needed)
  2. Wide CSS attribute selectors that survive class-name obfuscation
  3. Regex over raw HTML as final fallback
"""

import re
import json
from typing import Callable, Optional

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    """Scrapes LinkedIn public company pages."""

    def __init__(self, job_id: str, url: str, config: dict,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        super().__init__(job_id, config, progress_callback, log_callback)
        self.company_url = self._normalize_linkedin_url(url)
        self.max_posts = config.get("max_posts", 20)
        self.include_jobs = config.get("include_jobs", True)

    def _normalize_linkedin_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith("http"):
            slug = url.strip("/").split("/")[-1]
            return f"https://www.linkedin.com/company/{slug}/"
        if not url.rstrip("/").endswith("/"):
            url = url.rstrip("/") + "/"
        return url

    # ------------------------------------------------------------------
    async def run(self) -> dict:
        self.log_info("Starting LinkedIn scraper", url=self.company_url)
        try:
            await self._init_browser()
            await self._goto(self.company_url, wait_until="networkidle", timeout=60000)
            await self._page.wait_for_timeout(3000)

            company = await self._extract_company_info()
            company["posts"] = await self._extract_posts()

            if self.include_jobs:
                company["jobs"] = await self._extract_jobs()

            self.progress.update(items_delta=1)
            self.log_info(
                f"LinkedIn: {company.get('name')} | "
                f"Followers: {company.get('followers')} | "
                f"Industry: {company.get('industry')}"
            )
            return company

        except Exception as e:
            self.log_error(f"LinkedIn scrape failed: {e}", url=self.company_url)
            return {"error": str(e), "url": self.company_url}
        finally:
            await self._close_browser()

    # ------------------------------------------------------------------
    async def _extract_company_info(self) -> dict:
        company = {
            "profile_url": self.company_url,
            "name": "",
            "tagline": "",
            "description": "",
            "industry": "",
            "company_size": "",
            "employees": "",
            "headquarters": "",
            "founded": "",
            "website": "",
            "specialties": [],
            "followers": 0,
            "type": "",
            "locations": [],
            "logo": "",
        }

        html = await self._page.content()
        soup = BeautifulSoup(html, "lxml")

        # ── OG / meta ─────────────────────────────────────────────────
        og_title = soup.find("meta", property="og:title")
        if og_title:
            company["name"] = og_title.get("content", "").split("|")[0].strip()

        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            company["description"] = og_desc.get("content", "")

        og_image = soup.find("meta", property="og:image")
        if og_image:
            company["logo"] = og_image.get("content", "")

        # ── JSON-LD ───────────────────────────────────────────────────
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and data.get("@type") in ("Organization", "Corporation"):
                    company["name"] = data.get("name", company["name"])
                    company["description"] = data.get("description", company["description"])
                    company["website"] = data.get("url", company["website"])
                    addr = data.get("address", {})
                    if isinstance(addr, dict):
                        parts = [addr.get("streetAddress", ""), addr.get("addressLocality", ""),
                                 addr.get("addressCountry", "")]
                        company["headquarters"] = ", ".join(p for p in parts if p)
                    break
            except Exception:
                pass

        # ── Regex fallbacks over raw HTML ─────────────────────────────
        # Followers
        if company["followers"] == 0:
            for pattern in [
                r'"followerCount"\s*:\s*(\d+)',
                r'([\d,]+)\s+followers',
            ]:
                m = re.search(pattern, html, re.I)
                if m:
                    raw = m.group(1).replace(",", "")
                    if raw.isdigit():
                        company["followers"] = int(raw)
                    break

        # Company size
        m = re.search(r'"employeeCount"\s*:\s*(\d+)', html)
        if m:
            company["employees"] = m.group(1)

        # ── DOM selectors ─────────────────────────────────────────────
        try:
            # Name
            name_el = await self._page.query_selector(
                'h1[class*="org-top-card-summary__title"], '
                'h1[class*="t-24"], '
                'h1'
            )
            if name_el:
                t = (await name_el.inner_text()).strip()
                if t:
                    company["name"] = t

            # Tagline
            for sel in ['p[class*="tagline"]', 'p[class*="org-top-card-summary__tagline"]']:
                el = await self._page.query_selector(sel)
                if el:
                    company["tagline"] = (await el.inner_text()).strip()
                    break

            # Followers — look for text containing "followers"
            page_text = await self._page.inner_text("body")
            f_match = re.search(r"([\d,]+)\s+followers", page_text, re.I)
            if f_match and company["followers"] == 0:
                company["followers"] = int(f_match.group(1).replace(",", ""))

            # About / description from about section
            about_section = await self._page.query_selector(
                'section[data-test-id="about-us"], '
                'section[class*="about-us"], '
                'div[class*="about-us__description"]'
            )
            if about_section:
                company["description"] = (await about_section.inner_text()).strip()

            # Detail dl/dt/dd pairs
            detail_keys = await self._page.query_selector_all('dl dt')
            detail_vals = await self._page.query_selector_all('dl dd')
            for k_el, v_el in zip(detail_keys, detail_vals):
                try:
                    key = (await k_el.inner_text()).strip().lower()
                    val = (await v_el.inner_text()).strip()
                    if "industry" in key:
                        company["industry"] = val
                    elif "size" in key or "employee" in key:
                        company["company_size"] = val
                    elif "headquarter" in key or "location" in key:
                        company["headquarters"] = val
                    elif "founded" in key:
                        company["founded"] = val
                    elif "type" in key:
                        company["type"] = val
                    elif "website" in key or "address" in key:
                        if val.startswith("http"):
                            company["website"] = val
                except Exception:
                    pass

            # Specialties
            for sel in ['p[class*="specialties"]', 'div[class*="specialties"]']:
                el = await self._page.query_selector(sel)
                if el:
                    spec_text = (await el.inner_text()).strip()
                    company["specialties"] = [s.strip() for s in spec_text.split(",") if s.strip()]
                    break

        except Exception as e:
            self.log_warn(f"LinkedIn DOM extraction partial: {e}")

        return company

    # ------------------------------------------------------------------
    async def _extract_posts(self) -> list[dict]:
        posts = []
        try:
            posts_url = self.company_url.rstrip("/") + "/posts/"
            await self._goto(posts_url, wait_until="domcontentloaded", timeout=30000)
            await self._page.wait_for_timeout(2000)

            for _ in range(3):
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self._page.wait_for_timeout(1500)

            post_els = await self._page.query_selector_all(
                'li[class*="occludable-update"], '
                'div[class*="feed-shared-update-v2"], '
                'article'
            )

            for post_el in post_els[:self.max_posts]:
                try:
                    post = {}
                    for sel in [
                        'div[class*="feed-shared-text"]',
                        'span[class*="break-words"]',
                        'div[class*="commentary"]',
                    ]:
                        text_el = await post_el.query_selector(sel)
                        if text_el:
                            post["text"] = (await text_el.inner_text()).strip()
                            break
                    post.setdefault("text", "")

                    date_el = await post_el.query_selector(
                        'span[class*="visually-hidden"], time, span[class*="date"]'
                    )
                    post["date"] = (await date_el.inner_text()).strip() if date_el else ""

                    img_el = await post_el.query_selector('img[class*="ivm-view-attr"]')
                    post["image"] = await img_el.get_attribute("src") if img_el else ""

                    if post.get("text") or post.get("image"):
                        posts.append(post)
                except Exception:
                    continue

        except Exception as e:
            self.log_warn(f"LinkedIn posts extraction failed: {e}")

        return posts

    # ------------------------------------------------------------------
    async def _extract_jobs(self) -> list[dict]:
        jobs = []
        try:
            jobs_url = self.company_url.rstrip("/") + "/jobs/"
            await self._goto(jobs_url, wait_until="domcontentloaded", timeout=30000)
            await self._page.wait_for_timeout(2000)

            job_els = await self._page.query_selector_all(
                'li[class*="jobs-job-board-list__item"], '
                'div[class*="job-card-container"]'
            )

            for job_el in job_els[:20]:
                try:
                    job = {}
                    title_el = await job_el.query_selector(
                        'a[class*="job-card-list__title"], '
                        'a[class*="job-card-container__link"]'
                    )
                    job["title"] = (await title_el.inner_text()).strip() if title_el else ""
                    job["url"] = await title_el.get_attribute("href") if title_el else ""

                    loc_el = await job_el.query_selector(
                        'li[class*="metadata-item"], span[class*="job-card-container__metadata-item"]'
                    )
                    job["location"] = (await loc_el.inner_text()).strip() if loc_el else ""

                    if job.get("title"):
                        jobs.append(job)
                except Exception:
                    continue

        except Exception as e:
            self.log_warn(f"LinkedIn jobs extraction failed: {e}")

        return jobs
