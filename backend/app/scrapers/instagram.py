"""
Instagram Profile Scraper using Playwright.
Extracts profile data (followers, following, posts count), posts, captions, hashtags.

Strategy:
  1. Navigate to the profile page.
  2. Try to read embedded JSON data (window._sharedData / __additionalDataLoaded).
  3. Fall back to reading visible page text / aria labels for stats.
  4. Collect post URLs from the grid, then scrape each post's meta tags.
"""

import json
import re
from typing import Callable, Optional

from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper


class InstagramScraper(BaseScraper):
    """Scrapes Instagram public profile pages."""

    def __init__(self, job_id: str, url: str, config: dict,
                 progress_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        super().__init__(job_id, config, progress_callback, log_callback)
        self.profile_url = self._normalize_instagram_url(url)
        self.max_posts = config.get("max_posts", 50)
        self.download_media = config.get("download_media", False)
        self.include_reels = config.get("include_reels", True)

    # ------------------------------------------------------------------
    # URL normalisation
    # ------------------------------------------------------------------
    def _normalize_instagram_url(self, url: str) -> str:
        """Accept a username, @username, or full URL and return a proper profile URL."""
        url = url.strip()
        if url.startswith("@"):
            url = url[1:]
        if "instagram.com/" not in url:
            # Treat the input as a raw username
            return f"https://www.instagram.com/{url}/"
        url = url.rstrip("/") + "/"
        return url

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    async def run(self) -> dict:
        """Scrape Instagram profile."""
        self.log_info("Starting Instagram scraper", url=self.profile_url)
        try:
            await self._init_browser()
            await self._goto(self.profile_url, wait_until="networkidle", timeout=60000)
            await self._page.wait_for_timeout(4000)

            profile = await self._extract_profile_data()
            posts = await self._extract_posts()
            profile["posts"] = posts
            self.progress.update(items_delta=len(posts))

            self.log_info(
                f"Instagram: @{profile.get('username')} | "
                f"Followers: {profile.get('followers')} | "
                f"Following: {profile.get('following')} | "
                f"Posts count: {profile.get('posts_count')}"
            )
            return profile

        except Exception as e:
            self.log_error(f"Instagram scrape failed: {e}", url=self.profile_url)
            return {"error": str(e), "url": self.profile_url}
        finally:
            await self._close_browser()

    # ------------------------------------------------------------------
    # Profile data extraction
    # ------------------------------------------------------------------
    async def _extract_profile_data(self) -> dict:
        """Extract profile metadata from the page using multiple strategies."""
        profile = {
            "profile_url": self.profile_url,
            "username": "",
            "display_name": "",
            "bio": "",
            "followers": 0,
            "following": 0,
            "posts_count": 0,
            "profile_picture": "",
            "external_link": "",
            "email": "",
            "business_category": "",
            "verified": False,
            "is_private": False,
        }

        html = await self._page.content()
        soup = BeautifulSoup(html, "lxml")

        # ── 1. Meta / OG tags ──────────────────────────────────────────
        og_url = soup.find("meta", property="og:url")
        if og_url:
            parts = og_url.get("content", "").strip("/").split("/")
            if parts:
                profile["username"] = parts[-1]

        og_image = soup.find("meta", property="og:image")
        if og_image:
            profile["profile_picture"] = og_image.get("content", "")

        # og:description often contains "X Followers, X Following, X Posts"
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            desc_text = og_desc.get("content", "")
            self.log_info(f"og:description: {desc_text[:120]}")
            f_match = re.search(r"([\d,\.]+[KkMm]?)\s+Followers?", desc_text, re.I)
            fw_match = re.search(r"([\d,\.]+[KkMm]?)\s+Following", desc_text, re.I)
            p_match = re.search(r"([\d,\.]+[KkMm]?)\s+Posts?", desc_text, re.I)
            if f_match:
                profile["followers"] = self._parse_count(f_match.group(1))
            if fw_match:
                profile["following"] = self._parse_count(fw_match.group(1))
            if p_match:
                profile["posts_count"] = self._parse_count(p_match.group(1))

        # Page title: "Display Name (@username) • Posts"
        title_tag = soup.find("title")
        if title_tag:
            t = title_tag.get_text()
            un_m = re.search(r"@([\w.]+)", t)
            if un_m:
                profile["username"] = un_m.group(1)

        # ── 2. Embedded JSON (window._sharedData) ─────────────────────
        shared_data_match = re.search(
            r'<script[^>]*>\s*window\._sharedData\s*=\s*({.+?});\s*</script>',
            html, re.DOTALL
        )
        if shared_data_match:
            try:
                data = json.loads(shared_data_match.group(1))
                user = (
                    data.get("entry_data", {})
                    .get("ProfilePage", [{}])[0]
                    .get("graphql", {})
                    .get("user", {})
                )
                if user:
                    self.log_info("Loaded profile from window._sharedData")
                    profile.update(self._parse_user_graphql(user))
            except Exception as e:
                self.log_warn(f"_sharedData parse failed: {e}")

        # ── 3. Alternative JSON blobs ──────────────────────────────────
        for pattern in [
            r'"edge_followed_by"\s*:\s*\{"count"\s*:\s*(\d+)\}',
            r'"follower_count"\s*:\s*(\d+)',
        ]:
            m = re.search(pattern, html)
            if m and profile["followers"] == 0:
                profile["followers"] = int(m.group(1))

        for pattern in [
            r'"edge_follow"\s*:\s*\{"count"\s*:\s*(\d+)\}',
            r'"following_count"\s*:\s*(\d+)',
        ]:
            m = re.search(pattern, html)
            if m and profile["following"] == 0:
                profile["following"] = int(m.group(1))

        for pattern in [
            r'"edge_owner_to_timeline_media"\s*:\s*\{"count"\s*:\s*(\d+)\}',
            r'"media_count"\s*:\s*(\d+)',
        ]:
            m = re.search(pattern, html)
            if m and profile["posts_count"] == 0:
                profile["posts_count"] = int(m.group(1))

        # ── 4. Playwright DOM selectors (visible page elements) ────────
        try:
            # Stats row — Instagram renders 3 <li> items: posts / followers / following
            # The actual number is inside a <span> with a title attribute OR aria-label
            stat_spans = await self._page.query_selector_all(
                'ul li span[class] > span, header section ul li span'
            )
            stat_values = []
            for sp in stat_spans:
                t = (await sp.inner_text()).strip()
                if t:
                    stat_values.append(self._parse_count(t))

            self.log_info(f"DOM stat spans raw values: {stat_values}")

            if len(stat_values) >= 3 and profile["posts_count"] == 0:
                profile["posts_count"] = stat_values[0]
                profile["followers"] = stat_values[1]
                profile["following"] = stat_values[2]

            # Try title attributes on the spans (Instagram sometimes puts the full number there)
            stat_title_spans = await self._page.query_selector_all(
                'ul li span[title], header section ul li span[title]'
            )
            titled_vals = []
            for sp in stat_title_spans:
                t = await sp.get_attribute("title") or ""
                if t:
                    titled_vals.append(self._parse_count(t.replace(",", "")))

            self.log_info(f"DOM title attr values: {titled_vals}")
            if len(titled_vals) >= 3:
                profile["posts_count"] = titled_vals[0]
                profile["followers"] = titled_vals[1]
                profile["following"] = titled_vals[2]

            # Display name
            name_candidates = await self._page.query_selector_all(
                'h1, header h2, section h1, section h2'
            )
            for el in name_candidates:
                t = (await el.inner_text()).strip()
                if t and t != profile.get("username"):
                    profile["display_name"] = t
                    break

            # Bio
            bio_el = await self._page.query_selector(
                'header section > div > span, header section > div[class] span[class]'
            )
            if bio_el:
                bio_text = (await bio_el.inner_text()).strip()
                if bio_text:
                    profile["bio"] = bio_text

            # Email from bio
            full_bio = profile.get("bio", "")
            if full_bio:
                emails = self.extract_emails(full_bio)
                if emails:
                    profile["email"] = emails[0]

            # Verified badge
            verified_el = await self._page.query_selector(
                '[title="Verified"], [aria-label*="Verified"], svg[aria-label*="Verified"]'
            )
            profile["verified"] = verified_el is not None

            # Private account flag
            private_text = await self._page.query_selector('text=This Account is Private')
            profile["is_private"] = private_text is not None

            # External link
            link_els = await self._page.query_selector_all(
                'a[href^="https://l.instagram.com/?u="], '
                'a[rel="nofollow noopener noreferrer"][target="_blank"]'
            )
            for link_el in link_els:
                href = await link_el.get_attribute("href") or ""
                if href and "instagram.com" not in href:
                    profile["external_link"] = href
                    break

        except Exception as e:
            self.log_warn(f"DOM selector extraction partial failure: {e}")

        return profile

    # ------------------------------------------------------------------
    # GraphQL user parser
    # ------------------------------------------------------------------
    def _parse_user_graphql(self, user: dict) -> dict:
        return {
            "username": user.get("username", ""),
            "display_name": user.get("full_name", ""),
            "bio": user.get("biography", ""),
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts_count": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "profile_picture": user.get("profile_pic_url_hd") or user.get("profile_pic_url", ""),
            "external_link": user.get("external_url", ""),
            "verified": user.get("is_verified", False),
            "is_private": user.get("is_private", False),
            "business_category": user.get("business_category_name", ""),
        }

    # ------------------------------------------------------------------
    # Post extraction
    # ------------------------------------------------------------------
    async def _extract_posts(self) -> list[dict]:
        """Extract recent posts and reels from the profile grid."""
        posts = []
        try:
            # Scroll to load posts
            scroll_rounds = min(self.max_posts // 12 + 1, 6)
            for _ in range(scroll_rounds):
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self._page.wait_for_timeout(2000)
                if self._cancelled:
                    break

            # Collect post URLs from the grid
            post_links = await self._page.query_selector_all('a[href*="/p/"]')
            post_urls = []
            seen = set()
            for link in post_links:
                href = await link.get_attribute("href") or ""
                if "/p/" in href and href not in seen:
                    seen.add(href)
                    post_urls.append(href)

            # If enabled, also scrape Reels
            if self.include_reels:
                reel_links = await self._page.query_selector_all('a[href*="/reel/"]')
                self.log_info(f"Found {len(reel_links)} Reel links on grid")
                for link in reel_links:
                    href = await link.get_attribute("href") or ""
                    if "/reel/" in href and href not in seen:
                        seen.add(href)
                        post_urls.append(href)

            self.log_info(f"Found {len(post_urls)} total post/reel links on profile grid")

            for post_href in post_urls[:self.max_posts]:
                if self._cancelled:
                    break
                post_url = f"https://www.instagram.com{post_href}" if post_href.startswith("/") else post_href
                post_data = await self._scrape_post(post_url)
                if post_data:
                    posts.append(post_data)
                await self._delay(extra_ms=500)

        except Exception as e:
            self.log_error(f"Post extraction failed: {e}")

        return posts

    async def _scrape_post(self, post_url: str) -> Optional[dict]:
        """Scrape individual post via its meta tags."""
        try:
            post_page = await self._context.new_page()
            await post_page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await post_page.wait_for_timeout(1500)

            html = await post_page.content()
            soup = BeautifulSoup(html, "lxml")

            post = {"url": post_url}

            og_desc = soup.find("meta", property="og:description")
            caption = og_desc.get("content", "") if og_desc else ""
            post["caption"] = caption
            post["hashtags"] = re.findall(r"#(\w+)", caption)

            og_image = soup.find("meta", property="og:image")
            post["image_url"] = og_image.get("content", "") if og_image else ""

            og_type = soup.find("meta", property="og:type")
            post["type"] = og_type.get("content", "image") if og_type else "image"

            # Parse likes and comments count from meta description text if available
            post["likes"] = 0
            post["comments"] = 0
            if og_desc:
                desc_val = og_desc.get("content", "")
                likes_match = re.search(r"([\d,\.]+[KkMm]?)\s+Likes", desc_val, re.I)
                comments_match = re.search(r"([\d,\.]+[KkMm]?)\s+Comments", desc_val, re.I)
                if likes_match:
                    post["likes"] = self._parse_count(likes_match.group(1))
                if comments_match:
                    post["comments"] = self._parse_count(comments_match.group(1))

            # Scrape post published timestamp
            post["timestamp"] = ""
            time_el = soup.find("time")
            if time_el and time_el.get("datetime"):
                post["timestamp"] = time_el.get("datetime")
            else:
                meta_date = soup.find("meta", property="article:published_time") \
                            or soup.find("meta", itemprop="uploadDate") \
                            or soup.find("meta", itemprop="datePublished")
                if meta_date:
                    post["timestamp"] = meta_date.get("content", "")

            await post_page.close()
            return post

        except Exception as e:
            self.log_warn(f"Could not scrape post {post_url}: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_count(text: str) -> int:
        """Parse '1.2M', '15K', '1,234', '1.2k' style counts to integer."""
        text = str(text).strip().replace(",", "").replace("\u202f", "").replace("\xa0", "")
        try:
            upper = text.upper()
            if "M" in upper:
                return int(float(upper.replace("M", "")) * 1_000_000)
            elif "K" in upper:
                return int(float(upper.replace("K", "")) * 1_000)
            return int(float(text))
        except (ValueError, AttributeError):
            return 0
