"""
TeluguTimes.net — Telugu and English news.
Registers for both "telugutimes telugu" and "telugutimes english".
Uses RSS feeds if available, falls back to HTML section scraping.
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

# URL exclusion patterns
EXCLUDE_PATTERNS = [
    "#", "javascript:", "/tag/", "/author/", "/page/",
    "/gallery", "/epaper", "/convergence", "/aboutus", "/contactus"
]

# Date patterns specific to TeluguTimes
DATE_PATTERNS = [
    re.compile(r"(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})\s*(AM|PM)"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})"),
    re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})"),
]


class TeluguTimesScraper(BaseScraper):
    """Works for both Telugu and English editions based on base_url config."""
    
    def __init__(self, source_config):
        super().__init__(source_config)
        self.max_articles = self.scraper_config.get("max_articles", 50)
        self.request_delay = self.scraper_config.get("request_delay", 0.5)
        self.max_retries = self.scraper_config.get("max_retries", 2)
        self.fetch_full_content = self.scraper_config.get("fetch_full_content", True)
        self.sequential_mode = self.scraper_config.get("sequential_mode", False)
        
        base = self.scraper_config.get("base_url", self.base_url)
        
        # Initialize article extractor
        self.extractor = ArticleExtractor(
            base_url=base,
            content_selectors=[
                ".entry-content", ".post-content", ".td-post-content", 
                "article .content", ".article-body", ".story-content"
            ],
            image_selectors=[
                "article img", ".entry-content img", ".post-thumbnail img",
                ".featured-image img", ".entry-thumbnail img"
            ]
        )
    
    def _is_valid_article_url(self, url: str, base: str) -> bool:
        """Check if URL is a valid article URL."""
        if not url or is_excluded_url(url, EXCLUDE_PATTERNS):
            return False
        # TeluguTimes specific pattern
        return "/" in url.replace(base, "") and len(url) > len(base) + 10
    
    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch URL with retry logic."""
        return await fetch_with_retry(self, url, self.max_retries, self.request_delay)
    
    def _extract_links_from_html(self, html: str, seen: Set[str], base: str) -> List[Dict]:
        """Extract article links from HTML page."""
        soup = BeautifulSoup(html, "lxml")
        articles = []
        
        for a_tag in soup.find_all("a", href=True):
            href = normalize_url(base, a_tag.get("href", ""))
            if not self._is_valid_article_url(href, base) or href in seen:
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
            
            image_url = extract_image(a_tag, base) or extract_image(parent, base)
            
            articles.append({
                "url": href,
                "title": title,
                "image_url": image_url,
                "summary": summary,
                "published_at": published_at,
            })
        
        return articles
    
    async def _process_rss_entry(self, entry, seen: Set[str]) -> Optional[ScrapedArticle]:
        """Process a single RSS entry."""
        link = entry.get("link", "")
        if not link or link in seen:
            return None
        
        seen.add(link)
        title = entry.get("title", "")
        if not title:
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
            author="TeluguTimes"
        )
    
    async def _process_html_article(self, article_data: Dict, base: str) -> Optional[ScrapedArticle]:
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
                author="TeluguTimes"
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
            author="TeluguTimes"
        )
    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        
        # Determine base URL based on source name
        if "telugu" in self.source_name.lower():
            base = "https://www.telugutimes.net"
        else:
            base = "https://www.telugutimes.net"
        
        # Try RSS first
        logger.info(f"[TELUGUTIMES] Starting RSS scrape for {base}")
        rss_url = f"{base}/rss"
        xml = await self._fetch_with_retry(rss_url)
        if xml:
            feed = feedparser.parse(xml)
            logger.info(f"[TELUGUTIMES] RSS: {len(feed.entries)} entries")
            
            for entry in feed.entries:
                if len(articles) >= self.max_articles:
                    break
                
                article = await self._process_rss_entry(entry, seen)
                if article and article.is_valid():
                    articles.append(article)
                
                if not self.sequential_mode:
                    await asyncio.sleep(self.request_delay)
        else:
            # Fallback to HTML scraping
            logger.info(f"[TELUGUTIMES] RSS failed, trying HTML fallback")
            sections = self.scraper_config.get("sections", [""])
            for section in sections:
                if len(articles) >= self.max_articles:
                    break
                
                url = f"{base.rstrip('/')}/{section}" if section else base
                html = await self._fetch_with_retry(url)
                if not html:
                    continue
                
                soup = self.parse_html(html)
                article_links = self._extract_links_from_html(html, seen, base)
                
                logger.info(f"[TELUGUTIMES] Section {section}: found {len(article_links)} articles")
                
                for article_data in article_links:
                    if len(articles) >= self.max_articles:
                        break
                    
                    article = await self._process_html_article(article_data, base)
                    if article and article.is_valid():
                        articles.append(article)
                    
                    if not self.sequential_mode:
                        await asyncio.sleep(self.request_delay)
                
                await asyncio.sleep(self.request_delay)
        
        logger.info(f"[TELUGUTIMES] Scraped {len(articles)} articles total")
        return articles

ScraperFactory.register("telugutimes telugu", TeluguTimesScraper)
ScraperFactory.register("telugutimes english", TeluguTimesScraper)
