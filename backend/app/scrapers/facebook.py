"""
Facebook Page Scraper using Playwright.
Extracts page info, posts, reviews, events, and contact details.

Facebook aggressively blocks scrapers and login-gates most content.
Strategy:
  1. Navigate to the page (desktop & mobile fallback).
  2. Dismiss cookie/login overlays.
  3. Extract OG meta tags + JSON-LD (always available on public pages).
  4. Use broad text-search and attribute selectors for DOM elements.
  5. Regex over raw HTML for stats (followers, likes) embedded in JSON blobs.
"""

import json
import re
import urllib.parse
from typing import Callable, Optional

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper


class FacebookScraper(BaseScraper):
    """Scrapes public Facebook pages."""

    def __init__(self, job_id: str, url: str, config: dict,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        super().__init__(job_id, config, progress_callback, log_callback)
        self.page_url = self._normalize_fb_url(url)
        self.max_posts = config.get("max_posts", 30)
        self.include_reviews = config.get("include_reviews", True)
        self.include_events = config.get("include_events", True)

    def _normalize_fb_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith("http"):
            return f"https://www.facebook.com/{url.strip('/')}"
        return url

    # ------------------------------------------------------------------
    async def run(self) -> dict:
        self.log_info("Starting Facebook scraper", url=self.page_url)
        try:
            await self._init_browser()
            await self._goto(self.page_url, wait_until="domcontentloaded", timeout=60000)
            await self._page.wait_for_timeout(4000)
            await self._dismiss_overlays()

            page_info = await self._extract_page_info()
            page_info["posts"] = await self._extract_posts()

            if self.include_reviews:
                page_info["reviews"] = await self._extract_reviews()

            if self.include_events:
                page_info["events"] = await self._extract_events()

            self.progress.update(items_delta=1)
            self.log_info(
                f"Facebook: {page_info.get('name')} | "
                f"Followers: {page_info.get('followers')} | "
                f"Likes: {page_info.get('likes')}"
            )
            return page_info

        except Exception as e:
            self.log_error(f"Facebook scrape failed: {e}", url=self.page_url)
            return {"error": str(e), "url": self.page_url}
        finally:
            await self._close_browser()

    # ------------------------------------------------------------------
    async def _dismiss_overlays(self):
        """Dismiss cookie consent and login prompts."""
        selectors = [
            '[aria-label="Close"]',
            '[title="Close"]',
            'button[data-testid="cookie-policy-manage-dialog-decline-button"]',
            'div[aria-label="Decline optional cookies"]',
            'div[aria-label="Allow all cookies"] + div button',   # "Decline" on some locales
        ]
        for sel in selectors:
            try:
                btn = await self._page.query_selector(sel)
                if btn:
                    await btn.evaluate("el => el.click()")
                    await self._page.wait_for_timeout(600)
            except Exception:
                pass

    # ------------------------------------------------------------------
    async def _extract_page_info(self) -> dict:
        info = {
            "profile_url": self.page_url,
            "name": "",
            "username": "",
            "category": "",
            "about": "",
            "likes": 0,
            "followers": 0,
            "website": "",
            "email": "",
            "phone": "",
            "address": "",
            "business_hours": {},
            "rating": None,
            "total_reviews": 0,
            "messenger_link": "",
            "logo": "",
            "cover_photo": "",
        }

        html = await self._page.content()
        soup = BeautifulSoup(html, "lxml")

        # ── OG meta tags ──────────────────────────────────────────────
        og_title = soup.find("meta", property="og:title")
        if og_title:
            info["name"] = og_title.get("content", "")

        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            info["about"] = og_desc.get("content", "")

        og_image = soup.find("meta", property="og:image")
        if og_image:
            info["logo"] = og_image.get("content", "")

        # ── JSON-LD ───────────────────────────────────────────────────
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if not isinstance(data, dict):
                    continue
                t = data.get("@type", "")
                if t in ("LocalBusiness", "Organization", "Restaurant", "Store"):
                    info["name"] = data.get("name", info["name"])
                    info["about"] = data.get("description", info["about"])
                    info["website"] = data.get("url", info["website"])
                    addr = data.get("address", {})
                    if isinstance(addr, dict):
                        info["address"] = ", ".join(filter(None, [
                            addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressCountry"),
                        ]))
                    info["phone"] = data.get("telephone", info["phone"])
                    agg = data.get("aggregateRating", {})
                    if agg:
                        info["rating"] = agg.get("ratingValue")
                        info["total_reviews"] = agg.get("reviewCount", 0)
                    break
            except Exception:
                pass

        # ── Regex over raw HTML (JSON blobs) ──────────────────────────
        # Followers
        for pattern in [
            r'"followerCount"\s*:\s*(\d+)',
            r'"page_likers"\s*:\s*\{"count"\s*:\s*(\d+)',
            r'([\d,]+)\s+(?:people\s+)?follow',
        ]:
            m = re.search(pattern, html, re.I)
            if m:
                raw = m.group(1).replace(",", "")
                if raw.isdigit():
                    info["followers"] = int(raw)
                break

        # Likes
        for pattern in [
            r'"fan_count"\s*:\s*(\d+)',
            r'"page_fans"\s*:\s*(\d+)',
            r'([\d,]+)\s+(?:people\s+)?like',
        ]:
            m = re.search(pattern, html, re.I)
            if m:
                raw = m.group(1).replace(",", "")
                if raw.isdigit():
                    info["likes"] = int(raw)
                break

        # Category
        m = re.search(r'"category"\s*:\s*"([^"]+)"', html)
        if m:
            info["category"] = m.group(1)

        # Username from URL
        try:
            path = urllib.parse.urlparse(self.page_url).path.strip("/").split("/")
            if path:
                info["username"] = path[-1]
        except Exception:
            pass

        # ── DOM selectors ─────────────────────────────────────────────
        try:
            # Name via h1
            name_el = await self._page.query_selector('h1')
            if name_el:
                t = (await name_el.inner_text()).strip()
                if t:
                    info["name"] = t

            # Full page text for contacts
            page_text = await self._page.inner_text("body")

            emails = self.extract_emails(page_text)
            if emails:
                info["email"] = emails[0]

            phones = self.extract_phones(page_text)
            if phones:
                info["phone"] = phones[0]

            # Followers from visible text
            if info["followers"] == 0:
                f_m = re.search(r"([\d,\.]+[KkMm]?)\s+(?:people\s+)?followers?", page_text, re.I)
                if f_m:
                    info["followers"] = self._parse_count(f_m.group(1))

            # Likes from visible text
            if info["likes"] == 0:
                l_m = re.search(r"([\d,\.]+[KkMm]?)\s+(?:people\s+)?likes?", page_text, re.I)
                if l_m:
                    info["likes"] = self._parse_count(l_m.group(1))

            # Website via Facebook redirect links
            web_els = await self._page.query_selector_all('a[href*="l.facebook.com/l.php"]')
            for el in web_els:
                href = await el.get_attribute("href") or ""
                if "u=" in href:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if "u" in parsed:
                        info["website"] = parsed["u"][0]
                        break

            # Messenger link
            if info["name"]:
                slug = info["username"] or info["name"].lower().replace(" ", ".")
                info["messenger_link"] = f"https://m.me/{slug}"

        except Exception as e:
            self.log_warn(f"Facebook DOM extraction partial: {e}")

        return info

    # ------------------------------------------------------------------
    async def _extract_posts(self) -> list[dict]:
        posts = []
        try:
            for _ in range(5):
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self._page.wait_for_timeout(2000)
                if self._cancelled:
                    break

            # Broad article / role=article selectors
            post_els = await self._page.query_selector_all(
                '[role="article"], '
                'div[class*="x1yztbdb"][role="article"], '
                'div[data-ad-comet-preview="message"]'
            )

            for post_el in post_els[:self.max_posts]:
                try:
                    post = {}

                    # Text
                    for sel in [
                        'div[data-ad-comet-preview="message"]',
                        'div[class*="xdj266r"]',
                        'div[class*="x1iorvi4"]',
                        'span[class*="x193iq5w"]',
                    ]:
                        text_el = await post_el.query_selector(sel)
                        if text_el:
                            post["text"] = (await text_el.inner_text()).strip()
                            break
                    post.setdefault("text", "")

                    # Image
                    img_el = await post_el.query_selector('img[class*="x1ey2m1c"], img[class*="scaledImageFitWidth"]')
                    post["image"] = await img_el.get_attribute("src") if img_el else ""

                    # Timestamp
                    time_el = await post_el.query_selector('abbr[data-utime], time')
                    if time_el:
                        post["timestamp"] = (
                            await time_el.get_attribute("data-utime") or
                            await time_el.get_attribute("datetime") or ""
                        )
                    else:
                        post["timestamp"] = ""

                    # Reactions
                    react_el = await post_el.query_selector('[aria-label*="reaction"], span[class*="x1e558r4"]')
                    post["reactions"] = (await react_el.inner_text()).strip() if react_el else "0"

                    if post.get("text") or post.get("image"):
                        posts.append(post)

                except Exception:
                    continue

        except Exception as e:
            self.log_warn(f"Facebook post extraction failed: {e}")

        return posts

    # ------------------------------------------------------------------
    async def _extract_reviews(self) -> list[dict]:
        reviews = []
        try:
            reviews_url = self.page_url.rstrip("/") + "/reviews/"
            await self._goto(reviews_url, wait_until="domcontentloaded", timeout=30000)
            await self._page.wait_for_timeout(2000)
            await self._dismiss_overlays()

            review_els = await self._page.query_selector_all('[role="article"]')

            for rev_el in review_els[:30]:
                try:
                    review = {}

                    name_el = await rev_el.query_selector('a[role="link"] > span, h3')
                    review["reviewer"] = (await name_el.inner_text()).strip() if name_el else ""

                    rating_els = await rev_el.query_selector_all('[aria-label*="star"]')
                    review["rating"] = len(rating_els) if rating_els else None

                    text_el = await rev_el.query_selector('span[class*="x193iq5w"], div[class*="xdj266r"]')
                    review["text"] = (await text_el.inner_text()).strip() if text_el else ""

                    if review.get("reviewer") or review.get("text"):
                        reviews.append(review)

                except Exception:
                    continue

        except Exception as e:
            self.log_warn(f"Facebook reviews extraction failed: {e}")

        return reviews

    # ------------------------------------------------------------------
    async def _extract_events(self) -> list[dict]:
        events = []
        try:
            events_url = self.page_url.rstrip("/") + "/events/"
            await self._goto(events_url, wait_until="domcontentloaded", timeout=30000)
            await self._page.wait_for_timeout(2000)
            await self._dismiss_overlays()

            event_els = await self._page.query_selector_all('a[href*="/events/"]')

            for event_el in event_els[:20]:
                try:
                    event = {}
                    event["url"] = await event_el.get_attribute("href") or ""

                    title_el = await event_el.query_selector('span[class*="x1lliihq"], span, div')
                    event["title"] = (await title_el.inner_text()).strip() if title_el else ""

                    if event.get("title") and "/events/" in event.get("url", ""):
                        events.append(event)

                except Exception:
                    continue

        except Exception as e:
            self.log_warn(f"Facebook events extraction failed: {e}")

        return events

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_count(text: str) -> int:
        text = str(text).strip().replace(",", "").replace(".", "")
        try:
            upper = text.upper()
            if upper.endswith("M"):
                return int(float(upper[:-1]) * 1_000_000)
            elif upper.endswith("K"):
                return int(float(upper[:-1]) * 1_000)
            return int(text)
        except (ValueError, AttributeError):
            return 0
