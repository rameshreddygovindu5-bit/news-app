"""
CNN.com Dedicated Scraper — Full Site Coverage
================================================
Modelled after the GreatAndhra scraper pattern:
  Phase 1 — Collect article URLs from all CNN section listing pages
  Phase 2 — Fetch each article page SEQUENTIALLY with rate-limiting

Supports: https://www.cnn.com (English)
"""
import re
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from bs4 import BeautifulSoup
import httpx

from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)

CNN_BASE = "https://www.cnn.com"

CNN_SECTIONS = [
    "",            # Homepage
    "world",
    "politics",
    "us",
    "health",
    "tech",
    "business",
    "entertainment",
    "style",
    "travel",
    "science",
    "sport",
]

EXCLUDE_SUBSTRINGS = [
    "/terms", "/privacy", "/ad-choices", "/cnn-underscored",
    "/specials", "/about", "/careers", "/vr/", "/live-news",
    "cnnespanol", "edition.cnn.com", "/search?", "/programs/",
    "cnn-10", "/audio/", "javascript:", "mailto:",
]

DATE_PATTERNS = [
    re.compile(r"(\w+ \d{1,2},\s*\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM)\s*ET)", re.I),
    re.compile(r"(?:Updated|Published)[: ]+(\w+ \d{1,2},\s*\d{4})", re.I),
]

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}


def _parse_date(text: str) -> Optional[datetime]:
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                return datetime.strptime(m.group(1).strip(), "%B %d, %Y").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, IndexError):
                continue
    return None


def _is_excluded(url: str) -> bool:
    return any(ex in url.lower() for ex in EXCLUDE_SUBSTRINGS)


def _is_article_url(url: str) -> bool:
    if not url or _is_excluded(url):
        return False
    if "cnn.com" not in url:
        return False
    path = url.replace("https://www.cnn.com", "").replace("https://cnn.com", "")
    segments = [s for s in path.split("/") if s]
    if len(segments) < 2:
        return False
    # Date-based paths like /2024/11/05/politics/...
    if re.match(r"\d{4}", segments[0]) and len(segments) >= 4:
        return True
    # Section/slug paths
    if len(segments) >= 2 and len(segments[-1]) > 5:
        return True
    return False


class CNNScraper(BaseScraper):
    """
    Full-coverage CNN.com scraper using two-phase approach:
      Phase 1: Collect article URLs from section listing pages.
      Phase 2: Fetch each article page SEQUENTIALLY (prevents 429 rate-limiting).

    Config keys (set on NewsSource.scraper_config JSON):
      max_articles      : hard cap (default 500)
      section_max_pages : pagination pages per section (default 3)
      request_delay     : seconds between requests (default 0.8)
      fetch_full_content: fetch individual article pages (default True)
      max_retries       : retries per URL (default 2)
      sections          : list of sections to scrape (default CNN_SECTIONS)
    """

    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)
        self.base = CNN_BASE
        self.max_articles: int = min(
            self.scraper_config.get("max_articles", 500), 1000
        )
        self.section_max_pages: int = self.scraper_config.get("section_max_pages", 3)
        self.request_delay: float = float(self.scraper_config.get("request_delay", 0.8))
        self.fetch_full_content: bool = self.scraper_config.get("fetch_full_content", True)
        self.max_retries: int = self.scraper_config.get("max_retries", 2)
        self.sections: List[str] = self.scraper_config.get("sections", CNN_SECTIONS)

    # ── Helpers ───────────────────────────────────────────────────────

    def _normalize(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.base + url
        if not url.startswith("http"):
            return ""
        return url

    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch a URL with delay + exponential-backoff retry."""
        for attempt in range(1, self.max_retries + 2):
            await asyncio.sleep(self.request_delay)
            try:
                async with httpx.AsyncClient(
                    timeout=20.0,
                    follow_redirects=True,
                    headers=SCRAPE_HEADERS,
                ) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        return resp.text
                    if resp.status_code in (403, 429):
                        wait = self.request_delay * attempt * 3
                        logger.warning(
                            f"[CNN] Rate-limited ({resp.status_code}) {url} — wait {wait:.1f}s"
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.debug(f"[CNN] HTTP {resp.status_code} for {url}")
            except httpx.TimeoutException:
                logger.warning(f"[CNN] Timeout attempt {attempt} for {url}")
            except Exception as exc:
                logger.debug(f"[CNN] Fetch error attempt {attempt}: {exc}")
            if attempt <= self.max_retries:
                await asyncio.sleep(self.request_delay * attempt)
        return None

    # ── Phase 1: Link Collection ──────────────────────────────────────

    def _extract_links(self, html: str, seen: Set[str]) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        new_articles: List[Dict] = []

        for a_tag in soup.find_all("a", href=True):
            href = self._normalize(a_tag.get("href", ""))
            if not href or not _is_article_url(href) or href in seen:
                continue

            # Derive title from headline child elements
            title = ""
            for sel in [
                "span.container__headline-text",
                "h3.container__headline",
                "div.container__headline-text",
                "span", "h3", "h2",
            ]:
                el = a_tag.select_one(sel)
                if el:
                    t = el.get_text(strip=True)
                    if t and len(t) > 10:
                        title = t
                        break
            if not title:
                title = (
                    a_tag.get("aria-label", "").strip()
                    or a_tag.get("title", "").strip()
                    or a_tag.get_text(strip=True)
                )
            if not title or len(title) < 15:
                continue

            seen.add(href)

            # Extract image from enclosing card
            image_url = None
            card = a_tag.find_parent(
                lambda t: t.name in ("article", "div", "li", "section")
                and any(
                    cls in " ".join(t.get("class", []))
                    for cls in ("container", "card", "item", "story", "media")
                ),
            )
            if card:
                img = card.find("img")
                if img:
                    src = (
                        img.get("src") or img.get("data-src")
                        or img.get("data-original") or ""
                    )
                    if src and src.startswith("http"):
                        image_url = src

            new_articles.append({
                "url": href, "title": title,
                "image_url": image_url, "published_at": None,
            })
        return new_articles

    async def collect_all_links(self) -> List[Dict]:
        """Phase 1 — Crawl CNN section pages and collect article URLs."""
        seen_urls: Set[str] = set()
        all_articles: List[Dict] = []

        for section in self.sections:
            if len(all_articles) >= self.max_articles:
                break

            label = section or "homepage"
            section_count = 0
            consecutive_empty = 0

            for page_num in range(1, self.section_max_pages + 1):
                if len(all_articles) >= self.max_articles:
                    break

                url = f"{self.base}/{section}" if section else self.base
                if page_num > 1:
                    url = f"{url}?page={page_num}"

                html = await self._fetch(url)
                if not html:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
                    continue

                new_links = self._extract_links(html, seen_urls)
                if not new_links:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
                    continue
                else:
                    consecutive_empty = 0

                all_articles.extend(new_links)
                section_count += len(new_links)

            if section_count > 0:
                logger.info(
                    f"[CNN] /{label}: +{section_count} → {len(all_articles)} total"
                )

        logger.info(f"[CNN] Link collection done: {len(all_articles)} URLs")
        return all_articles

    # ── Phase 2: Article Content ──────────────────────────────────────

    async def fetch_article_content(self, url: str) -> Dict:
        result = {
            "title": "", "content": "", "author": "",
            "published_at": None, "image_url": "", "tags": [],
        }
        html = await self._fetch(url)
        if not html:
            return result

        soup = BeautifulSoup(html, "lxml")

        # Title
        h1 = soup.find("h1")
        result["title"] = h1.get_text(strip=True) if h1 else ""
        if not result["title"]:
            og = soup.find("meta", property="og:title")
            if og:
                result["title"] = og.get("content", "").strip()

        # Date
        date_meta = soup.find("meta", attrs={"property": "article:published_time"})
        if date_meta:
            try:
                result["published_at"] = datetime.fromisoformat(
                    date_meta.get("content", "").replace("Z", "+00:00")
                )
            except ValueError:
                pass
        if not result["published_at"]:
            result["published_at"] = _parse_date(soup.get_text(" ", strip=True))

        # Author
        author_el = soup.select_one(
            "div.byline__name, span.byline__name, div.article__byline"
        )
        if author_el:
            raw = re.sub(r"(?i)^by\s+", "", author_el.get_text(strip=True))
            if raw and len(raw) < 100:
                result["author"] = raw

        # Hero image
        og_img = soup.find("meta", property="og:image")
        if og_img:
            result["image_url"] = og_img.get("content", "").strip()
        if not result["image_url"]:
            hero = soup.select_one("div.article__media img, picture img")
            if hero:
                result["image_url"] = hero.get("src") or hero.get("data-src", "")

        # Body content
        STOP = re.compile(
            r"Sign up|Subscribe|Newsletter|Follow CNN|©\s*\d{4}|More from CNN",
            re.I,
        )
        NOISE = re.compile(
            r"related|sidebar|footer|ad-|promo|social|share|gallery|video|caption|subscribe",
            re.I,
        )

        body = soup.select_one(
            "div.article__content, div.article-body__content, "
            "div.zn-body__read-all, main article, div[class*='article-body']"
        )
        source = body if body else soup
        parts: List[str] = []
        for el in source.find_all(["p", "h2", "h3", "blockquote"]):
            if el.find_parent(
                lambda t: t.get("class")
                and re.search(NOISE, " ".join(t.get("class", [])))
            ):
                continue
            text = el.get_text(strip=True)
            if not text or len(text) < 20 or text == result["title"]:
                continue
            if STOP.search(text):
                continue
            if text not in parts:
                parts.append(text)
        result["content"] = "\n\n".join(parts)

        # Tags
        tag_els = soup.select("a.metadata__tag, div.article-sub-topics a")
        result["tags"] = [t.get_text(strip=True) for t in tag_els if t.get_text(strip=True)]

        return result

    # ── Main Pipeline ─────────────────────────────────────────────────

    async def scrape(self) -> List[ScrapedArticle]:
        """
        Full two-phase CNN scrape:
          1. Collect links from all sections.
          2. Fetch each article SEQUENTIALLY (prevents server rate-limiting).
        """
        logger.info("[CNN] ═══ Starting CNN.com scrape ═══")

        article_links = await self.collect_all_links()
        if not article_links:
            logger.warning("[CNN] No article links found")
            return []

        articles: List[ScrapedArticle] = []
        failed = 0
        total = len(article_links)
        logger.info(f"[CNN] === Fetching {total} articles SEQUENTIALLY ===")

        for i, link_data in enumerate(article_links):
            url = link_data["url"]
            listing_title = link_data["title"]

            try:
                if self.fetch_full_content:
                    data = await self.fetch_article_content(url)
                    title = data["title"] or listing_title
                    content = data["content"]
                    author = data["author"]
                    image_url = data["image_url"] or link_data.get("image_url")
                    published_at = data["published_at"] or link_data.get("published_at")
                    tags = data.get("tags", [])
                else:
                    title = listing_title
                    content = listing_title
                    author = None
                    image_url = link_data.get("image_url")
                    published_at = link_data.get("published_at")
                    tags = []

                if not title or len(title) < 10:
                    continue

                article = ScrapedArticle(
                    title=title,
                    content=content or title,
                    url=url,
                    published_at=published_at or datetime.now(timezone.utc),
                    image_url=image_url,
                    author=author,
                    metadata={
                        "source": "CNN",
                        "tags": tags,
                        "language": "en",
                        "has_full_content": bool(content and len(content) > 80),
                        "content_length": len(content) if content else 0,
                    },
                )

                if article.is_valid():
                    articles.append(article)

                if (i + 1) % 20 == 0:
                    logger.info(
                        f"[CNN] Progress: {i+1}/{total} fetched, "
                        f"{len(articles)} valid, {failed} failed"
                    )

            except Exception as exc:
                failed += 1
                logger.error(f"[CNN] Error on {url}: {exc}")
                continue

        logger.info(
            f"[CNN] ═══ SCRAPE COMPLETE ═══\n"
            f"[CNN]   Total links    : {total}\n"
            f"[CNN]   Valid articles : {len(articles)}\n"
            f"[CNN]   Failed         : {failed}"
        )
        return articles


# Register all name variants a CNN source might use
ScraperFactory.register("cnn", CNNScraper)
ScraperFactory.register("cnn live", CNNScraper)
ScraperFactory.register("cnn.com", CNNScraper)
ScraperFactory.register("CNN", CNNScraper)
