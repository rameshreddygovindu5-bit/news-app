"""
PrabhaNews.com — Telugu news portal.
RSS: https://www.prabhanews.com/feed/
Sections: /andhra-pradesh, /telangana, /politics, /national, /crime, /sports, /movies
"""
import asyncio, logging, feedparser, re
from datetime import datetime, timezone
from typing import List, Set, Dict, Optional
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory
from app.scrapers.scraper_utils import (
    normalize_url, is_excluded_url, extract_image, filter_content,
    fetch_with_retry, extract_date_from_text, validate_article,
    ArticleExtractor
)

logger = logging.getLogger(__name__)
BASE = "https://www.prabhanews.com"
SECTION_FEEDS = [
    f"{BASE}/feed/",
    f"{BASE}/category/andhra-pradesh/feed/",
    f"{BASE}/category/telangana/feed/",
    f"{BASE}/category/politics/feed/",
    f"{BASE}/category/national/feed/",
    f"{BASE}/category/sports/feed/",
    f"{BASE}/category/movies/feed/",
]

# URL exclusion patterns
EXCLUDE_PATTERNS = [
    "/photo", "/video", "#", "javascript:", "/tag/", "/page/",
    "/gallery", "/epaper", "/convergence", "/aboutus", "/contactus"
]

# Date patterns specific to PrabhaNews
DATE_PATTERNS = [
    re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})"),
    re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})"),
]


class PrabhaNewsScraper(BaseScraper):
    def __init__(self, source_config):
        super().__init__(source_config)
        self.max_articles = self.scraper_config.get("max_articles", 50)
        self.request_delay = self.scraper_config.get("request_delay", 0.5)
        self.max_retries = self.scraper_config.get("max_retries", 2)
        self.fetch_full_content = self.scraper_config.get("fetch_full_content", True)
        self.sequential_mode = self.scraper_config.get("sequential_mode", False)
        
        # Initialize article extractor
        self.extractor = ArticleExtractor(
            base_url=BASE,
            content_selectors=[
                ".entry-content", ".post-content", "article .content", 
                ".td-post-content", ".article-body", ".story-content"
            ],
            image_selectors=[
                ".entry-content img", ".post-thumbnail img", "article img",
                ".featured-image img", ".entry-thumbnail img"
            ]
        )
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL."""
        if not url or is_excluded_url(url, EXCLUDE_PATTERNS):
            return False
        # PrabhaNews specific pattern
        return "/" in url.replace(BASE, "") and len(url) > len(BASE) + 10
    
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        return await fetch_with_retry(self, url, self.max_retries, self.request_delay)
    
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
        if hasattr(entry, "media_content") and entry.media_content:
            image_url = entry.media_content[0].get("url")
        
        # Fetch full content
        content = summary
        if self.fetch_full_content and link:
            html = await self._fetch_with_retry(link)
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
            author="PrabhaNews"
        )
    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        
        logger.info(f"[PRABHA] Starting RSS scrape from {len(SECTION_FEEDS)} feeds")
        for feed_url in SECTION_FEEDS:
            if len(articles) >= self.max_articles:
                break
            
            try:
                xml = await self._fetch_with_retry(feed_url)
                if not xml:
                    continue
                
                feed = feedparser.parse(xml)
                logger.info(f"[PRABHA] {feed_url.split('/')[-2]}: {len(feed.entries)} entries")
                
                for entry in feed.entries:
                    if len(articles) >= self.max_articles:
                        break
                    
                    article = await self._process_rss_entry(entry, seen)
                    if article and article.is_valid():
                        articles.append(article)
                    
                    if not self.sequential_mode:
                        await asyncio.sleep(self.request_delay)
                        
            except Exception as e:
                logger.warning(f"[PRABHA] Feed error for {feed_url}: {e}")
        
        logger.info(f"[PRABHA] Scraped {len(articles)} articles total")
        return articles

ScraperFactory.register("prabhanews", PrabhaNewsScraper)
