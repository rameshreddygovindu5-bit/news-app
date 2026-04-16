
import asyncio
import sys
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.models import NewsArticle, NewsSource

# Set encoding to UTF-8 for windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def find_article():
    slug = "బవ-బవ-అటట-బగద-నత-ఉటట-రవతజ-వరసడ-లవ-సగ-రలజమస-మహరజ-రవతజ-సదరడ-తనయడ-మధవ-భపతరజ-హరగ-వసతనన-తజ-చతర-మరమమ-7f159b"
    async with AsyncSessionLocal() as session:
        stmt = select(NewsArticle).where(NewsArticle.slug == slug)
        result = await session.execute(stmt)
        article = result.scalar_one_or_none()
        
        if article:
            print(f"Article Found: ID={article.id}")
            print(f"Original Title: {article.original_title}")
            print(f"Slug: {article.slug}")
            print(f"Source ID: {article.source_id}")
            print(f"AI Status: {article.ai_status}")
            print(f"Flag: {article.flag}")
            print(f"Original Content Length: {len(article.original_content) if article.original_content else 0}")
            print(f"Rephrased Content Length: {len(article.rephrased_content) if article.rephrased_content else 0}")
            print(f"Telugu Content Length: {len(article.telugu_content) if article.telugu_content else 0}")
            print(f"Original URL: {article.original_url}")
            
            # Fetch source name
            source_stmt = select(NewsSource).where(NewsSource.id == article.source_id)
            source_res = await session.execute(source_stmt)
            source = source_res.scalar_one_or_none()
            if source:
                print(f"Source Name: {source.name}")
        else:
            print("Article NOT found in database with that slug.")

if __name__ == "__main__":
    asyncio.run(find_article())
