"""
TeluguTimes.net — Telugu and English news.
Registers for both "telugutimes telugu" and "telugutimes english".
Uses RSS feeds if available, falls back to HTML section scraping.
"""
import asyncio, logging, feedparser
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)

class TeluguTimesScraper(BaseScraper):
    """Works for both Telugu and English editions based on base_url config."""

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        base = self.scraper_config.get("base_url", self.base_url)

        # Try RSS first
        rss_url = self.scraper_config.get("rss_url", f"{base}/feed/")
        xml = await self.fetch_url(rss_url)
        if xml:
            feed = feedparser.parse(xml)
            logger.info(f"[TELUGUTIMES] RSS: {len(feed.entries)} entries")
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
                        for sel in [".entry-content", ".post-content", ".td-post-content", "article .content"]:
                            elem = soup.select_one(sel)
                            if elem:
                                full = " ".join(p.get_text(strip=True) for p in elem.find_all("p") if p.get_text(strip=True))
                                if len(full) > len(content or ""): content = full
                                break
                        if not image_url:
                            img = soup.select_one("article img, .entry-content img")
                            if img: image_url = img.get("src") or img.get("data-src")
                except Exception: pass
                await asyncio.sleep(0.3)
                art = ScrapedArticle(title=title, content=content or "", url=link,
                                     published_at=pub_date or datetime.now(timezone.utc),
                                     image_url=image_url, author="TeluguTimes")
                if art.is_valid(): articles.append(art)
        else:
            # Fallback to HTML scraping
            sections = self.scraper_config.get("sections", [""])
            for section in sections:
                url = f"{base.rstrip('/')}/{section}" if section else base
                html = await self.fetch_url(url)
                if not html: continue
                soup = self.parse_html(html)
                for a in soup.find_all("a", href=True):
                    if len(articles) >= self.max_articles: break
                    href = a["href"]
                    if not href.startswith("http"): href = f"{base.rstrip('/')}/{href.lstrip('/')}"
                    if base not in href or href in seen: continue
                    skip = ["#", "javascript:", "/tag/", "/author/", "/page/"]
                    if any(s in href.lower() for s in skip): continue
                    t = a.get_text(strip=True)
                    if t and len(t) > 12:
                        seen.add(href)
                        from app.scrapers.content_extractor import extract_article
                        r = await extract_article(href)
                        content = r["content"] if r.get("success") else ""
                        img = r.get("image_url")
                        art = ScrapedArticle(title=t, content=content, url=href,
                                             published_at=datetime.now(timezone.utc), image_url=img, author="TeluguTimes")
                        if art.is_valid(): articles.append(art)
                        await asyncio.sleep(0.3)

        logger.info(f"[TELUGUTIMES] Scraped {len(articles)} articles")
        return articles

ScraperFactory.register("telugutimes telugu", TeluguTimesScraper)
ScraperFactory.register("telugutimes english", TeluguTimesScraper)
