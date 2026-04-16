"""
Telugu123.com — Telugu entertainment and news.
HTML scraper — scrapes section listing pages then fetches article detail.
Sections: /news, /movies, /reviews, /political-news
"""
import asyncio, logging, re
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
BASE = "https://www.telugu123.com"  # Site showing 'Launching Soon'
SECTIONS = ["news", "movies", "reviews", "political-news", "gossips"]

# URL exclusion patterns
EXCLUDE_PATTERNS = [
    "/photo", "/video", "#", "javascript:", "/tag/", "/page/",
    "/gallery", "/epaper", "/convergence", "/aboutus", "/contactus"
]

# Date patterns specific to Telugu123
DATE_PATTERNS = [
    re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})"),
    re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})"),
]


class Telugu123Scraper(BaseScraper):
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
                ".entry-content", ".post-content", ".article-body", 
                "article", ".story-content", ".post-detail"
            ],
            image_selectors=[
                ".entry-content img", ".post-thumbnail img", "article img",
                ".featured-image img", ".post-detail img"
            ]
        )
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL."""
        if not url or is_excluded_url(url, EXCLUDE_PATTERNS):
            return False
        # Telugu123 specific pattern
        return "/" in url.replace(BASE, "") and len(url) > len(BASE) + 10
    
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        return await fetch_with_retry(self, url, self.max_retries, self.request_delay)
    
    def _extract_links_from_html(self, html: str, seen: Set[str]) -> List[Dict]:
        """Extract article links from HTML page."""
        soup = BeautifulSoup(html, "lxml")
        articles = []
        
        for a_tag in soup.find_all("a", href=True):
            href = normalize_url(BASE, a_tag.get("href", ""))
            if not self._is_valid_article_url(href) or href in seen:
                continue
            
            title = (a_tag.get("title") or "").strip()
            if not title:
                title = a_tag.get_text(strip=True)
            if not title or len(title) < 12:
                continue
            
            seen.add(href)
            
            # Extract additional info from parent
            parent = a_tag.find_parent(["li", "div", "article", "td"])
            summary = ""
            published_at = None
            
            if parent:
                parent_text = parent.get_text(" ", strip=True)
                published_at = extract_date_from_text(parent_text, DATE_PATTERNS)
                # Look for summary in parent
                for child in parent.children:
                    if hasattr(child, 'get_text'):
                        txt = child.get_text(strip=True)
                        if (txt and len(txt) > 30 and 
                            txt != title and 
                            "Published Date" not in txt):
                            summary = txt
                            break
            
            image_url = extract_image(a_tag, BASE) or extract_image(parent, BASE)
            
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
                author="Telugu123"
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
            author="Telugu123"
        )
    async def scrape(self) -> List[ScrapedArticle]:
        # Site is showing 'Launching Soon', return empty list
        logger.warning("[TELUGU123] Site is showing 'Launching Soon' - scraper disabled")
        return []

ScraperFactory.register("telugu123", Telugu123Scraper)
