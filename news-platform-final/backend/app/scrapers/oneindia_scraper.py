"""
OneIndia — English (oneindia.com) and Telugu (telugu.oneindia.com) editions.

English RSS feeds:
  - https://www.oneindia.com/rss/news-fb.xml (top stories)
  - https://www.oneindia.com/rss/india-fb.xml (India)
  - https://www.oneindia.com/rss/international-fb.xml

Telugu RSS:
  - https://telugu.oneindia.com/rss
  - https://telugu.oneindia.com/rss/category/telangana
  - https://telugu.oneindia.com/rss/category/andhra-pradesh
  - https://telugu.oneindia.com/rss/category/national
"""
import asyncio, functools, logging, feedparser, re
from datetime import datetime, timezone
from typing import List, Set, Dict, Optional
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory
from app.scrapers.scraper_utils import (
    normalize_url, is_excluded_url, extract_image, filter_content,
    fetch_with_retry, extract_date_from_text, validate_article,
    ArticleExtractor
)

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

logger = logging.getLogger(__name__)

ENG_FEEDS = [
    "https://www.oneindia.com/rss/news-fb.xml",
    "https://www.oneindia.com/rss/india-fb.xml",
    "https://www.oneindia.com/rss/international-fb.xml",
]
TEL_FEEDS = [
    "https://telugu.oneindia.com/rss/news-fb.xml",
    "https://telugu.oneindia.com/rss/category/telangana",
    "https://telugu.oneindia.com/rss/category/andhra-pradesh",
    "https://telugu.oneindia.com/rss/category/national",
]

# URL exclusion patterns
EXCLUDE_PATTERNS = [
    "/photo", "/video", "#", "javascript:", "/tag/", "/page/",
    "/gallery", "/epaper", "/convergence", "/aboutus", "/contactus"
]

# Date patterns specific to OneIndia
DATE_PATTERNS = [
    re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})"),
    re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})"),
]


def _sync_cloudscraper_get(url: str, max_retries: int = 2) -> Optional[str]:
    """Synchronous fetch using cloudscraper (runs in executor for async compat).

    cloudscraper handles Cloudflare JS challenges that cause 403s with
    plain aiohttp/requests.
    """
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False},
        delay=3,
    )
    for attempt in range(max_retries + 1):
        try:
            resp = scraper.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.text
            logger.warning(f"cloudscraper: HTTP {resp.status_code} for {url}")
        except Exception as e:
            logger.warning(f"cloudscraper: attempt {attempt+1} failed for {url}: {e}")
        if attempt < max_retries:
            import time
            time.sleep(2 * (attempt + 1))
    return None


class OneIndiaScraper(BaseScraper):
    """Dedicated OneIndia scraper — parses RSS feeds then fetches full article pages."""

    def __init__(self, source_config):
        super().__init__(source_config)
        self.max_articles = self.scraper_config.get("max_articles", 50)
        self.request_delay = self.scraper_config.get("request_delay", 0.5)
        self.max_retries = self.scraper_config.get("max_retries", 2)
        self.fetch_full_content = self.scraper_config.get("fetch_full_content", True)
        self.sequential_mode = self.scraper_config.get("sequential_mode", False)

        # Initialize article extractor
        self.extractor = ArticleExtractor(
            base_url="https://www.oneindia.com",
            content_selectors=[
                ".article-desc", ".content-txt", "#storyBody",
                ".article-body", ".ad-content-txt", ".post-content"
            ],
            image_selectors=[
                ".story-img img", ".article-image img", "article img",
                ".featured-image img", ".post-thumbnail img"
            ]
        )

    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL."""
        if not url or is_excluded_url(url, EXCLUDE_PATTERNS):
            return False
        # OneIndia specific pattern
        return "/" in url and len(url) > 30

    # Use cloudscraper to bypass Cloudflare JS challenges (403 errors).
    # cloudscraper is synchronous, so we run it in an executor to stay async-safe.
    async def _fetch_with_retry(self, url: str, *, for_rss: bool = False) -> Optional[str]:
        """Fetch URL, using cloudscraper to bypass Cloudflare 403s."""
        if cloudscraper is None:
            logger.warning("cloudscraper not installed — falling back to plain fetch "
                           "(pip install cloudscraper)")
            return await fetch_with_retry(self, url, self.max_retries, self.request_delay)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            functools.partial(_sync_cloudscraper_get, url, self.max_retries),
        )
        return result

    async def _process_rss_entry(self, entry, seen: Set[str]) -> Optional[ScrapedArticle]:
        """Process a single RSS entry."""
        link = entry.get("link", "")
        if not link or link in seen:
            return None

        seen.add(link)
        title = entry.get("title", "")
        if not title or len(title) < 5:
            return None

        # Parse date
        pub_date = None
        for attr in ("published_parsed", "updated_parsed"):
            p = getattr(entry, attr, None)
            if p:
                pub_date = datetime(*p[:6], tzinfo=timezone.utc)
                break

        # Extract summary
        summary = entry.get("summary", "")
        if summary:
            summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)

        # Extract image
        image_url = None
        for attr in ("media_content", "media_thumbnail"):
            m = getattr(entry, attr, None)
            if m:
                image_url = m[0].get("url")
                break

        # Fetch full content
        content = summary
        if self.fetch_full_content and link:
            html = await self._fetch_with_retry(link)  # HTML page, not RSS
            if html:
                soup = self.parse_html(html)
                extracted = self.extractor.extract_content(soup, title)
                if len(extracted) > len(summary or ""):
                    content = extracted
                if not image_url:
                    image_url = self.extractor.extract_image(soup)

        # newspaper3k fallback
        if not content or len(content) < 80:
            result = await self.extractor.extract_with_newspaper3k(link)
            if result.get("success") and len(result.get("content", "")) > len(content or ""):
                content = result["content"]
                if not image_url and result.get("image_url"):
                    image_url = result["image_url"]

        return ScrapedArticle(
            title=title,
            content=content or "",
            url=link,
            published_at=pub_date or datetime.now(timezone.utc),
            image_url=image_url,
            author="OneIndia"
        )

    def _extract_links_from_html(self, soup, seen: Set[str], base_url: str) -> List[Dict]:
        """Extract article links from HTML page."""
        articles = []

        # Look for article containers with specific classes
        article_containers = soup.find_all("div", class_=["oi-article-thumb"])

        for container in article_containers:
            a_tag = container.find("a", href=True)
            if not a_tag:
                continue

            href = a_tag.get("href", "")
            if not href or href in seen:
                continue

            # Normalize URL
            if href.startswith("/"):
                href = base_url + href
            elif not href.startswith("http"):
                continue

            # OneIndia specific URL pattern
            if not self._is_valid_article_url(href):
                continue

            seen.add(href)

            # Extract title
            title_tag = container.find("a", class_="oiHyperLink")
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                title = container.find("a").get_text(strip=True)

            if not title or len(title) < 10:
                continue

            # Extract image
            img_tag = container.find("img")
            image_url = img_tag.get("src") if img_tag else None

            # Extract summary from hover text
            hover_div = container.find("div", class_="hover-text")
            summary = hover_div.get_text(strip=True) if hover_div else ""

            # Extract published date
            published_at = None
            date_tag = container.find("div", class_="oi-article-title")
            if date_tag:
                date_text = date_tag.get_text(strip=True)
                published_at = extract_date_from_text(date_text, DATE_PATTERNS)

            articles.append({
                "url": href,
                "title": title,
                "image_url": image_url,
                "summary": summary,
                "published_at": published_at,
            })

        return articles

    async def _process_html_article(self, article_data: Dict) -> Optional[ScrapedArticle]:
        """Process article from HTML scraping."""
        url = article_data["url"]
        title = article_data["title"]

        if not self.fetch_full_content:
            return ScrapedArticle(
                title=title,
                content=article_data.get("summary", ""),
                url=url,
                published_at=article_data.get("published_at") or datetime.now(timezone.utc),
                image_url=article_data.get("image_url"),
                author="OneIndia"
            )

        html = await self._fetch_with_retry(url)
        if not html:
            return None

        soup = self.parse_html(html)
        content = self.extractor.extract_content(soup, title)
        image_url = self.extractor.extract_image(soup) or article_data.get("image_url")

        # newspaper3k fallback
        if not content or len(content) < 80:
            result = await self.extractor.extract_with_newspaper3k(url, html)
            if result.get("success"):
                content = result["content"]
                if not image_url and result.get("image_url"):
                    image_url = result["image_url"]

        return ScrapedArticle(
            title=title,
            content=content or "",
            url=url,
            published_at=article_data.get("published_at") or datetime.now(timezone.utc),
            image_url=image_url,
            author="OneIndia"
        )

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        is_telugu = "telugu" in self.source_name.lower() or self.language == "te"
        base_url = "https://telugu.oneindia.com" if is_telugu else "https://www.oneindia.com"
        tag = "ONEINDIA-TE" if is_telugu else "ONEINDIA-EN"

        # Try RSS first, fallback to HTML scraping
        feeds = TEL_FEEDS if is_telugu else ENG_FEEDS
        logger.info(f"[{tag}] Starting RSS scrape from {len(feeds)} feeds")

        rss_success = False
        for feed_url in feeds:
            if len(articles) >= self.max_articles:
                break

            try:
                # --- FIX: Pass for_rss=True so the Accept header is XML ---
                xml = await self._fetch_with_retry(feed_url, for_rss=True)
                if not xml:
                    continue

                feed = feedparser.parse(xml)
                logger.info(f"[{tag}] {feed_url.split('/')[-1]}: {len(feed.entries)} entries")

                for entry in feed.entries:
                    if len(articles) >= self.max_articles:
                        break

                    article = await self._process_rss_entry(entry, seen)
                    if article and article.is_valid():
                        articles.append(article)
                        rss_success = True

                    if not self.sequential_mode:
                        await asyncio.sleep(self.request_delay)

            except Exception as e:
                logger.warning(f"[{tag}] Feed error for {feed_url}: {e}")

        # If RSS fails, try HTML scraping
        if not rss_success or len(articles) == 0:
            logger.info(f"[{tag}] RSS failed, trying HTML scraping")

            # Define sections to scrape
            if is_telugu:
                sections = ["/", "/telangana", "/andhra-pradesh", "/national", "/sports", "/movies"]
            else:
                sections = ["/", "/india", "/international", "/sports", "/entertainment"]

            for section in sections:
                if len(articles) >= self.max_articles:
                    break

                url = f"{base_url}{section}" if section else base_url
                html = await self._fetch_with_retry(url)
                if not html:
                    continue

                soup = self.parse_html(html)
                article_links = self._extract_links_from_html(soup, seen, base_url)

                logger.info(f"[{tag}] Section {section}: found {len(article_links)} articles")

                for article_data in article_links:
                    if len(articles) >= self.max_articles:
                        break

                    article = await self._process_html_article(article_data)
                    if article and article.is_valid():
                        articles.append(article)

                    if not self.sequential_mode:
                        await asyncio.sleep(self.request_delay)

                await asyncio.sleep(self.request_delay)

        logger.info(f"[{tag}] Scraped {len(articles)} articles total")
        return articles


ScraperFactory.register("oneindia english", OneIndiaScraper)
ScraperFactory.register("oneindia telugu", OneIndiaScraper)