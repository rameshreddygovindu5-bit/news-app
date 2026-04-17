"""
Google News Scraper (v6)
High-fidelity extraction using pygooglenews + googlenewsdecoder (new_decoderv1) + newspaper3k.
Optimized for 100% format compliance.
"""

import asyncio
import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse

from app.scrapers.base_scraper import BaseScraper, ScrapedArticle
from pygooglenews import GoogleNews
from newspaper import Article, Config

logger = logging.getLogger(__name__)

class GoogleNewsScraper(BaseScraper):
    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.gn = GoogleNews(lang='en', country='US')
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/437.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        }
        self.session = requests.Session()
        self.article_config = Config()
        self.article_config.browser_user_agent = self.headers['User-Agent']
        self.article_config.request_timeout = 20
        self.article_config.memoize_articles = False

    def resolve_url(self, google_url: str) -> str:
        """Standard pygooglenews links are redirects; resolve to actual URL."""
        try:
            from googlenewsdecoder import new_decoderv1
            res = new_decoderv1(google_url, interval=1)
            if res.get("status") and res.get("decoded_url"):
                return res["decoded_url"]
        except Exception as e:
            logger.info(f"[GNews] Decoder failed for {google_url[:50]}: {e}")
        return google_url

    def format_html_content(self, text: str) -> str:
        """Standard Antigravity Bold style formatting."""
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
        """Extracts clean domain name from URL (e.g., reuters.com)."""
        try:
            domain = urlparse(url).netloc
            return domain.replace("www.", "")
        except:
            return "Unknown Source"

    def get_friendly_category(self, topic: Optional[str], query: Optional[str]) -> str:
        """Maps config inputs to requested standard categories."""
        if query and "india" in query.lower():
            return "India"
        if topic:
            mapping = {
                "WORLD": "World",
                "NATION": "U.S.",
                "BUSINESS": "Business",
                "TECHNOLOGY": "Technology"
            }
            return mapping.get(topic.upper(), "General")
        return "General"

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        topic = self.scraper_config.get("topic")
        search_query = self.scraper_config.get("search_query")
        max_limit = self.scraper_config.get("max_articles", 100)
        
        category = self.get_friendly_category(topic, search_query)

        logger.info(f"[GNews] Scraping {self.source_name} Category")
        try:
            if topic:
                feed = self.gn.topic_headlines(topic.upper())
            elif search_query:
                feed = self.gn.search(search_query, when='24h')
            else:
                feed = self.gn.top_headlines()
            
            entries = feed.get('entries', [])[:max_limit]
        except Exception as e:
            logger.error(f"[GNews] RSS Fetch Error: {e}")
            return []

        for entry in entries:
            try:
                # 1. Resolve URL
                logger.info(f"[GNews] Resolving: {entry.get('title', '...')[:40]}")
                url = await asyncio.to_thread(self.resolve_url, entry.get('link'))
                
                # 2. Extract Data
                article_data = await asyncio.to_thread(self.extract_full, url)
                if not article_data: continue

                # 3. Create ScrapedArticle mapped strictly to requested schema
                scraped = ScrapedArticle(
                    title=article_data['title'],
                    content=article_data['content'],
                    url=url, # Home
                    published_at=datetime.now(timezone.utc),
                    image_url=article_data['image_url'],
                    # Fulfilling mandatory custom fields inside metadata or mapping depending on your BaseScraper
                    metadata={
                        "Category": category,
                        "Source": self.extract_source(url),
                        "Peoples Feedback": "N/A",
                        "Tags": article_data['tags'],
                        "source_id": self.source_name
                    }
                )
                if scraped.is_valid():
                    articles.append(scraped)
                    logger.info(f"[GNews]   ✓ {scraped.title[:50]}...")
            except Exception as e:
                logger.debug(f"[GNews] Error: {e}")
                continue
        
        return articles

    def extract_full(self, url: str) -> Optional[Dict]:
        try:
            article = Article(url, config=self.article_config)
            article.download()
            article.parse()
            
            text = article.text
            if not text or len(text) < 150:
                return None
            
            try: 
                article.nlp()
                # Join tags list into comma-separated string to match your prompt specs
                tags = ", ".join(article.keywords[:5])
            except: 
                tags = ""

            return {
                "title": article.title or "Unknown",
                "content": self.format_html_content(text),
                "image_url": article.top_image,
                "tags": tags
            }
        except: 
            return None

# Self-registration
from app.scrapers.base_scraper import ScraperFactory
ScraperFactory.register("googlenews", GoogleNewsScraper)