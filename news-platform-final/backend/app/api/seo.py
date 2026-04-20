
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.models import NewsArticle, Category
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SEO"])

@router.get("/robots.txt", response_class=Response)
async def get_robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "Sitemap: https://peoples-feedback.com/sitemap.xml"
    )
    return Response(content=content, media_type="text/plain")

@router.get("/sitemap.xml", response_class=Response)
async def get_sitemap_xml(db: AsyncSession = Depends(get_db)):
    """Generate dynamic sitemap.xml for Google indexing."""
    base_url = "https://www.peoples-feedback.com"
    
    # 1. Static and Category URLs
    urls = [
        {"loc": base_url, "changefreq": "always", "priority": "1.0"},
        {"loc": f"{base_url}/telugu", "changefreq": "always", "priority": "0.9"},
        {"loc": f"{base_url}/wishes", "changefreq": "daily", "priority": "0.7"},
    ]
    
    # Categories
    categories = (await db.execute(select(Category.name).where(Category.is_active == True))).scalars().all()
    for cat in categories:
        urls.append({
            "loc": f"{base_url}/news?category={cat}",
            "changefreq": "hourly",
            "priority": "0.8"
        })
    
    # 2. Latest 2000 published articles
    # Use rephrased_title existence as a proxy for 'enriched' content to prioritese for SEO
    articles_result = await db.execute(
        select(NewsArticle.slug, NewsArticle.updated_at, NewsArticle.telugu_title)
        .where(NewsArticle.flag == "Y", NewsArticle.is_duplicate == False)
        .order_by(NewsArticle.published_at.desc())
        .limit(2000)
    )
    articles = articles_result.all()
    
    for art in articles:
        if art.slug:
            lastmod = getattr(art, 'updated_at', datetime.now())
            if not lastmod: lastmod = datetime.now()
            lastmod_str = lastmod.strftime("%Y-%m-%d")
            # English article URL
            urls.append({
                "loc": f"{base_url}/news/{art.slug}",
                "lastmod": lastmod_str,
                "changefreq": "monthly",
                "priority": "0.6"
            })
            # Telugu article URL (if Telugu content exists)
            if getattr(art, "telugu_title", None):
                urls.append({
                    "loc": f"{base_url}/telugu/{art.slug}",
                    "lastmod": lastmod_str,
                    "changefreq": "monthly",
                    "priority": "0.6"
                })

    # Build XML
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for url in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{url['loc']}</loc>")
        if "lastmod" in url:
            xml_lines.append(f"    <lastmod>{url['lastmod']}</lastmod>")
        xml_lines.append(f"    <changefreq>{url['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{url['priority']}</priority>")
        xml_lines.append("  </url>")
        
    xml_lines.append("</urlset>")
    
    return Response(content="\n".join(xml_lines), media_type="application/xml")
