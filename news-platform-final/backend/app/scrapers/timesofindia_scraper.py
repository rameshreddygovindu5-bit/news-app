"""
Times of India News Scraper
============================
RSS feeds → full article extraction via CSS selectors + newspaper3k fallback.

Key design:
  - newspaper3k fallback when CSS selectors fail (TOI changes DOM frequently)
  - Source name / branding stripped from content and titles
  - Image extracted from RSS enclosure + og:image + article body
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import feedparser
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Source branding patterns to strip from scraped content
_SOURCE_PATTERNS = [
    re.compile(r'\(?(PTI|ANI|IANS|Reuters|AP|AFP|Times of India|TOI|Agencies)\)?\.?\s*', re.I),
    re.compile(r'(?:Read Also|Also Read|Related News|Follow us on|Subscribe to).*$', re.I | re.M),
    re.compile(r'For the latest.*?(?:visit|download|follow).*$', re.I | re.M),
    re.compile(r'Published on:?\s*\w+ \d{1,2},?\s*\d{4}.*$', re.I | re.M),
    re.compile(r'Updated:?\s*\w+ \d{1,2},?\s*\d{4}.*$', re.I | re.M),
    re.compile(r'Get the latest.*$', re.I | re.M),
    re.compile(r'Download the.*?app.*$', re.I | re.M),
    re.compile(r'Share this article.*$', re.I | re.M),
    re.compile(r'(?:Written|Reported)\s+[Bb]y\s+.*?(?:\n|$)', re.M),
    re.compile(r'timesofindia\.indiatimes\.com', re.I),
]

def _clean_text(text: str) -> str:
    """Remove source names, branding, and noise from scraped text."""
    if not text:
        return ""
    for pat in _SOURCE_PATTERNS:
        text = pat.sub('', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


RSS_FEEDS = {
    'top_stories':   'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
    'india':         'https://timesofindia.indiatimes.com/rssfeeds/2955838.cms',
    'world':         'https://timesofindia.indiatimes.com/rssfeeds/2986608.cms',
    'business':      'https://timesofindia.indiatimes.com/rssfeeds/1898055.cms',
    'sports':        'https://timesofindia.indiatimes.com/rssfeeds/4719148.cms',
    'tech':          'https://timesofindia.indiatimes.com/rssfeeds/6613053.cms',
    'entertainment': 'https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms',
    'science':       'https://timesofindia.indiatimes.com/rssfeeds/1481486148.cms',
    'health':        'https://timesofindia.indiatimes.com/rssfeeds/-2128672765.cms',
}

# TOI content selectors — ordered by reliability
CONTENT_SELECTORS = [
    'div._s30J',
    'div[data-articlebody="1"]',
    'div.Normal',
    'div._3WlLe',
    'div[data-plugin="storycontent"]',
    'div.article_content',
    'div.article-body',
    'div.story-content',
    'article .content',
]


class TimesOfIndiaScraper(BaseScraper):
    """Times of India scraper — RSS + robust article extraction."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://timesofindia.indiatimes.com"
        self.max_articles = self.scraper_config.get("max_articles", settings.MAX_ARTICLES_PER_SCRAPE)
        self.request_delay = self.scraper_config.get("request_delay", 0.3)

    async def scrape(self) -> List[ScrapedArticle]:
        all_articles: List[ScrapedArticle] = []
        seen_urls = set()

        for feed_name, feed_url in RSS_FEEDS.items():
            if len(all_articles) >= self.max_articles:
                break
            try:
                articles = await self._scrape_feed(feed_name, feed_url, seen_urls)
                all_articles.extend(articles)
                logger.info(f"[TOI] {feed_name}: +{len(articles)} articles")
            except Exception as e:
                logger.error(f"[TOI] Feed {feed_name} error: {e}")

        logger.info(f"[TOI] Total: {len(all_articles)} unique articles")
        return all_articles

    async def _scrape_feed(self, feed_name: str, feed_url: str, seen: set) -> List[ScrapedArticle]:
        articles = []
        xml = await self.fetch_url(feed_url)
        if not xml:
            return articles

        feed = feedparser.parse(xml)

        for entry in feed.entries:
            if len(articles) >= self.max_articles:
                break

            link = getattr(entry, 'link', '').strip()
            if not link or link in seen:
                continue
            seen.add(link)

            title = _clean_text(getattr(entry, 'title', '').strip())
            if not title or len(title) < 10:
                continue

            # Parse date
            pub_date = None
            for attr in ('published_parsed', 'updated_parsed'):
                p = getattr(entry, attr, None)
                if p:
                    try:
                        pub_date = datetime(*p[:6], tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        pass
                    break

            # Image from RSS
            image_url = None
            if hasattr(entry, 'enclosures'):
                for enc in entry.enclosures:
                    if getattr(enc, 'type', '').startswith('image/'):
                        image_url = getattr(enc, 'url', '') or getattr(enc, 'href', '')
                        break
            if not image_url:
                for attr in ('media_content', 'media_thumbnail'):
                    m = getattr(entry, attr, None)
                    if m:
                        image_url = m[0].get('url', '')
                        break

            # RSS summary
            summary = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
            if summary:
                summary = BeautifulSoup(summary, 'lxml').get_text(separator=' ', strip=True)
                summary = _clean_text(summary)

            # Fetch full content
            content, page_image = await self._extract_full_content(link)
            if not content or len(content) < len(summary or ''):
                content = summary
            if not image_url and page_image:
                image_url = page_image

            content = _clean_text(content or '')
            title = _clean_text(title)

            article = ScrapedArticle(
                title=title,
                content=content,
                url=link,
                published_at=pub_date,
                image_url=image_url,
                author=getattr(entry, 'author', None),
            )
            if article.is_valid():
                articles.append(article)

            await asyncio.sleep(self.request_delay)

        return articles

    async def _extract_full_content(self, url: str) -> tuple:
        """Extract full article text + image. Returns (content, image_url)."""
        image_url = None

        # Method 1: CSS selectors
        html = await self.fetch_url(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')

            # Extract og:image
            og = soup.find('meta', property='og:image')
            if og:
                image_url = og.get('content', '')

            # Remove noise
            for tag in soup.select('script, style, .ad, .advertisement, .social-share, '
                                   '.share-toolbar, .comments, .related-articles, '
                                   'aside, nav, footer, .sidebar, .widget'):
                tag.decompose()

            # Try each selector
            for selector in CONTENT_SELECTORS:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(separator='\n', strip=True)
                    if len(text) > 150:
                        return _clean_text(text), image_url

            # Fallback: all <p> tags
            article_el = soup.find('article') or soup.find('main') or soup
            paras = article_el.find_all('p')
            text = '\n\n'.join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 20)
            if len(text) > 150:
                return _clean_text(text), image_url

        # Method 2: newspaper3k
        try:
            from app.scrapers.content_extractor import extract_article
            result = await extract_article(url, html)
            if result.get('success') and len(result.get('content', '')) > 100:
                if not image_url and result.get('image_url'):
                    image_url = result['image_url']
                return _clean_text(result['content']), image_url
        except Exception as e:
            logger.debug(f"[TOI] newspaper3k failed for {url}: {e}")

        return None, image_url


ScraperFactory.register('Times of India', TimesOfIndiaScraper)
ScraperFactory.register('timesofindia', TimesOfIndiaScraper)
