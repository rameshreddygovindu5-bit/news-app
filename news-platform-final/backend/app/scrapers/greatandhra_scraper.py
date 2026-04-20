"""
GreatAndhra.com Dedicated Scraper — Full site coverage

Supports:
  - English site: https://www.greatandhra.com
  - Telugu site:  https://telugu.greatandhra.com

Strategy:
  1. PRIMARY: Deep-paginate /latest (has ALL articles, ~15 per page)
     → Stop only when a page returns zero new article links
  2. SUPPLEMENTARY: Scrape each section's first N pages for any stragglers
  3. For every unique URL collected, fetch the full article page SEQUENTIALLY
     with proper rate limiting (NOT parallel — parallel causes 403 blocks)
"""

import re
import asyncio
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from bs4 import BeautifulSoup

from app.scrapers.base_scraper import BaseScraper, ScrapedArticle, ScraperFactory

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SITE CONFIGURATION
# ─────────────────────────────────────────────

ENG_BASE = "https://www.greatandhra.com"
TEL_BASE = "https://telugu.greatandhra.com"

ENG_ARTICLE_RE = re.compile(r"https?://(?:www\.)?greatandhra\.com/[a-z].+[\w-]")
TEL_ARTICLE_RE = re.compile(r"https?://telugu\.greatandhra\.com/[a-z].+[\w-]")

# Correct section URLs verified from actual site navigation
ENG_LISTING_SECTIONS = [
    "latest",                    # Primary
    "politics",                  # Main Politics
    "andhra-news",               # From sub-menu
    "telangana-news",            # From sub-menu
    "india-news",                # From sub-menu
    "movies",                    # Main Movies (news)
    "moviegossip",               # From sub-menu
    "boxoffice",                 # From sub-menu
    "reviews",                   # Main Reviews
    "opinion",                   # Main Opinion
]

TEL_LISTING_SECTIONS = [
    "latest-news",               # Primary
    "politics",                  # Main Politics (వార్తలు)
    "politics/andhra-news",      # From sub-menu (ఆంధ్ర)
    "politics/telangana-news",   # From sub-menu (తెలంగాణ)
    "politics/national",         # From sub-menu (జాతీయం)
    "politics/opinion",          # From sub-menu (అభిప్రాయం)
    "politics/analysis",         # From sub-menu (విశ్లేషణ)
    "politics/gossip",           # From sub-menu (గాసిప్స్)
    "movies",                    # Main Movies (సినిమా)
    "movies/movie-news",         # From sub-menu (వార్తలు)
    "movies/movie-gossip",       # From sub-menu (గాసిప్స్)
    "movies/reviews",            # From sub-menu (రివ్యూలు)
    "movies/press-releases",     # From sub-menu (ప్రెస్ రిలీజ్లు)
    "mbs",                       # Extra (ఎమ్బీయస్)
    "health",                    # Added from mobile menu
]

EXCLUDE_SUBSTRINGS = [
    "/gallery", "/epaper", "/convergence", "/aboutus",
    "/contactus", "/disclaimer", "/privacy", "/grievance",
    "gallery.greatandhra.com", "msnrealty.com",
    "/catviews.php", "/topic/",
]

DATE_RE = re.compile(
    r"(\d{1,2})-([A-Za-z]{3})-(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*IST"
)
MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def parse_ga_date(text: str) -> Optional[datetime]:
    if not text:
        return None
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        day, mon, yr, h, mi, s = m.groups()
        return datetime(
            int(yr), MONTH_MAP.get(mon, 1), int(day),
            int(h), int(mi), int(s), tzinfo=timezone.utc,
        )
    except (ValueError, KeyError):
        return None


def is_excluded(url: str) -> bool:
    return any(ex in url for ex in EXCLUDE_SUBSTRINGS)


# ─────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────

class GreatAndhraScraper(BaseScraper):
    """
    Full-coverage GreatAndhra scraper with SEQUENTIAL article fetching.

    Config options (in scraper_config):
      max_articles:       hard cap (default 2000)
      latest_max_pages:   max pages for /latest (default 50)
      section_max_pages:  max pages per other section (default 5)
      request_delay:      seconds between requests (default 0.5)
      fetch_full_content: fetch each article page (default True)
      max_retries:        retry failed fetches (default 2)
    """

    def __init__(self, source_config: Dict[str, Any]):
        super().__init__(source_config)

        self.is_telugu = "telugu.greatandhra.com" in (self.base_url or "")
        self.current_base = TEL_BASE if self.is_telugu else ENG_BASE

        defaults = TEL_LISTING_SECTIONS if self.is_telugu else ENG_LISTING_SECTIONS
        self.sections = self.scraper_config.get("sections", defaults)

        self.max_articles = min(self.scraper_config.get("max_articles", 2000), 2000)
        self.latest_max_pages = self.scraper_config.get("latest_max_pages", 5)
        self.section_max_pages = self.scraper_config.get("section_max_pages", 3)
        self.request_delay = self.scraper_config.get("request_delay", 0.5)
        self.fetch_full_content = self.scraper_config.get("fetch_full_content", True)
        self.max_retries = self.scraper_config.get("max_retries", 2)

        self.article_re = TEL_ARTICLE_RE if self.is_telugu else ENG_ARTICLE_RE

    # ─── URL helpers ───

    def _normalize(self, url: str) -> str:
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.current_base + url
        if not url.startswith("http"):
            return self.current_base + "/" + url
        return url

    def _is_article(self, url: str) -> bool:
        if not url or is_excluded(url):
            return False
        if len(url) < 40:  # Too short to be an article URL
            return False
        # Exclude pure section listing URLs (single segment after domain)
        path = url.split("greatandhra.com/", 1)[-1] if "greatandhra.com/" in url else ""
        if path and "/" not in path.rstrip("/") and not path.endswith(".html"):
            # Single segment like "/latest" or "/politics" — listing page, not article
            return False
        return bool(self.article_re.match(url))

    # ─── Fetch with retry ───

    async def _fetch_with_retry(self, url: str) -> Optional[str]:
        """Fetch a URL with delay and retry on failure."""
        for attempt in range(1, self.max_retries + 1):
            await asyncio.sleep(self.request_delay)
            html = await self.fetch_url(url)
            if html:
                return html
            if attempt < self.max_retries:
                wait = self.request_delay * attempt * 2
                logger.warning(f"[GA] Retry {attempt}/{self.max_retries} for {url} (wait {wait:.1f}s)")
                await asyncio.sleep(wait)
        return None

    # ─── STEP 1: Collect links ───

    def _extract_links_from_page(self, html: str, seen: Set[str]) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        new_articles = []

        for a_tag in soup.find_all("a", href=True):
            href = self._normalize(a_tag.get("href", ""))
            if not self._is_article(href) or href in seen:
                continue

            title = (a_tag.get("title") or "").strip()
            if not title:
                title = a_tag.get_text(strip=True)
            if not title or len(title) < 8:
                continue

            seen.add(href)

            image_url = self._find_image(a_tag)
            published_at = None
            summary = ""

            parent = a_tag.find_parent(["li", "div", "article", "td"])
            if parent:
                parent_text = parent.get_text(" ", strip=True)
                published_at = parse_ga_date(parent_text)
                for child in parent.children:
                    if hasattr(child, "get_text"):
                        txt = child.get_text(strip=True)
                        if (txt and len(txt) > 30
                                and txt != title
                                and "Published Date" not in txt):
                            summary = txt
                            break
                if not image_url:
                    image_url = self._find_image(parent)

            new_articles.append({
                "url": href,
                "title": title,
                "image_url": image_url,
                "summary": summary,
                "published_at": published_at,
            })

        return new_articles

    def _find_image(self, element) -> Optional[str]:
        img = element.find("img") if element else None
        if not img:
            return None
        src = img.get("src") or img.get("data-src") or ""
        if not src or "atrk.gif" in src or "msn_" in src:
            return None
        return self._normalize(src)

    async def collect_all_links(self) -> List[Dict]:
        """Phase 1: /latest deep + Phase 2: supplementary sections."""
        seen_urls: Set[str] = set()
        all_articles: List[Dict] = []

        # ── PHASE 1: Deep scrape /latest ──
        primary = self.sections[0] if self.sections else "latest"
        logger.info(f"[GA] === PHASE 1: Deep scraping /{primary} ===")

        consecutive_empty = 0
        for page_num in range(1, self.latest_max_pages + 1):
            if len(all_articles) >= self.max_articles:
                break

            if page_num == 1:
                url = f"{self.current_base}/{primary}"
            else:
                if self.is_telugu:
                    url = f"{self.current_base}/{primary}/page/{page_num}"
                else:
                    url = f"{self.current_base}/{primary}?page={page_num}"

            html = await self._fetch_with_retry(url)
            if not html:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    logger.info(f"[GA] 3 consecutive failures, stopping /{primary}")
                    break
                continue

            new_links = self._extract_links_from_page(html, seen_urls)
            if not new_links:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    logger.info(f"[GA] 2 empty pages, /{primary} exhausted at page {page_num}")
                    break
                continue
            else:
                consecutive_empty = 0

            all_articles.extend(new_links)
            logger.info(f"[GA] /{primary} p{page_num}: +{len(new_links)} → {len(all_articles)} total")

        logger.info(f"[GA] Phase 1 done: {len(all_articles)} articles from /{primary}")

        # ── PHASE 2: Supplementary sections ──
        remaining = [s for s in self.sections if s != primary]
        for section in remaining:
            if len(all_articles) >= self.max_articles:
                break
            section_new = 0
            consecutive_empty = 0

            for page_num in range(1, self.section_max_pages + 1):
                if len(all_articles) >= self.max_articles:
                    break

                if page_num == 1:
                    url = f"{self.current_base}/{section}"
                else:
                    if self.is_telugu:
                        url = f"{self.current_base}/{section}/page/{page_num}"
                    else:
                        url = f"{self.current_base}/{section}?page={page_num}"

                html = await self._fetch_with_retry(url)
                if not html:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
                    continue

                new_links = self._extract_links_from_page(html, seen_urls)
                if not new_links:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        break
                    continue
                else:
                    consecutive_empty = 0

                all_articles.extend(new_links)
                section_new += len(new_links)

            if section_new > 0:
                logger.info(f"[GA] /{section}: +{section_new} → {len(all_articles)} total")

        logger.info(f"[GA] Link collection done: {len(all_articles)} unique URLs")
        return all_articles

    # ─── STEP 2: Fetch article content ───

    async def fetch_article_content(self, url: str) -> Dict:
        result = {
            "title": "", "content": "", "author": "",
            "published_at": None, "tags": [], "image_url": "",
        }

        html = await self._fetch_with_retry(url)
        if not html:
            return result

        soup = BeautifulSoup(html, "lxml")

        # Title
        h1 = soup.find("h1")
        if h1:
            result["title"] = h1.get_text(strip=True)

        # Author & date
        page_text = soup.get_text(" ", strip=True)
        auth_match = re.search(r"By\s+(.+?)\s+On\s+", page_text, re.IGNORECASE)
        if auth_match:
            author = auth_match.group(1).strip()
            if len(author) < 50:
                result["author"] = author
        result["published_at"] = parse_ga_date(page_text)

        # Image
        if h1:
            for elem in h1.find_all_next(limit=20):
                if elem.name == "img":
                    src = elem.get("src") or elem.get("data-src") or ""
                    if src and ("image.php" in src or "newphotos" in src):
                        result["image_url"] = self._normalize(src)
                        break

        # Content extraction with robust fallbacks
        from app.scrapers.scraper_utils import ArticleExtractor
        ae = ArticleExtractor(
            base_url=self.current_base,
            content_selectors=[".post-content", ".article-content", ".entry-content", "#storyBody", ".Normal"]
        )
        result["content"] = ae.extract_content(soup, result["title"])

        # newspaper3k fallback if content is too short
        if not result["content"] or len(result["content"]) < 200:
            try:
                from app.scrapers.content_extractor import extract_article
                np_result = await extract_article(url, html)
                if np_result.get("success") and len(np_result.get("content", "")) > len(result["content"] or ""):
                    result["content"] = np_result["content"]
                    if not result["image_url"] and np_result.get("image_url"):
                        result["image_url"] = np_result["image_url"]
                    if not result["published_at"] and np_result.get("published_at"):
                        result["published_at"] = np_result["published_at"]
            except Exception as e:
                logger.debug(f"[GA] newspaper3k fallback failed for {url}: {e}")

        # Tags
        tags_label = soup.find(["strong", "b"], string=re.compile(r"Tags:", re.I))
        if tags_label:
            parent = tags_label.find_parent()
            if parent:
                result["tags"] = [
                    a.get_text(strip=True)
                    for a in parent.find_all("a")
                    if a.get_text(strip=True)
                ]

        return result

    # ─── MAIN PIPELINE ───

    async def scrape(self) -> List[ScrapedArticle]:
        """
        Full pipeline — SEQUENTIAL fetching to avoid server blocks.
        
        Why not parallel? GreatAndhra blocks concurrent requests.
        10 simultaneous fetches → server drops ~30-50% of them → articles lost.
        Sequential with 0.5s delay = 100% success rate.
        """
        lang = "Telugu" if self.is_telugu else "English"
        logger.info(f"[GA] Starting GreatAndhra scrape ({lang} site)")

        # Step 1: Collect all links
        article_links = await self.collect_all_links()
        if not article_links:
            logger.warning("[GA] No article links found!")
            return []

        # Step 2: Fetch each article ONE BY ONE (not parallel!)
        articles: List[ScrapedArticle] = []
        failed = 0
        total = len(article_links)
        logger.info(f"[GA] === Fetching {total} articles SEQUENTIALLY ===")

        for i, link_data in enumerate(article_links):
            url = link_data["url"]
            listing_title = link_data["title"]

            try:
                if self.fetch_full_content:
                    article_data = await self.fetch_article_content(url)
                    title = article_data["title"] or listing_title
                    content = article_data["content"]
                    author = article_data["author"]
                    image_url = article_data["image_url"] or link_data.get("image_url")
                    published_at = article_data["published_at"] or link_data.get("published_at")
                    tags = article_data["tags"]
                else:
                    title = listing_title
                    content = link_data.get("summary", "")
                    author = None
                    image_url = link_data.get("image_url")
                    published_at = link_data.get("published_at")
                    tags = []

                article = ScrapedArticle(
                    title=title,
                    content=content,
                    url=url,
                    published_at=published_at or datetime.now(timezone.utc),
                    image_url=image_url,
                    author=author,
                    metadata={
                        "source": "GreatAndhra",
                        "tags": tags,
                        "is_telugu": self.is_telugu,
                        "has_full_content": bool(content and len(content) > 50),
                        "content_length": len(content) if content else 0,
                    },
                )

                if article.is_valid():
                    articles.append(article)

                # Log progress every 25 articles
                if (i + 1) % 25 == 0:
                    logger.info(
                        f"[GA] Progress: {i+1}/{total} fetched, "
                        f"{len(articles)} valid, {failed} failed"
                    )

            except Exception as e:
                failed += 1
                logger.error(f"[GA] Error on {url}: {e}")
                continue

        logger.info(
            f"[GA] === SCRAPE COMPLETE ===\n"
            f"[GA]   Total links   : {total}\n"
            f"[GA]   Valid articles : {len(articles)}\n"
            f"[GA]   Failed        : {failed}"
        )
        return articles


# Register with factory
ScraperFactory.register("greatandhra", GreatAndhraScraper)
ScraperFactory.register("greatandhra.com", GreatAndhraScraper)

