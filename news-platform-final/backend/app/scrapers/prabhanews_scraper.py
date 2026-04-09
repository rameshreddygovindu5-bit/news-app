"""
PrabhaNews.com — Telugu news portal.
RSS: https://www.prabhanews.com/feed/
Sections: /andhra-pradesh, /telangana, /politics, /national, /crime, /sports, /movies
"""
import asyncio, logging, feedparser
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

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

class PrabhaNewsScraper(BaseScraper):
    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        for feed_url in SECTION_FEEDS:
            if len(articles) >= self.max_articles: break
            try:
                xml = await self.fetch_url(feed_url)
                if not xml: continue
                feed = feedparser.parse(xml)
                for entry in feed.entries:
                    if len(articles) >= self.max_articles: break
                    link = entry.get("link", "")
                    if not link or link in seen: continue
                    seen.add(link)
                    title = entry.get("title", "")
                    if not title or len(title) < 5: continue

                    pub_date = None
                    for attr in ("published_parsed", "updated_parsed"):
                        p = getattr(entry, attr, None)
                        if p:
                            pub_date = datetime(*p[:6], tzinfo=timezone.utc); break

                    summary = entry.get("summary", "")
                    if summary: summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)
                    image_url = None
                    if hasattr(entry, "media_content") and entry.media_content:
                        image_url = entry.media_content[0].get("url")

                    # Fetch full article
                    content = summary
                    try:
                        html = await self.fetch_url(link)
                        if html:
                            soup = self.parse_html(html)
                            for sel in [".entry-content", ".post-content", "article .content", ".td-post-content"]:
                                elem = soup.select_one(sel)
                                if elem:
                                    full = " ".join(p.get_text(strip=True) for p in elem.find_all("p") if p.get_text(strip=True))
                                    if len(full) > len(content or ""): content = full
                                    break
                            if not image_url:
                                img = soup.select_one(".entry-content img, .post-thumbnail img, article img")
                                if img: image_url = img.get("src") or img.get("data-src")
                    except Exception: pass

                    # newspaper3k fallback
                    if not content or len(content) < 80:
                        try:
                            from app.scrapers.content_extractor import extract_article
                            np_r = await extract_article(link)
                            if np_r.get("success") and len(np_r.get("content","")) > len(content or ""):
                                content = np_r["content"]
                                if not image_url and np_r.get("image_url"): image_url = np_r["image_url"]
                        except Exception: pass

                    await asyncio.sleep(0.3)

                    art = ScrapedArticle(title=title, content=content or "", url=link,
                                         published_at=pub_date or datetime.now(timezone.utc),
                                         image_url=image_url, author="PrabhaNews")
                    if art.is_valid(): articles.append(art)
            except Exception as e:
                logger.warning(f"[PRABHA] Feed error: {e}")
        logger.info(f"[PRABHA] Scraped {len(articles)} articles")
        return articles

ScraperFactory.register("prabhanews", PrabhaNewsScraper)
