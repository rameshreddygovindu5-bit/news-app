"""
Finviz Market News Scraper
==========================
Scrapes ONLY the Market News section from https://finviz.com/news.ashx
(the first table on the page — NOT the Blogs sidebar).

Architecture:
  - Inherits from BaseScraper (same pattern as TOI, Al Jazeera, etc.)
  - Registered with ScraperFactory as "finviz"
  - Extracts headline, URL, source, timestamp for each news item
  - Fetches full article content via newspaper3k (content_extractor)
  - ONLY saves articles where content extraction SUCCEEDS
"""

from __future__ import annotations
import asyncio
import hashlib
import logging
import re
from datetime import datetime, date, timezone
from typing import List, Dict, Optional, Any

from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FINVIZ_URL = "https://finviz.com/news.ashx"

# ── Source branding patterns to strip from scraped content ───────────────────
_SOURCE_PATTERNS = [
    re.compile(r'\(?(PTI|ANI|IANS|Reuters|AP|AFP|Bloomberg|CNBC|WSJ|FT|Yahoo Finance|MarketWatch)\)?\.?\s*', re.I),
    re.compile(r'(?i)subscribe\s+to\s+continue\s+reading.*', re.DOTALL),
    re.compile(r'(?i)this\s+article\s+is\s+for\s+subscribers.*', re.DOTALL),
    re.compile(r'(?i)sign\s+in\s+to\s+read\s+the\s+full.*', re.DOTALL),
    re.compile(r'(?i)already\s+a\s+subscriber\?.*', re.DOTALL),
    re.compile(r'\n{3,}', re.M),
]

def _clean_text(text: str) -> str:
    """Remove source names, paywall notices, and excess whitespace."""
    if not text:
        return ""
    for pat in _SOURCE_PATTERNS:
        text = pat.sub('', text)
    return text.strip()

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Tech": ["ai ", "artificial intelligence", "tech", "apple", "google", "microsoft", "amazon", "nvidia", "chip", "software", "nasdaq"],
    "Business": ["fed ", "federal reserve", "interest rate", "inflation", "gdp", "earnings", "stock", "market", "s&p", "dow", "economy"],
    "World": ["china", "russia", "europe", "nato", "ukraine", "war", "opec", "oil price", "middle east", "israel", "india"],
    "Politics": ["congress", "senate", "white house", "president", "biden", "trump", "republican", "democrat", "legislation", "tax", "policy"],
}

_PAYWALLED_DOMAINS = frozenset(["wsj.com", "barrons.com", "ft.com", "bloomberg.com", "economist.com"])

def _extract_source_from_svg(td_element) -> str:
    svg = td_element.find("svg")
    if not svg: return "Unknown"
    for use in svg.find_all("use"):
        href = use.get("href", "")
        m = re.search(r"#(.+?)(?:-(light|dark))?$", href)
        if m:
            raw = m.group(1).replace("-", " ").title()
            return re.sub(r"\s(Light|Dark)$", "", raw)
    return "Unknown"

def _parse_finviz_time(raw_time: str) -> tuple[str, str]:
    raw = raw_time.strip()
    today = date.today()
    m = re.match(r"^(\d{1,2}:\d{2}(?:AM|PM))$", raw, re.I)
    if m:
        try:
            t = datetime.strptime(m.group(1).upper(), "%I:%M%p").time()
            dt = datetime.combine(today, t, tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), today.isoformat()
        except ValueError: pass
    m = re.match(r"^([A-Za-z]{3})-(\d{1,2})(?:-(\d{2}))?$", raw)
    if m:
        mon, day = m.group(1), int(m.group(2))
        yr = int("20" + m.group(3)) if m.group(3) else today.year
        try:
            dt = datetime.strptime(f"{mon} {day} {yr}", "%b %d %Y").replace(tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), dt.date().isoformat()
        except ValueError: pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), today.isoformat()

def _auto_category(title: str, content: str) -> str:
    text = f"{title} {content[:800]}".lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords): return cat
    return "Business"

class FinvizScraper(BaseScraper):
    """Finviz Market News Scraper."""

    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.headers.update({
            "Referer": "https://www.google.com/",
            "DNT": "1",
        })
        self.max_articles = self.scraper_config.get("max_articles", 50)
        self.skip_paywalled = self.scraper_config.get("skip_paywalled", True)
        self.min_content_len = self.scraper_config.get("min_content_length", 150)
        self.fetch_delay = self.scraper_config.get("fetch_delay_seconds", 0.6)

    async def scrape(self) -> List[ScrapedArticle]:
        logger.info(f"[{self.source_name}] Starting scrape from {FINVIZ_URL}")
        html = await self.fetch_url(FINVIZ_URL)
        if not html: return []
        
        soup = self.parse_html(html)
        tables = soup.find_all("table", class_="styled-table-new")
        if not tables: return []
        
        # Market News is the first table
        rows = tables[0].find_all("tr", class_="news_table-row")
        if not rows:
            rows = [r for r in tables[0].find_all("tr") if r.find("a", class_="nn-tab-link")]
        
        headlines = []
        seen_urls = set()
        for row in rows[:self.max_articles]:
            tds = row.find_all("td")
            if len(tds) < 3: continue
            link_tag = tds[2].find("a", class_="nn-tab-link") or tds[2].find("a", href=True)
            if not link_tag: continue
            
            headline = link_tag.get_text(strip=True)
            url = link_tag.get("href", "").strip()
            if not headline or not url or url in seen_urls: continue
            if not url.startswith("http"): continue
            
            seen_urls.add(url)
            timestamp, _ = _parse_finviz_time(tds[1].get_text(strip=True))
            headlines.append({
                "headline": headline, "url": url, 
                "source": _extract_source_from_svg(tds[0]),
                "timestamp": timestamp
            })
        
        return await self._fetch_all_content(headlines)

    async def _fetch_all_content(self, headlines: List[Dict]) -> List[ScrapedArticle]:
        from app.scrapers.content_extractor import extract_article
        articles = []
        for i, item in enumerate(headlines):
            url = item["url"]
            # Skip paywall
            if self.skip_paywalled:
                from urllib.parse import urlparse
                host = urlparse(url).netloc.lower().lstrip("www.")
                if any(host == dom or host.endswith("." + dom) for dom in _PAYWALLED_DOMAINS):
                    continue

            try:
                result = await extract_article(url)
                if not result.get("success"): continue
                
                content = _clean_text(result.get("content", ""))
                if len(content) < self.min_content_len: continue
                
                title = _clean_text(result.get("title", "").strip() or item["headline"])
                pub_at = result.get("published_at") or datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
                
                article = ScrapedArticle(
                    title=title, content=content, url=url,
                    published_at=pub_at, image_url=result.get("image_url"),
                    author=result.get("author") or item["source"],
                    metadata={"finviz_source": item["source"], "category": _auto_category(title, content)}
                )
                if article.is_valid(): articles.append(article)
                await asyncio.sleep(self.fetch_delay)
            except Exception: continue
            
        logger.info(f"[{self.source_name}] Scraped {len(articles)} valid articles")
        return articles

ScraperFactory.register("finviz", FinvizScraper)

def seed_finviz_source(db_session=None) -> None:
    source_data = {
        "name": "Finviz Market News",
        "url": FINVIZ_URL,
        "language": "en",
        "scraper_type": "finviz",
        "scrape_interval_minutes": 15,
        "ai_processing_interval_minutes": 5,
        "is_enabled": True,
        "is_paused": False,
        "credibility_score": 0.88,
        "priority": 2,
        "scraper_config": {
            "max_articles": 50, "skip_paywalled": True, "min_content_length": 150,
            "fetch_delay_seconds": 0.6, "target_category": "Business", "fetch_full_content": True,
        },
    }
    if db_session:
        from app.models.models import NewsSource
        from sqlalchemy import select
        if not db_session.execute(select(NewsSource).where(NewsSource.url == source_data["url"])).first():
            db_session.add(NewsSource(**source_data))
            db_session.commit()
    else:
        try:
            import sqlite3, json
            conn = sqlite3.connect("newsagg.db")
            cur = conn.cursor()
            cur.execute("SELECT id FROM news_sources WHERE url=?", (source_data["url"],))
            if not cur.fetchone():
                cur.execute("""INSERT INTO news_sources (name, url, language, scraper_type, scrape_interval_minutes, ai_processing_interval_minutes, is_enabled, is_paused, credibility_score, priority, scraper_config) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (source_data["name"], source_data["url"], source_data["language"], source_data["scraper_type"], 15, 5, 1, 0, 0.88, 2, json.dumps(source_data["scraper_config"])))
                conn.commit()
            conn.close()
        except Exception: pass
