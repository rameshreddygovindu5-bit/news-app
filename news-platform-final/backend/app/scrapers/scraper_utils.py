"""
Common utilities for all scrapers - implements best practices from GreatAndhra scraper.
"""
import re
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def normalize_url(base_url: str, url: str) -> str:
    """Normalize URL to absolute form."""
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(base_url, url)
    if not url.startswith("http"):
        return urljoin(base_url + "/", url)
    return url


def is_excluded_url(url: str, exclude_patterns: List[str]) -> bool:
    """Check if URL matches any exclusion pattern."""
    return any(ex in url for ex in exclude_patterns)


def extract_image(element, base_url: str = "") -> Optional[str]:
    """Extract image URL from element with normalization."""
    if not element:
        return None
    img = element.find("img") if hasattr(element, 'find') else None
    if not img:
        return None
    src = img.get("src") or img.get("data-src") or ""
    if not src or any(skip in src.lower() for skip in ["atrk.gif", "msn_", "placeholder"]):
        return None
    return normalize_url(base_url, src) if base_url else src


def filter_content(text: str, title: str = "", end_markers: List[str] = None) -> str:
    """Filter out common noise from content."""
    if not text:
        return ""
    
    # Common noise patterns
    noise_patterns = [
        r"Click Here For Photo Gallery",
        r"Published Date",
        r"UPDATED",
        r"Tags:",
        r"RELATED ARTICLES",
        r"Related Articles",
        r"Top News",
        r"Top Trending",
        r"Recommended For You",
        r"Gossip:",
        r"About Us",
        r"Disclaimer",
        r"\u00a9",
    ]
    
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 15:
            continue
        if line == title:
            continue
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in noise_patterns):
            continue
        filtered_lines.append(line)
    
    return '\n\n'.join(filtered_lines)


async def fetch_with_retry(scraper, url: str, max_retries: int = 2, 
                         request_delay: float = 0.5) -> Optional[str]:
    """
    Fetch URL with retry logic and exponential backoff.
    Based on GreatAndhra scraper's _fetch_with_retry method.
    """
    for attempt in range(1, max_retries + 1):
        await asyncio.sleep(request_delay)
        html = await scraper.fetch_url(url)
        if html:
            return html
        if attempt < max_retries:
            wait = request_delay * attempt * 2
            logger.warning(f"[RETRY] Attempt {attempt}/{max_retries} for {url} (wait {wait:.1f}s)")
            await asyncio.sleep(wait)
    return None


def extract_date_from_text(text: str, date_patterns: List[re.Pattern] = None) -> Optional[datetime]:
    """Extract date from text using regex patterns."""
    if not text:
        return None
    
    # Default patterns for common date formats
    if not date_patterns:
        date_patterns = [
            re.compile(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*IST"),
            re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{1,2}):(\d{2}):(\d{2})"),
            re.compile(r"([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})"),
        ]
    
    for pattern in date_patterns:
        match = pattern.search(text)
        if match:
            try:
                # Handle different pattern formats
                groups = match.groups()
                if len(groups) == 6:  # DD-MMM-YYYY HH:MM:SS IST
                    day, mon, yr, h, mi, s = groups
                    month_map = {
                        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
                    }
                    return datetime(
                        int(yr), month_map.get(mon, 1), int(day),
                        int(h), int(mi), int(s), tzinfo=timezone.utc
                    )
                elif len(groups) == 6:  # YYYY-MM-DD HH:MM:SS
                    yr, mon, day, h, mi, s = groups
                    return datetime(
                        int(yr), int(mon), int(day),
                        int(h), int(mi), int(s), tzinfo=timezone.utc
                    )
            except (ValueError, KeyError):
                continue
    
    return None


def validate_article(title: str, content: str, url: str) -> bool:
    """Validate article has minimum required data."""
    if not title or len(title.strip()) < 5:
        return False
    if not url:
        return False
    return True


class ArticleExtractor:
    """Helper class for extracting article content with multiple fallbacks."""
    
    def __init__(self, base_url: str = "", content_selectors: List[str] = None,
                 image_selectors: List[str] = None, end_markers: List[str] = None):
        self.base_url = base_url
        self.content_selectors = content_selectors or [
            ".article-body", ".entry-content", ".post-content", 
            ".story-content", ".article-content", "article .content",
            ".fullstory", ".field-item", "#storyBody"
        ]
        self.image_selectors = image_selectors or [
            ".article-image img", ".featured-image img", 
            ".entry-thumbnail img", "article img"
        ]
        self.end_markers = end_markers or [
            "RELATED ARTICLES", "Related Articles", "Top News", 
            "Top Trending", "Recommended For You", "Tags:"
        ]
    
    def extract_content(self, soup: BeautifulSoup, title: str = "") -> str:
        """Extract content using multiple selectors."""
        content_parts = []
        
        for selector in self.content_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Extract paragraphs
                paragraphs = elem.find_all("p")
                if paragraphs:
                    content = " ".join(
                        p.get_text(strip=True) 
                        for p in paragraphs 
                        if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20
                    )
                else:
                    content = elem.get_text(separator=" ", strip=True)
                
                if len(content) > 100:
                    return filter_content(content, title, self.end_markers)
        
        return ""
    
    def extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract image using multiple selectors."""
        for selector in self.image_selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get("src") or img.get("data-src") or ""
                if src and not any(skip in src.lower() for skip in ["atrk.gif", "msn_", "placeholder"]):
                    return normalize_url(self.base_url, src) if self.base_url else src
        return None
    
    async def extract_with_newspaper3k(self, url: str, html: str = None) -> Dict[str, Any]:
        """Fallback extraction using newspaper3k."""
        try:
            from app.scrapers.content_extractor import extract_article
            result = await extract_article(url, html)
            return result
        except Exception as e:
            logger.debug(f"[NEWSPAPER3K] Failed for {url}: {e}")
            return {"success": False, "content": "", "image_url": None}
