"""
Telugu123.com — Telugu entertainment and news.
HTML scraper — scrapes section listing pages then fetches article detail.
Sections: /news, /movies, /reviews, /political-news
"""
import asyncio, logging
from datetime import datetime, timezone
from typing import List
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)
BASE = "https://www.telugu123.com"
SECTIONS = ["news", "movies", "reviews", "political-news", "gossips"]

class Telugu123Scraper(BaseScraper):
    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen, urls = set(), []
        for section in SECTIONS:
            html = await self.fetch_url(f"{BASE}/{section}")
            if not html: continue
            soup = self.parse_html(html)
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if not href.startswith("http"): href = f"{BASE}/{href.lstrip('/')}"
                if BASE not in href or href in seen: continue
                skip = ["/photo", "/video", "#", "javascript:", "/tag/", "/page/"]
                if any(s in href.lower() for s in skip): continue
                t = a.get_text(strip=True)
                if t and len(t) > 12 and len(href) > len(BASE) + 10:
                    seen.add(href); urls.append((href, t))
            await asyncio.sleep(0.3)
        logger.info(f"[TELUGU123] {len(urls)} URLs")

        for url, title in urls[:self.max_articles]:
            try:
                html = await self.fetch_url(url)
                if not html: continue
                soup = self.parse_html(html)
                content, image_url = "", None
                for sel in [".entry-content", ".post-content", ".article-body", "article"]:
                    elem = soup.select_one(sel)
                    if elem:
                        content = " ".join(p.get_text(strip=True) for p in elem.find_all("p") if p.get_text(strip=True))
                        if content: break
                if not content:
                    from app.scrapers.content_extractor import extract_article
                    r = await extract_article(url, html)
                    if r.get("success"): content = r["content"]
                img = soup.select_one(".entry-content img, .post-thumbnail img, article img")
                if img: image_url = img.get("src") or img.get("data-src")
                art = ScrapedArticle(title=title, content=content or "", url=url,
                                     published_at=datetime.now(timezone.utc), image_url=image_url, author="Telugu123")
                if art.is_valid(): articles.append(art)
                await asyncio.sleep(0.3)
            except Exception as e: logger.warning(f"[TELUGU123] {url}: {e}")
        logger.info(f"[TELUGU123] Scraped {len(articles)} articles")
        return articles

ScraperFactory.register("telugu123", Telugu123Scraper)
