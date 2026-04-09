"""
Eenadu.net — Largest Telugu newspaper.
Uses real Eenadu RSS feeds for each section, then fetches full article pages.

RSS feeds verified:
  - https://www.eenadu.net/rss/mainnews-rss.xml (main)
  - https://www.eenadu.net/rss/telangana-rss.xml
  - https://www.eenadu.net/rss/andhrapradesh-rss.xml
  - https://www.eenadu.net/rss/politics-rss.xml
  - https://www.eenadu.net/rss/sports-rss.xml
  - https://www.eenadu.net/rss/business-rss.xml
  - https://www.eenadu.net/rss/movies-rss.xml
  - https://www.eenadu.net/rss/international-rss.xml
"""

import asyncio
import logging
import feedparser
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)

BASE = "https://www.eenadu.net"
RSS_FEEDS = [
    f"{BASE}/rss/mainnews-rss.xml",
    f"{BASE}/rss/telangana-rss.xml",
    f"{BASE}/rss/andhrapradesh-rss.xml",
    f"{BASE}/rss/politics-rss.xml",
    f"{BASE}/rss/sports-rss.xml",
    f"{BASE}/rss/business-rss.xml",
    f"{BASE}/rss/movies-rss.xml",
    f"{BASE}/rss/international-rss.xml",
]


class EenaduScraper(BaseScraper):
    """Eenadu dedicated scraper — RSS feeds + full article page extraction."""

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen_urls = set()

        for feed_url in RSS_FEEDS:
            if len(articles) >= self.max_articles:
                break
            try:
                xml = await self.fetch_url(feed_url)
                if not xml:
                    continue
                feed = feedparser.parse(xml)
                logger.info(f"[EENADU] {feed_url.split('/')[-1]}: {len(feed.entries)} entries")

                for entry in feed.entries:
                    if len(articles) >= self.max_articles:
                        break
                    link = entry.get("link", "")
                    if not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    title = entry.get("title", "")
                    if not title or len(title) < 5:
                        continue

                    # Parse RSS date
                    pub_date = None
                    for attr in ("published_parsed", "updated_parsed"):
                        p = getattr(entry, attr, None)
                        if p:
                            pub_date = datetime(*p[:6], tzinfo=timezone.utc)
                            break

                    # RSS summary as fallback content
                    summary = entry.get("summary", entry.get("description", ""))
                    if summary:
                        summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)

                    # RSS image
                    image_url = None
                    if hasattr(entry, "media_content") and entry.media_content:
                        image_url = entry.media_content[0].get("url")

                    # Fetch full article content
                    content = summary
                    try:
                        html = await self.fetch_url(link)
                        if html:
                            soup = self.parse_html(html)
                            # Eenadu specific: .fullstory, .field-item
                            for sel in [".fullstory", ".field-item.even", "#newsBody", "article .content"]:
                                elem = soup.select_one(sel)
                                if elem:
                                    paras = elem.find_all("p")
                                    if paras:
                                        full = " ".join(p.get_text(strip=True) for p in paras if p.get_text(strip=True))
                                    else:
                                        full = elem.get_text(separator=" ", strip=True)
                                    if len(full) > len(content or ""):
                                        content = full
                                    break
                            # Image from article page
                            if not image_url:
                                img = soup.select_one(".field-items img, .fullstory img, article img")
                                if img:
                                    image_url = img.get("src") or img.get("data-src")
                                    if image_url and not image_url.startswith("http"):
                                        image_url = f"{BASE}{image_url}"
                    except Exception:
                        pass

                    # newspaper3k fallback if CSS selectors got nothing
                    if not content or len(content) < 80:
                        try:
                            from app.scrapers.content_extractor import extract_article
                            np_r = await extract_article(link)
                            if np_r.get("success") and len(np_r.get("content","")) > len(content or ""):
                                content = np_r["content"]
                                if not image_url and np_r.get("image_url"):
                                    image_url = np_r["image_url"]
                        except Exception:
                            pass

                    await asyncio.sleep(0.3)

                    art = ScrapedArticle(
                        title=title, content=content or "", url=link,
                        published_at=pub_date or datetime.now(timezone.utc),
                        image_url=image_url, author="Eenadu",
                    )
                    if art.is_valid():
                        articles.append(art)

            except Exception as e:
                logger.warning(f"[EENADU] Feed error {feed_url}: {e}")

        logger.info(f"[EENADU] Scraped {len(articles)} articles from {len(RSS_FEEDS)} feeds")
        return articles


ScraperFactory.register("eenadu", EenaduScraper)
