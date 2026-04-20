"""
Google News Scraper (v7) — Dependency-Free Edition
Uses feedparser directly to avoid pygooglenews conflicts.
High-fidelity extraction using googlenewsdecoder (new_decoderv1) + newspaper3k.
"""

import asyncio
import logging
import requests
import feedparser
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse, quote

from app.scrapers.base_scraper import BaseScraper, ScrapedArticle
from newspaper import Article, Config

logger = logging.getLogger(__name__)

class GoogleNewsScraper(BaseScraper):
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        }
        self.session = requests.Session()
        self.article_config = Config()
        self.article_config.browser_user_agent = self.headers['User-Agent']
        self.article_config.request_timeout = 20
        self.article_config.memoize_articles = False

    def resolve_url(self, google_url: str) -> str:
        """Resolve Google News redirect links to actual article URLs."""
        # 1. Try Decoder (Modern way)
        try:
            from googlenewsdecoder import new_decoderv1
            res = new_decoderv1(google_url, interval=1)
            if res.get("status") and res.get("decoded_url"):
                return res["decoded_url"]
        except Exception:
            pass

        # 2. Fallback: Manual Resolve (User's logic)
        try:
            response = self.session.get(google_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                if "url=" in response.text.lower():
                    match = re.search(r'url=([^\s"]+)', response.text, re.IGNORECASE)
                    if match: 
                        u = match.group(1).replace('"', '').replace("'", "")
                        if u.startswith('http'): return u
                return response.url
        except:
            pass
        return google_url

    def format_html_content(self, text: str) -> str:
        """Antigravity Style: Bold first paragraph, wrap in <p> labels."""
        if not text: return ""
        paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
        html = ""
        for i, p in enumerate(paragraphs):
            if i == 0:
                html += f"<p><b>{p}</b></p>\n"
            else:
                html += f"<p>{p}</p>\n"
        return html

    def extract_source(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            domain = urlparse(url).netloc
            return domain.replace("www.", "")
        except:
            return "Unknown Source"

    def get_friendly_category(self, topic: Optional[str], query: Optional[str]) -> str:
        mapping = {"WORLD": "World", "NATION": "U.S.", "BUSINESS": "Business", "TECHNOLOGY": "Technology"}
        if query and "india" in query.lower(): return "India"
        if topic: return mapping.get(topic.upper(), "General")
        return "General"

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        topic = self.scraper_config.get("topic")
        search_query = self.scraper_config.get("search_query")
        max_limit = self.scraper_config.get("max_articles", 5) 

        # Construct RSS URL
        if topic:
            rss_url = f"https://news.google.com/rss/headlines/section/topic/{topic.upper()}?hl=en-US&gl=US&ceid=US:en"
        elif search_query:
            rss_url = f"https://news.google.com/rss/search?q={quote(search_query)}&hl=en-US&gl=US&ceid=US:en"
        else:
            rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"

        logger.info(f"[GNews] Fetching RSS: {rss_url}")
        try:
            feed = await asyncio.to_thread(feedparser.parse, rss_url)
            entries = feed.get('entries', [])[:max_limit]
        except Exception as e:
            logger.error(f"[GNews] RSS Error: {e}")
            return []

        category = self.get_friendly_category(topic, search_query)

        for entry in entries:
            try:
                # 1. Resolve
                google_link = entry.get('link')
                logger.info(f"[GNews] Processing: {entry.get('title', '...')[:50]}")
                url = await asyncio.to_thread(self.resolve_url, google_link)
                
                # 2. Extract
                article_data = await asyncio.to_thread(self.extract_full, url)
                if not article_data: continue

                # 3. Create
                scraped = ScrapedArticle(
                    title=article_data['title'],
                    content=article_data['content'],
                    url=url,
                    published_at=datetime.now(timezone.utc),
                    image_url=article_data['image_url'],
                    metadata={
                        "Category": category,
                        "Source": self.extract_source(url),
                        "Tags": article_data['tags']
                    }
                )
                if scraped.is_valid():
                    articles.append(scraped)
                    logger.info(f"[GNews]   ✓ Saved")
            except Exception as e:
                logger.debug(f"[GNews] Entry Error: {e}")
                continue
        
        return articles

    def extract_full(self, url: str) -> Optional[Dict]:
        try:
            article = Article(url, config=self.article_config)
            article.download()
            article.parse()
            text = article.text
            
            # If newspaper3k returns too little, try our specialized ArticleExtractor
            if not text or len(text) < 300:
                from app.scrapers.scraper_utils import ArticleExtractor
                import requests
                from bs4 import BeautifulSoup
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.ok:
                    soup = BeautifulSoup(resp.text, "lxml")
                    ae = ArticleExtractor(base_url=url)
                    alt_text = ae.extract_content(soup, article.title)
                    if len(alt_text) > len(text or ""):
                        text = alt_text

            if not text or len(text) < 100: return None
            
            try:
                article.nlp()
                tags = ", ".join(article.keywords[:5])
            except:
                tags = ""

            return {
                "title": article.title or "Unknown",
                "content": self.format_html_content(text),
                "image_url": article.top_image,
                "tags": tags
            }
        except Exception as e:
            logger.debug(f"[GNews] Extraction failed for {url}: {e}")
            return None

# Registration — register under both keys so ScraperFactory always finds it
from app.scrapers.base_scraper import ScraperFactory
ScraperFactory.register("googlenews", GoogleNewsScraper)
ScraperFactory.register("google news", GoogleNewsScraper)  # matches source.name for AI bypass check