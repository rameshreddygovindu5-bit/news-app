"""
AlJazeera.com — International English news.
RSS: https://www.aljazeera.com/xml/rss/all.xml

AlJazeera content selectors (verified 2025):
  - .wysiwyg (main article body)
  - .article__body-text (newer layout)
  - #main-content-area (fallback)
  
Falls back to newspaper3k if CSS selectors fail.
"""
import asyncio, logging, feedparser
from datetime import datetime, timezone
from typing import List
from bs4 import BeautifulSoup
from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RSS_FEEDS = [
    "https://www.aljazeera.com/xml/rss/all.xml",
]

# AlJazeera content selectors — ordered by reliability
CONTENT_SELECTORS = [
    ".wysiwyg--all-content",
    ".wysiwyg",
    ".article__body-text",
    ".article-body",
    "#main-content-area",
    "main article",
    ".post-content",
]

IMAGE_SELECTORS = [
    ".article-featured-image img",
    ".responsive-image img",
    ".main-article-media img",
    "figure.article-featured-image img",
    "picture source",
    "article img",
]


class AlJazeeraScraper(BaseScraper):
    """AlJazeera dedicated scraper — RSS + full article extraction with newspaper3k fallback."""

    def __init__(self, source_config):
        super().__init__(source_config)
        self.max_articles = self.scraper_config.get("max_articles", settings.MAX_ARTICLES_PER_SCRAPE)

    async def scrape(self) -> List[ScrapedArticle]:
        articles = []
        seen = set()

        for feed_url in RSS_FEEDS:
            if len(articles) >= self.max_articles:
                break
            xml = await self.fetch_url(feed_url)
            if not xml:
                continue
            feed = feedparser.parse(xml)
            logger.info(f"[ALJAZEERA] RSS: {len(feed.entries)} entries")

            for entry in feed.entries:
                if len(articles) >= self.max_articles:
                    break
                link = entry.get("link", "")
                if not link or link in seen:
                    continue
                if link.startswith("/"):
                    link = f"https://www.aljazeera.com{link}"
                seen.add(link)

                title = entry.get("title", "")
                if not title or len(title) < 5:
                    continue

                # Parse date
                pub_date = None
                for attr in ("published_parsed", "updated_parsed"):
                    p = getattr(entry, attr, None)
                    if p:
                        pub_date = datetime(*p[:6], tzinfo=timezone.utc)
                        break

                # RSS summary
                summary = entry.get("summary", "")
                if summary:
                    summary = BeautifulSoup(summary, "lxml").get_text(separator=" ", strip=True)

                # RSS image
                image_url = None
                if hasattr(entry, "media_content") and entry.media_content:
                    image_url = entry.media_content[0].get("url")
                elif hasattr(entry, "links"):
                    for lnk in entry.links:
                        if lnk.get("type", "").startswith("image"):
                            image_url = lnk.get("href")
                            break

                # ── FULL CONTENT EXTRACTION ──
                content = summary
                try:
                    html = await self.fetch_url(link)
                    if html:
                        soup = self.parse_html(html)

                        # Try CSS selectors first
                        extracted = ""
                        for sel in CONTENT_SELECTORS:
                            elem = soup.select_one(sel)
                            if elem:
                                paras = elem.find_all("p")
                                if paras:
                                    extracted = " ".join(
                                        p.get_text(strip=True)
                                        for p in paras
                                        if p.get_text(strip=True) and len(p.get_text(strip=True)) > 20
                                    )
                                else:
                                    extracted = elem.get_text(separator=" ", strip=True)
                                if len(extracted) > 100:
                                    break
                                extracted = ""

                        # Use CSS result if good, otherwise fall back to newspaper3k
                        if len(extracted) > 100:
                            content = extracted
                        else:
                            from app.scrapers.content_extractor import extract_article
                            np_result = await extract_article(link, html)
                            if np_result.get("success") and len(np_result.get("content", "")) > 50:
                                content = np_result["content"]
                                logger.debug(f"[ALJAZEERA] newspaper3k fallback used for {link}")
                            else:
                                # Use RSS summary as fallback instead of empty
                                content = summary if summary else extracted
                                logger.warning(f"[ALJAZEERA] Both extraction methods failed for {link}, using RSS summary")

                        # Image from article page
                        if not image_url:
                            for img_sel in IMAGE_SELECTORS:
                                img = soup.select_one(img_sel)
                                if img:
                                    image_url = img.get("src") or img.get("data-src") or img.get("srcset", "").split(",")[0].split(" ")[0]
                                    if image_url and not image_url.startswith("http"):
                                        image_url = f"https://www.aljazeera.com{image_url}"
                                    if image_url:
                                        break
                except Exception as e:
                    logger.warning(f"[ALJAZEERA] Content extraction failed for {link}: {e}")

                await asyncio.sleep(0.3)

                art = ScrapedArticle(
                    title=title,
                    content=content or "",
                    url=link,
                    published_at=pub_date or datetime.now(timezone.utc),
                    image_url=image_url,
                    author="Al Jazeera",
                )
                if art.is_valid():
                    articles.append(art)

        logger.info(f"[ALJAZEERA] Scraped {len(articles)} articles")
        return articles


ScraperFactory.register("aljazeera", AlJazeeraScraper)
ScraperFactory.register("al jazeera", AlJazeeraScraper)
