"""
Google Maps Review Scraper using Playwright.
Extracts business info, rating, all reviews with pagination, owner replies.

Strategy:
  - Navigate directly to the Google Maps /place/ URL (no conversion to /search/).
  - Wait robustly for the detail panel (h1 + F7nice rating container + Reviews tab).
  - Click the "Reviews" tab with JS-level click to bypass overlays.
  - Scroll the review feed container and extract every review card.
"""

import re
from typing import Callable, Optional

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper


class GoogleMapsScraper(BaseScraper):
    """Scrapes Google Maps business pages for info and reviews."""

    SORT_MODES = {
        "newest": 1,
        "highest": 3,
        "lowest": 4,
        "relevant": 0,
    }

    def __init__(self, job_id: str, url: str, config: dict,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        super().__init__(job_id, config, progress_callback, log_callback)
        self.maps_url = self._clean_maps_url(url)
        self.max_reviews = config.get("max_reviews", 100)
        self.sort_order = config.get("sort_order", "newest")

    # ------------------------------------------------------------------
    # URL cleaning — keep /place/ URLs as-is; only strip junk params
    # ------------------------------------------------------------------
    def _clean_maps_url(self, url: str) -> str:
        """Return a clean Maps URL. Keep /place/ URLs directly — do NOT convert
        to /search/ because that skips the detail panel rendering."""
        url = url.strip()
        # If someone passes a plain business name or query, convert to search
        if not url.startswith("http"):
            from urllib.parse import quote
            return f"https://www.google.com/maps/search/{quote(url)}"
        self.log_info(f"Using Maps URL: {url}")
        return url

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------
    async def run(self) -> dict:
        """Scrape business info and all reviews."""
        self.log_info("Starting Google Maps scraper", url=self.maps_url)
        try:
            await self._init_browser()
            await self._goto(self.maps_url, wait_until="load", timeout=60000)

            # ── Handle cookie / consent overlay ───────────────────────
            try:
                for sel in [
                    'form[action*="consent.google"] button',
                    'button[aria-label*="Accept all"]',
                    'button[aria-label*="Agree"]',
                ]:
                    btn = await self._page.query_selector(sel)
                    if btn:
                        self.log_info("Dismissing consent banner")
                        await btn.evaluate("el => el.click()")
                        await self._page.wait_for_timeout(2500)
                        break
            except Exception as e:
                self.log_warn(f"Consent handling: {e}")

            # ── Handle search list page (multiple results or search listing) ──
            if "/maps/search/" in self._page.url or "search" in self._page.url:
                self.log_info("Search results list page detected. Looking for place cards...")
                try:
                    for _ in range(10):
                        cards = await self._page.query_selector_all('a[href*="/maps/place/"]') \
                                or await self._page.query_selector_all('a[class*="hfpxzc"]')
                        if cards:
                            card = cards[0]
                            label = await card.get_attribute("aria-label") or "first place card"
                            self.log_info(f"Clicking first search result: {label}")
                            await card.evaluate("el => el.click()")
                            await self._page.wait_for_timeout(3000)
                            break
                        await self._page.wait_for_timeout(500)
                except Exception as e:
                    self.log_warn(f"Error handling search list results: {e}")

            # ── Wait for the business name (h1) to appear ─────────────
            self.log_info("Waiting for business name heading…")
            try:
                for _ in range(60):           # up to 30 s
                    el = await self._page.query_selector('h1[class*="DUwDvf"]') \
                         or await self._page.query_selector('h1')
                    if el and (await el.inner_text()).strip():
                        break
                    await self._page.wait_for_timeout(500)
            except Exception:
                pass

            # ── Wait for rating or Reviews tab ────────────────────────
            self.log_info("Waiting for rating / Reviews tab…")
            try:
                for _ in range(30):           # up to 15 s
                    rating_el = await self._page.query_selector('div[class*="F7nice"]')
                    tab_el = await self._page.query_selector('button[aria-label*="Reviews"]')
                    if rating_el or tab_el:
                        break
                    await self._page.wait_for_timeout(500)
            except Exception:
                pass

            # Short safety buffer for remaining JS rendering
            await self._page.wait_for_timeout(2000)

            # ── Extract metadata ──────────────────────────────────────
            business_info = await self._extract_business_info()
            self.log_info(
                f"Business: {business_info.get('name')} | "
                f"Rating: {business_info.get('rating')} | "
                f"Total reviews: {business_info.get('total_reviews')}"
            )

            # ── Scrape reviews ────────────────────────────────────────
            reviews = await self._scrape_reviews()
            business_info["reviews"] = reviews
            self.progress.update(items_delta=len(reviews))
            self.log_info(f"Collected {len(reviews)} reviews.")

            return business_info

        except Exception as e:
            self.log_error(f"Google Maps scrape failed: {e}", url=self.maps_url)
            raise
        finally:
            await self._close_browser()

    # ------------------------------------------------------------------
    # Business metadata
    # ------------------------------------------------------------------
    async def _extract_business_info(self) -> dict:
        """Extract all business metadata from the Maps detail panel."""
        result = {
            "name": "",
            "category": "",
            "rating": None,
            "total_reviews": 0,
            "address": "",
            "phone": "",
            "website": "",
            "maps_url": self._page.url,
            "opening_hours": {},
            "coordinates": {},
            "photos": [],
        }

        # Name
        try:
            el = await self._page.query_selector('h1[class*="DUwDvf"]') \
                 or await self._page.query_selector('h1')
            if el:
                result["name"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Rating + review count from F7nice container
        # Typical inner_text: "4.3\n(12)" or "4,3\n(1 234)" etc.
        try:
            container = await self._page.query_selector('div[class*="F7nice"]')
            if container:
                text = await container.inner_text()
                self.log_info(f"F7nice text: {repr(text)}")

                rating_m = re.search(r"(\d[\.,]\d)", text)
                if rating_m:
                    result["rating"] = float(rating_m.group(1).replace(",", "."))

                # Remove the rating portion and pull out remaining digits for review count
                cleaned = text
                if rating_m:
                    cleaned = cleaned.replace(rating_m.group(1), "")
                nums = re.findall(r"[\d,\u202f\xa0]+", cleaned)
                if nums:
                    raw = nums[0].replace(",", "").replace("\u202f", "").replace("\xa0", "")
                    result["total_reviews"] = int(raw) if raw.isdigit() else 0
        except Exception as e:
            self.log_warn(f"Rating/reviews parse error: {e}")

        # Fallback via aria-label span
        if result["total_reviews"] == 0:
            try:
                for sel in [
                    'div[class*="F7nice"] span[aria-label]',
                    'span[aria-label*="review"]',
                    'span[aria-label*="reviews"]',
                ]:
                    el = await self._page.query_selector(sel)
                    if el:
                        aria = await el.get_attribute("aria-label") or await el.inner_text()
                        nums = re.findall(r"[\d,]+", aria)
                        if nums:
                            result["total_reviews"] = int(nums[0].replace(",", ""))
                        break
            except Exception:
                pass

        # Address
        try:
            el = await self._page.query_selector('button[data-item-id="address"]')
            if el:
                result["address"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Phone
        try:
            el = await self._page.query_selector('button[data-item-id*="phone"]')
            if el:
                result["phone"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Website
        try:
            el = await self._page.query_selector('a[data-item-id="authority"]')
            if el:
                result["website"] = await el.get_attribute("href") or ""
        except Exception:
            pass

        # Category
        try:
            el = await self._page.query_selector('button[class*="DkEaL"]')
            if not el:
                el = await self._page.query_selector('span[class*="mgr77e"]')
            if el:
                result["category"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Coordinates from current URL
        url = self._page.url
        m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if m:
            result["coordinates"] = {
                "lat": float(m.group(1)),
                "lng": float(m.group(2)),
            }

        # Opening hours
        try:
            rows = await self._page.query_selector_all('tr[class*="y0skZc"]')
            hours = {}
            for row in rows:
                day_el = await row.query_selector("td:first-child")
                time_el = await row.query_selector("td:last-child")
                if day_el and time_el:
                    hours[(await day_el.inner_text()).strip()] = (await time_el.inner_text()).strip()
            result["opening_hours"] = hours
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
    async def _scrape_reviews(self) -> list[dict]:
        """Click the Reviews tab and collect all visible reviews."""
        reviews = []
        try:
            # Find the Reviews tab
            reviews_tab = None
            for sel in [
                'button[aria-label*="Reviews"]',
                'button[aria-label*="reviews"]',
                'button[jsaction*="pane.rating.moreReviews"]',
            ]:
                reviews_tab = await self._page.query_selector(sel)
                if reviews_tab:
                    break

            if not reviews_tab:
                # Scan all role=tab buttons for text containing "review"
                for btn in await self._page.query_selector_all('button[role="tab"]'):
                    t = (await btn.inner_text()).strip().lower()
                    if "review" in t:
                        reviews_tab = btn
                        break

            if reviews_tab:
                label = (await reviews_tab.inner_text()).strip()
                self.log_info(f"Clicking Reviews tab: '{label}'")
                await reviews_tab.evaluate("el => el.click()")
                await self._page.wait_for_timeout(3000)
            else:
                self.log_warn("Reviews tab not found — attempting to proceed anyway.")

            # Sort reviews
            await self._sort_reviews()

            # Find the scrollable review feed
            scrollable = None
            for sel in [
                'div[class*="dS8AEf"]',
                'div[role="feed"]',
                'div[class*="m6QErb"]',
            ]:
                scrollable = await self._page.query_selector(sel)
                if scrollable:
                    self.log_info(f"Scroll container found via: {sel}")
                    break

            last_count = 0
            stale_rounds = 0

            while len(reviews) < self.max_reviews and stale_rounds < 8:
                if self._cancelled:
                    break

                if scrollable:
                    await scrollable.evaluate("el => el.scrollTop = el.scrollHeight")
                else:
                    await self._page.keyboard.press("End")

                await self._page.wait_for_timeout(2500)

                # Expand "More" buttons (truncated reviews)
                for sel in [
                    'button[aria-label="See more"]',
                    'button[class*="kyuRq"]',
                    'button[jsaction*="pane.review.expandReview"]',
                ]:
                    btns = await self._page.query_selector_all(sel)
                    for btn in btns:
                        try:
                            await btn.evaluate("el => el.click()")
                            await self._page.wait_for_timeout(150)
                        except Exception:
                            pass

                current = await self._extract_reviews_from_page()
                self.log_info(f"Scroll round: {len(current)} reviews visible in DOM")

                if len(current) <= last_count:
                    stale_rounds += 1
                else:
                    stale_rounds = 0
                    last_count = len(current)

                reviews = current
                self.progress.update(items_delta=0)

        except Exception as e:
            self.log_error(f"Review scrape error: {e}")

        return reviews[:self.max_reviews]

    async def _sort_reviews(self):
        """Apply the chosen sort order."""
        try:
            sort_btn = await self._page.query_selector('button[aria-label*="Sort reviews"]')
            if not sort_btn:
                sort_btn = await self._page.query_selector('button[data-value*="sort"]')
            if not sort_btn:
                # Scan buttons for sort text
                for btn in await self._page.query_selector_all("button"):
                    t = (await btn.inner_text()).strip().lower()
                    if "sort" in t:
                        sort_btn = btn
                        break

            if sort_btn:
                self.log_info("Clicking sort button…")
                await sort_btn.evaluate("el => el.click()")
                await self._page.wait_for_timeout(1200)

                sort_mode = self.SORT_MODES.get(self.sort_order, 1)
                menu_items = await self._page.query_selector_all('[role="menuitemradio"]')
                self.log_info(f"{len(menu_items)} sort menu items found, picking index {sort_mode}")
                if sort_mode < len(menu_items):
                    await menu_items[sort_mode].evaluate("el => el.click()")
                    await self._page.wait_for_timeout(2000)
            else:
                self.log_warn("Sort button not found.")
        except Exception as e:
            self.log_warn(f"Could not sort reviews: {e}")

    async def _extract_reviews_from_page(self) -> list[dict]:
        """Parse every review card currently rendered in the DOM."""
        reviews = []

        # Primary: divs that carry data-review-id
        cards = await self._page.query_selector_all('div[data-review-id]')
        if not cards:
            cards = await self._page.query_selector_all('div[class*="jftiEf"]')
        if not cards:
            cards = await self._page.query_selector_all('div[class*="jJc9Ad"]')

        for card in cards:
            try:
                review: dict = {}

                # Reviewer name
                name_el = (
                    await card.query_selector('div[class*="d4r55"]') or
                    await card.query_selector('div[class*="W3g53d"]') or
                    await card.query_selector('button[class*="al6Kxe"]')
                )
                review["reviewer_name"] = (await name_el.inner_text()).strip() if name_el else ""

                # Profile URL
                profile_btn = await card.query_selector('button[data-href]')
                if profile_btn:
                    review["reviewer_profile"] = await profile_btn.get_attribute("data-href") or ""
                else:
                    profile_a = await card.query_selector('a[class*="al6Kxe"]')
                    review["reviewer_profile"] = (
                        await profile_a.get_attribute("href") if profile_a else ""
                    )

                # Reviewer photo
                photo_el = await card.query_selector('img[class*="NBa7we"]')
                review["reviewer_photo"] = await photo_el.get_attribute("src") if photo_el else ""

                # Star rating
                rating_el = (
                    await card.query_selector('span[class*="kvMYJc"]') or
                    await card.query_selector('span[aria-label*="star"]') or
                    await card.query_selector('[role="img"][aria-label*="star"]')
                )
                if rating_el:
                    aria = await rating_el.get_attribute("aria-label") or ""
                    m = re.search(r"(\d+)\s*star", aria, re.I)
                    if m:
                        review["rating"] = int(m.group(1))
                    else:
                        m2 = re.search(r"\d+", aria)
                        review["rating"] = int(m2.group(0)) if m2 else None

                # Review text
                text_el = await card.query_selector('span[class*="wiI7pd"]')
                review["text"] = (await text_el.inner_text()).strip() if text_el else ""

                # Date
                date_el = (
                    await card.query_selector('span[class*="rsqaWe"]') or
                    await card.query_selector('div[class*="DU9Pgb"]')
                )
                review["review_date"] = (await date_el.inner_text()).strip() if date_el else ""

                # Owner reply
                reply_el = await card.query_selector('div[class*="CDe7pd"]')
                if reply_el:
                    reply_text_el = await reply_el.query_selector('div[class*="wiI7pd"]')
                    reply_date_el = await reply_el.query_selector('span[class*="DZSIDd"]')
                    review["owner_reply"] = (
                        (await reply_text_el.inner_text()).strip() if reply_text_el else ""
                    )
                    review["owner_reply_date"] = (
                        (await reply_date_el.inner_text()).strip() if reply_date_el else ""
                    )

                # Images attached to review
                imgs = await card.query_selector_all('img[class*="YQ4gaf"]')
                review["images"] = [await img.get_attribute("src") for img in imgs]

                if review.get("reviewer_name") or review.get("text"):
                    reviews.append(review)

            except Exception:
                continue

        return reviews
