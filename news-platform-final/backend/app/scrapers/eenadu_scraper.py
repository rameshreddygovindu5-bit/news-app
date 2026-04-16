"""
Eenadu.net — Largest Telugu newspaper.
Uses real Eenadu RSS feeds for each section, then fetches full article pages.

RSS feeds verified:
  - https://www.eenadu.net/rss/mainnews-rss.xml (main)
  - https://www.eenadu.net/rss/telangana-rss.xml
  - https://www.eenadu.net/rss/andhrapradesh-rss.xml
  - https://www.eenadu.net/rss/politics-rss.xml
  - https://www.eenadu.net/rss/sports-rss.xml
  - https://www.eenadu.net/rss/business-rss.xml
  - https://www.eenadu.net/rss/movies-rss.xml
  - https://www.eenadu.net/rss/international-rss.xml
"""

import asyncio
import logging
import feedparser
import re
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

BASE = "https://www.eenadu.net"
RSS_FEEDS = []  # RSS feeds not working (404 errors)
HTML_SECTIONS = [
    "/latest-news-list",
    "/telangana",
    "/andhra-pradesh", 
    "/politics",
    "/national",
    "/sports",
    "/business",
    "/movies",
    "/international"
]

# URL exclusion patterns
EXCLUDE_PATTERNS = [
    "/photo", "/video", "#", "javascript:", "/tag/",
    "/gallery", "/epaper", "/convergence", "/aboutus", "/contactus"
]

# Date patterns specific to Eenadu
DATE_PATTERNS = [
    re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})"),
    re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})"),
]


class EenaduScraper(BaseScraper):
    """Eenadu dedicated scraper — RSS feeds + full article page extraction."""
    
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
                ".fullstory", ".field-item.even", "#newsBody", 
                "article .content", ".article-body", ".entry-content"
            ],
            image_selectors=[
                ".field-items img", ".fullstory img", "article img",
                ".post-thumbnail img", ".entry-thumbnail img"
            ]
        )
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL."""
        if not url or is_excluded_url(url, EXCLUDE_PATTERNS):
            return False
        # Eenadu specific pattern
        return "/" in url.replace(BASE, "") and len(url) > len(BASE) + 10
    
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        return await fetch_with_retry(self, url, self.max_retries, self.request_delay)
    
    async def _process_rss_entry(self, entry, seen_urls: Set[str]) -> Optional[ScrapedArticle]:
        """Process a single RSS entry."""
        link = entry.get("link", "")
        if not link or link in seen_urls:
            return None
        
        seen_urls.add(link)
        title = entry.get("title", "")
        if not title or len(title) < 5:
            return None
        
        # Parse RSS date
        pub_date = None
        for attr in ("published_parsed", "updated_parsed"):
            p = getattr(entry, attr, None)
            if p:
                pub_date = datetime(*p[:6], tzinfo=timezone.utc)
                break
        
        # RSS summary as fallback content
        summary = entry.get("summary", entry.get("description", ""))
        if summary:
            summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)
        
        # RSS image
        image_url = None
        if hasattr(entry, "media_content") and entry.media_content:
            image_url = entry.media_content[0].get("url")
        
        # Fetch full article content
        content = summary
        if self.fetch_full_content and link:
            html = await self._fetch_with_retry(link)
            if html:
                soup = self.parse_html(html)
                # Eenadu specific: .fullstory, .field-item
                extracted = self.extractor.extract_content(soup, title)
                if len(extracted) > len(summary or ""):
                    content = extracted
                if not image_url:
                    image_url = self.extractor.extract_image(soup)
        
        # newspaper3k fallback if CSS selectors got nothing
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
            author="Eenadu"
        )
    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        
        # HTML scraping only since RSS feeds are not working
        logger.info(f"[EENADU] Starting HTML scrape from {len(HTML_SECTIONS)} sections")
        for section in HTML_SECTIONS:
            if len(articles) >= self.max_articles:
                break
            
            section_url = f"{BASE}{section}"
            html = await self._fetch_with_retry(section_url)
            if not html:
                continue
            
            soup = self.parse_html(html)
            article_links = self._extract_links_from_html(html, seen)
            
            logger.info(f"[EENADU] Section {section}: found {len(article_links)} articles")
            
            for article_data in article_links:
                if len(articles) >= self.max_articles:
                    break
                
                article = await self._process_html_article(article_data)
                if article and article.is_valid():
                    articles.append(article)
                
                if not self.sequential_mode:
                    await asyncio.sleep(self.request_delay)
            
            await asyncio.sleep(self.request_delay)
        
        logger.info(f"[EENADU] Scraped {len(articles)} articles total")
        return articles
    
    def _extract_links_from_html(self, html: str, seen: Set[str]) -> List[Dict]:
        """Extract article links from HTML page."""
        soup = BeautifulSoup(html, "lxml")
        articles = []
        
        for a_tag in soup.find_all("a", href=True):
            href = normalize_url(BASE, a_tag.get("href", ""))
            if not href or href in seen:
                continue
            
            # Eenadu specific URL pattern
            if not href.startswith(BASE) or len(href) < len(BASE) + 10:
                continue
            
            title = (a_tag.get("title") or "").strip()
            if not title:
                title = a_tag.get_text(strip=True)
            if not title or len(title) < 10:
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
                author="Eenadu"
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
            author="Eenadu"
        )


ScraperFactory.register("eenadu", EenaduScraper)
