"""
Website Scraper: Full recursive crawler using Playwright + BeautifulSoup.

Extracts: page content, emails, phones, addresses, social links,
images, PDFs, schema.org, Open Graph, headings, metadata.
"""

import asyncio
import re
from collections import deque
from typing import Any, Callable, Optional
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper
from app.config import settings


class WebsiteScraper(BaseScraper):
    """
    Recursively crawls a website and extracts structured data from every page.
    Respects robots.txt, enforces depth/page limits, and tracks progress.
    """

    def __init__(self, job_id: str, url: str, config: dict,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        super().__init__(job_id, config, progress_callback, log_callback)
        self.start_url = self.normalize_url(url)
        self.base_domain = urlparse(self.start_url).netloc
        self.visited: set[str] = set()
        self.queue: deque = deque()
        self.results: list[dict] = []
        self._robots: Optional[RobotFileParser] = None

    async def run(self) -> dict:
        """Execute the full website crawl."""
        self.log_info("Starting website crawl", url=self.start_url)

        try:
            await self._init_browser()

            # Load robots.txt
            if self.config.get("respect_robots", True):
                await self._load_robots()

            # Seed the queue
            self.queue.append((self.start_url, 0))
            max_pages = self.config.get("max_pages", settings.DEFAULT_MAX_PAGES)
            max_depth = self.config.get("max_depth", settings.DEFAULT_MAX_DEPTH)

            while self.queue and len(self.visited) < max_pages:
                if self._cancelled:
                    break
                await self._check_pause()

                url, depth = self.queue.popleft()
                if url in self.visited or depth > max_depth:
                    continue

                self.visited.add(url)
                page_data = await self._scrape_page(url, depth)
                if page_data:
                    self.results.append(page_data)

                    # Extract and enqueue internal links
                    if depth < max_depth:
                        for link in page_data.get("internal_links", []):
                            if link not in self.visited:
                                self.queue.append((link, depth + 1))

                self.progress.total_pages = len(self.visited) + len(self.queue)
                self.progress.update(current_url=url, items_delta=1)

            self.log_info("Crawl complete",
                          pages=len(self.results),
                          url=self.start_url)

            return {
                "pages": self.results,
                "summary": self._build_summary(),
            }

        except Exception as e:
            self.log_error(f"Crawl failed: {e}", url=self.start_url)
            raise
        finally:
            await self._close_browser()

    async def _load_robots(self):
        """Load and parse robots.txt for the target domain."""
        robots_url = f"{urlparse(self.start_url).scheme}://{self.base_domain}/robots.txt"
        try:
            self._robots = RobotFileParser(robots_url)
            self._robots.read()
            self.log_info("Loaded robots.txt", url=robots_url)
        except Exception as e:
            self.log_warn(f"Could not load robots.txt: {e}")

    def _is_allowed(self, url: str) -> bool:
        """Check if robots.txt allows crawling this URL."""
        if not self._robots:
            return True
        return self._robots.can_fetch("*", url)

    async def _scrape_page(self, url: str, depth: int) -> Optional[dict]:
        """Navigate to a URL and extract all data."""
        if not self._is_allowed(url):
            self.log_warn("Blocked by robots.txt", url=url)
            return None

        try:
            self.log_info(f"Crawling [{depth}]", url=url)
            response = await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            status_code = response.status if response else None

            if status_code and status_code >= 400:
                self.log_warn(f"HTTP {status_code}", url=url)
                return None

            await self._delay()
            html = await self._page.content()
            title = await self._page.title()
            page_url = self._page.url  # Final URL after redirects

            soup = BeautifulSoup(html, "lxml")
            return self._parse_page(soup, html, page_url, title, status_code, depth)

        except Exception as e:
            self.log_error(f"Page scrape error: {e}", url=url)
            return None

    def _parse_page(self, soup: BeautifulSoup, html: str, url: str,
                    title: str, status_code: int, depth: int) -> dict:
        """Parse BeautifulSoup object into structured data."""

        # ── Meta ──────────────────────────────────────────────
        meta_title = ""
        meta_desc = ""
        canonical = ""
        og = {}

        for tag in soup.find_all("meta"):
            name = tag.get("name", "").lower()
            prop = tag.get("property", "").lower()
            content = tag.get("content", "")
            if name == "description":
                meta_desc = content
            elif name in ("title",):
                meta_title = content
            elif prop.startswith("og:"):
                og[prop[3:]] = content

        canonical_tag = soup.find("link", rel="canonical")
        if canonical_tag:
            canonical = canonical_tag.get("href", "")

        # ── Headings ──────────────────────────────────────────
        headings = []
        for level in range(1, 7):
            for h in soup.find_all(f"h{level}"):
                headings.append({"level": level, "text": h.get_text(strip=True)})

        h1 = headings[0]["text"] if headings and headings[0]["level"] == 1 else title

        # ── Body text ─────────────────────────────────────────
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body_text = soup.get_text(separator=" ", strip=True)
        word_count = len(body_text.split())

        # ── Contacts ──────────────────────────────────────────
        emails = self.extract_emails(html)
        phones = self.extract_phones(body_text)

        # Filter out common false-positives
        emails = [e for e in emails if not e.endswith((".png", ".jpg", ".svg", ".css", ".js"))]

        # ── Social links ──────────────────────────────────────
        social_links = self.detect_social_links(html, url)

        # ── Internal links ────────────────────────────────────
        internal_links = []
        external_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            abs_url = self.normalize_url(href, url)
            if not abs_url.startswith("http"):
                continue
            if self.same_domain(abs_url, url):
                internal_links.append(abs_url)
            else:
                external_links.append(abs_url)

        # ── Images ────────────────────────────────────────────
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src", "")
            if src:
                images.append({
                    "src": self.normalize_url(src, url),
                    "alt": img.get("alt", ""),
                    "title": img.get("title", ""),
                })

        # ── PDFs & downloads ──────────────────────────────────
        pdfs = []
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if href.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip")):
                pdfs.append(self.normalize_url(a["href"], url))

        # ── Schema.org ────────────────────────────────────────
        schema_data = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "{}")
                schema_data.append(data)
            except Exception:
                pass

        return {
            "url": url,
            "title": title,
            "meta_title": meta_title or title,
            "meta_description": meta_desc,
            "canonical": canonical,
            "h1": h1,
            "headings": headings,
            "body_text": body_text[:5000],  # Truncate to 5KB
            "word_count": word_count,
            "emails": emails,
            "phones": phones,
            "social_links": social_links,
            "internal_links": list(set(internal_links)),
            "external_links": list(set(external_links))[:50],
            "images": images[:50],
            "pdfs": pdfs,
            "open_graph": og,
            "schema_org": schema_data,
            "status_code": status_code,
            "crawl_depth": depth,
        }

    def _build_summary(self) -> dict:
        """Aggregate stats across all scraped pages."""
        all_emails = set()
        all_phones = set()
        all_social: dict[str, set] = {}
        all_pdfs = []

        for page in self.results:
            all_emails.update(page.get("emails", []))
            all_phones.update(page.get("phones", []))
            all_pdfs.extend(page.get("pdfs", []))
            for platform, links in page.get("social_links", {}).items():
                all_social.setdefault(platform, set()).update(links)

        return {
            "total_pages": len(self.results),
            "total_emails": list(all_emails),
            "total_phones": list(all_phones),
            "total_social_links": {k: list(v) for k, v in all_social.items()},
            "total_pdfs": list(set(all_pdfs)),
        }
