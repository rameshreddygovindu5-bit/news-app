"""
OneIndia — English (oneindia.com) and Telugu (telugu.oneindia.com) editions.

English RSS feeds:
  - https://www.oneindia.com/rss/news-fb.xml (top stories)
  - https://www.oneindia.com/rss/india-fb.xml (India)
  - https://www.oneindia.com/rss/international-fb.xml

Telugu RSS:
  - https://telugu.oneindia.com/rss/feeds/oneindia-telugu.xml
  - https://telugu.oneindia.com/rss/feeds/oneindia-telugu-news.xml
"""
import asyncio, logging, feedparser
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)

ENG_FEEDS = [
    "https://www.oneindia.com/rss/news-fb.xml",
    "https://www.oneindia.com/rss/india-fb.xml",
    "https://www.oneindia.com/rss/international-fb.xml",
]
TEL_FEEDS = [
    "https://telugu.oneindia.com/rss/feeds/oneindia-telugu.xml",
    "https://telugu.oneindia.com/rss/feeds/oneindia-telugu-news.xml",
]

class OneIndiaScraper(BaseScraper):
    """Dedicated OneIndia scraper — parses RSS feeds then fetches full article pages."""

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()
        is_telugu = "telugu" in self.source_name.lower() or self.language == "te"
        feeds = TEL_FEEDS if is_telugu else ENG_FEEDS
        tag = "ONEINDIA-TE" if is_telugu else "ONEINDIA-EN"

        for feed_url in feeds:
            if len(articles) >= self.max_articles: break
            try:
                xml = await self.fetch_url(feed_url)
                if not xml: continue
                feed = feedparser.parse(xml)
                logger.info(f"[{tag}] {feed_url.split('/')[-1]}: {len(feed.entries)} entries")

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
                        if p: pub_date = datetime(*p[:6], tzinfo=timezone.utc); break

                    summary = entry.get("summary", "")
                    if summary: summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)
                    image_url = None
                    for attr in ("media_content", "media_thumbnail"):
                        m = getattr(entry, attr, None)
                        if m: image_url = m[0].get("url"); break

                    # Fetch full article
                    content = summary
                    try:
                        html = await self.fetch_url(link)
                        if html:
                            soup = self.parse_html(html)
                            # OneIndia uses .article-desc, .content-txt
                            for sel in [".article-desc", ".content-txt", "#storyBody", ".article-body", ".ad-content-txt"]:
                                elem = soup.select_one(sel)
                                if elem:
                                    full = " ".join(p.get_text(strip=True) for p in elem.find_all("p") if p.get_text(strip=True))
                                    if len(full) > len(content or ""): content = full
                                    break
                            if not image_url:
                                img = soup.select_one(".story-img img, .article-image img, article img")
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
                                         image_url=image_url, author="OneIndia")
                    if art.is_valid(): articles.append(art)
            except Exception as e:
                logger.warning(f"[{tag}] Feed error: {e}")

        logger.info(f"[{tag}] Scraped {len(articles)} articles")
        return articles

ScraperFactory.register("oneindia english", OneIndiaScraper)
ScraperFactory.register("oneindia telugu", OneIndiaScraper)
