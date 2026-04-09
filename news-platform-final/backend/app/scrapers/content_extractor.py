"""newspaper3k wrapper — extracts full article from any URL."""
import asyncio, logging
from datetime import timezone
from typing import Dict
logger = logging.getLogger(__name__)

def _extract_sync(url: str, html: str = None) -> Dict:
    try:
        from newspaper import Article, Config
        cfg = Config()
        cfg.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        cfg.request_timeout = 15; cfg.fetch_images = True; cfg.memoize_articles = False
        a = Article(url, config=cfg)
        if html: a.set_html(html)
        else: a.download()
        a.parse()
        pd = a.publish_date
        if pd and pd.tzinfo is None: pd = pd.replace(tzinfo=timezone.utc)
        return {"title": (a.title or "").strip(), "content": (a.text or "").strip(),
                "image_url": a.top_image, "author": ", ".join(a.authors) if a.authors else None,
                "published_at": pd, "success": bool(a.text and len(a.text) > 50)}
    except Exception as e:
        logger.debug(f"[EXTRACTOR] {url}: {e}")
        return {"title":"","content":"","image_url":None,"author":None,"published_at":None,"success":False}

async def extract_article(url: str, html: str = None) -> Dict:
    return await asyncio.to_thread(_extract_sync, url, html)
