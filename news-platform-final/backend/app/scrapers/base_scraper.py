"""
Base scraper module and scraper factory.
All scrapers inherit from BaseScraper and implement the scrape() method.
"""

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import httpx
import feedparser
from bs4 import BeautifulSoup
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScrapedArticle:
    """Represents a single scraped article."""

    def __init__(
        self,
        title: str,
        content: str = "",
        url: str = "",
        published_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.title = title.strip() if title else ""
        self.content = content.strip() if content else ""
        self.url = url.strip() if url else ""
        self.published_at = published_at
        self.image_url = image_url
        self.author = author
        self.metadata = metadata or {}

    @property
    def content_hash(self) -> str:
        """Generate unique hash for duplicate detection."""
        raw = f"{self.title}|{self.url}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_valid(self) -> bool:
        """Check if article has minimum required data."""
        return bool(self.title and len(self.title) > 5)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, source_config: Dict[str, Any]):
        self.config = source_config
        self.source_name = source_config.get("name", "Unknown")
        self.base_url = source_config.get("url", "")
        self.language = source_config.get("language", "en")
        self.scraper_config = source_config.get("scraper_config", {})
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5,te;q=0.3",
        }
        self.timeout = settings.SCRAPE_TIMEOUT

    async def fetch_url(self, url: str) -> Optional[str]:
        """Fetch content from URL with error handling."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching {url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} fetching {url}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content."""
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    async def scrape(self) -> List[ScrapedArticle]:
        """Scrape articles from source. Must be implemented by subclasses."""
        pass


class RSSScaper(BaseScraper):
    """Generic RSS scraper — parses feed then fetches FULL article via newspaper3k.

    This is the default scraper for NDTV, The Hindu, TOI, Indian Express, ANI,
    BBC India, Reuters, Samayam Telugu, and any other RSS source.
    """

    async def scrape(self) -> List[ScrapedArticle]:
        rss_url = self.scraper_config.get("rss_url", self.base_url)
        fetch_full = self.scraper_config.get("fetch_full_content", True)
        max_arts = self.scraper_config.get("max_articles", settings.MAX_ARTICLES_PER_SCRAPE)
        articles = []

        logger.info(f"[{self.source_name}] Scraping RSS: {rss_url}")
        raw = await self.fetch_url(rss_url)
        if not raw:
            return articles

        feed = feedparser.parse(raw)
        entries = feed.entries[:max_arts]
        logger.info(f"[{self.source_name}] Found {len(entries)} RSS entries")

        for i, entry in enumerate(entries):
            try:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                if summary:
                    summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)

                pub_date = None
                for attr in ("published_parsed", "updated_parsed"):
                    p = getattr(entry, attr, None)
                    if p:
                        pub_date = datetime(*p[:6], tzinfo=timezone.utc)
                        break

                image_url = None
                for attr in ("media_content", "media_thumbnail"):
                    m = getattr(entry, attr, None)
                    if m:
                        image_url = m[0].get("url")
                        break
                if not image_url and hasattr(entry, "enclosures"):
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("image"):
                            image_url = enc.get("href") or enc.get("url")
                            break
                
                # Ensure image_url is absolute
                if image_url and not image_url.startswith("http"):
                    image_url = f"{self.base_url.rstrip('/')}/{image_url.lstrip('/')}"

                # Fetch FULL article content via newspaper3k
                full_content = summary
                if fetch_full and link:
                    try:
                        from app.scrapers.content_extractor import extract_article
                        result = await extract_article(link)
                        if result.get("success") and len(result.get("content", "")) > len(summary or ""):
                            full_content = result["content"]
                        if not image_url and result.get("image_url"):
                            image_url = result["image_url"]
                        if not pub_date and result.get("published_at"):
                            pub_date = result["published_at"]
                    except Exception:
                        pass
                    await asyncio.sleep(0.2)

                article = ScrapedArticle(
                    title=title,
                    content=full_content,
                    url=link,
                    published_at=pub_date,
                    image_url=image_url,
                    author=entry.get("author"),
                )
                if article.is_valid():
                    articles.append(article)

            except Exception as e:
                logger.warning(f"[{self.source_name}] Error parsing entry: {e}")
                continue

        logger.info(f"[{self.source_name}] Scraped {len(articles)} articles (full content: {fetch_full})")
        return articles


class HTMLScraper(BaseScraper):
    """Generic HTML page scraper."""

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        base = self.scraper_config.get("base_url", self.base_url)
        sections = self.scraper_config.get("sections", [""])
        
        # User-defined selectors from Database configuration
        article_sel = self.scraper_config.get("article_selector")
        title_sel = self.scraper_config.get("title_selector")
        link_sel = self.scraper_config.get("link_selector")
        content_sel = self.scraper_config.get("content_selector")
        image_sel = self.scraper_config.get("image_selector")

        for section in sections:
            url = f"{base}/{section}" if section else base
            logger.info(f"[{self.source_name}] Scraping HTML: {url}")

            html = await self.fetch_url(url)
            if not html:
                continue

            soup = self.parse_html(html)
            
            # 1. Identify Articles
            found_articles = []
            if article_sel:
                found_articles = soup.select(article_sel)
            else:
                # Fallback to generic detection patterns
                article_selectors = [
                    "article", ".article", ".news-item", ".story", ".story-item", 
                    ".news-box", ".category-story", "div.item", "div.list-item",
                    ".post", ".entry", ".card", ".news-card",
                ]
                for selector in article_selectors:
                    found = soup.select(selector)
                    if found and len(found) >= 3:
                        found_articles = found
                        break
            
            if not found_articles:
                found_articles = soup.find_all("a", href=True)
                found_articles = [
                    a for a in found_articles
                    if a.get_text(strip=True) and len(a.get_text(strip=True)) > 20
                ]

            for element in found_articles[:settings.MAX_ARTICLES_PER_SCRAPE]:
                try:
                    # 2. Extract Title
                    if title_sel:
                        title_elem = element.select_one(title_sel)
                    else:
                        title_elem = element.find(["h1", "h2", "h3", "h4", "a"])
                    
                    title = title_elem.get_text(strip=True) if title_elem else element.get_text(strip=True)
                    if not title or len(title) < 5: continue

                    # 3. Extract URL
                    if link_sel:
                        link_elem = element.select_one(link_sel)
                    else:
                        link_elem = element.find("a", href=True) if element.name != "a" else element
                    
                    link = ""
                    if link_elem:
                        link = link_elem.get("href", "")
                        if link and not link.startswith("http"):
                            link = f"{base.rstrip('/')}/{link.lstrip('/')}"

                    # 4. Extract Content Snippet
                    if content_sel:
                        content_elem = element.select_one(content_sel)
                    else:
                        content_elem = element.find(["p", ".summary", ".description", ".excerpt"])
                    
                    content = content_elem.get_text(strip=True) if content_elem else ""

                    # 5. Extract Image
                    if image_sel:
                        img_elem = element.select_one(image_sel)
                    else:
                        img_elem = element.find("img")
                    
                    image_url = None
                    if img_elem:
                        image_url = img_elem.get("src") or img_elem.get("data-src")
                        if image_url and not image_url.startswith("http"):
                            image_url = f"{base.rstrip('/')}/{image_url.lstrip('/')}"

                    # 6. Create Article Object
                    article = ScrapedArticle(
                        title=title,
                        content=content,
                        url=link,
                        image_url=image_url,
                        published_at=datetime.now(timezone.utc),
                    )
                    if article.is_valid():
                        articles.append(article)

                except Exception as e:
                    logger.warning(f"[{self.source_name}] Error parsing element: {e}")
                    continue

        # Deduplicate by URL within same scrape
        seen_urls = set()
        unique_articles = []
        for art in articles:
            if art.url and art.url not in seen_urls:
                seen_urls.add(art.url)
                unique_articles.append(art)
            elif not art.url:
                unique_articles.append(art)

        logger.info(f"[{self.source_name}] Scraped {len(unique_articles)} articles from HTML")
        return unique_articles


class ScraperFactory:
    """Factory for creating appropriate scraper instances."""

    # Registry of dedicated scrapers by source name (lowercase)
    _dedicated_scrapers: Dict[str, type] = {}

    @classmethod
    def register(cls, source_name: str, scraper_class: type):
        """Register a dedicated scraper for a specific source."""
        cls._dedicated_scrapers[source_name.lower()] = scraper_class

    @classmethod
    def create(cls, source_config: Dict[str, Any]) -> BaseScraper:
        source_name = source_config.get("name", "").lower()

        # Check for dedicated scraper first
        if source_name in cls._dedicated_scrapers:
            logger.info(f"Using dedicated scraper for: {source_name}")
            return cls._dedicated_scrapers[source_name](source_config)

        # Fall back to generic scrapers by type
        scraper_type = source_config.get("scraper_type", "rss")
        if scraper_type == "rss":
            return RSSScaper(source_config)
        elif scraper_type == "html":
            return HTMLScraper(source_config)
        else:
            logger.warning(f"Unknown scraper type: {scraper_type}, falling back to RSS")
            return RSSScaper(source_config)
