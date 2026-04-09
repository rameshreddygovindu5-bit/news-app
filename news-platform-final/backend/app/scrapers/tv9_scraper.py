"""
TV9Telugu.com — Major Telugu news channel.
RSS: https://www.tv9telugu.com/feed
Sections: andhra-pradesh, telangana, national, business, technology, sports, entertainment
"""
import asyncio, logging, feedparser
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)

BASE = "https://www.tv9telugu.com"
RSS_FEEDS = [f"{BASE}/feed"]
HTML_SECTIONS = ["andhra-pradesh", "telangana", "national", "business",
                 "technology", "sports", "entertainment", "international"]

class TV9TeluguScraper(BaseScraper):
    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()

        # RSS first
        for feed_url in RSS_FEEDS:
            if len(articles) >= self.max_articles: break
            xml = await self.fetch_url(feed_url)
            if not xml: continue
            feed = feedparser.parse(xml)
            if feed.entries:
                logger.info(f"[TV9] RSS: {len(feed.entries)} entries")
            for entry in feed.entries:
                if len(articles) >= self.max_articles: break
                link = entry.get("link", "")
                if not link or link in seen: continue
                seen.add(link)
                title = entry.get("title", "")
                if not title: continue
                pub_date = None
                for attr in ("published_parsed", "updated_parsed"):
                    p = getattr(entry, attr, None)
                    if p: pub_date = datetime(*p[:6], tzinfo=timezone.utc); break
                summary = entry.get("summary", "")
                if summary: summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)
                image_url = None
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url")

                content = summary
                try:
                    html = await self.fetch_url(link)
                    if html:
                        soup = self.parse_html(html)
                        for sel in [".article-full-content", ".article-body", ".entry-content", ".story-details"]:
                            elem = soup.select_one(sel)
                            if elem:
                                full = " ".join(p.get_text(strip=True) for p in elem.find_all("p") if p.get_text(strip=True))
                                if len(full) > len(content or ""): content = full
                                break
                        if not image_url:
                            img = soup.select_one(".article-image img, .featured-image img, article img")
                            if img: image_url = img.get("src") or img.get("data-src")
                except Exception: pass
                await asyncio.sleep(0.3)
                art = ScrapedArticle(title=title, content=content or "", url=link,
                                     published_at=pub_date or datetime.now(timezone.utc),
                                     image_url=image_url, author="TV9 Telugu")
                if art.is_valid(): articles.append(art)

        # HTML fallback
        if len(articles) < 5:
            for section in HTML_SECTIONS:
                if len(articles) >= self.max_articles: break
                html = await self.fetch_url(f"{BASE}/{section}")
                if not html: continue
                soup = self.parse_html(html)
                for a in soup.find_all("a", href=True):
                    if len(articles) >= self.max_articles: break
                    href = a["href"]
                    if not href.startswith("http"): href = f"{BASE}{href}"
                    if BASE not in href or href in seen: continue
                    skip = ["/photo", "/video-", "/live", "#", "javascript:", "/tag/"]
                    if any(s in href.lower() for s in skip): continue
                    t = a.get_text(strip=True)
                    if not t or len(t) < 12: continue
                    seen.add(href)
                    from app.scrapers.content_extractor import extract_article
                    r = await extract_article(href)
                    if r.get("success"):
                        art = ScrapedArticle(title=t, content=r["content"], url=href,
                                             published_at=r.get("published_at") or datetime.now(timezone.utc),
                                             image_url=r.get("image_url"), author="TV9 Telugu")
                        if art.is_valid(): articles.append(art)
                    await asyncio.sleep(0.3)

        logger.info(f"[TV9] Scraped {len(articles)} articles")
        return articles

ScraperFactory.register("tv9 telugu", TV9TeluguScraper)
