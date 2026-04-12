#!/usr/bin/env python3
"""
Direct AI Processing Script
Bypasses Celery to run AI processing directly
"""

import asyncio
import sys
import os

# Add the backend path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'news-platform-final', 'backend'))

from app.config import get_settings
from app.database import SyncSessionLocal

settings = get_settings()
print(f"Database URL: {settings.DATABASE_URL_SYNC}")
from app.models.models import NewsArticle
from app.services.ai_service import ai_service
from sqlalchemy import select, and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_articles_directly():
    """Process unprocessed articles directly"""
    db = SyncSessionLocal()
    try:
        # Get unprocessed articles (flag = N)
        query = select(NewsArticle).where(NewsArticle.flag == 'N').limit(5)
        result = db.execute(query)
        articles = result.scalars().all()
        
        logger.info(f"Found {len(articles)} unprocessed articles")
        
        for article in articles:
            logger.info(f"Processing article {article.id}: {article.original_title[:50]}...")
            
            try:
                # Process the article with title and content
                processed = ai_service.process_article(
                    title=article.original_title,
                    content=article.original_content or article.original_title
                )
                
                if processed:
                    # Update the article
                    article.flag = 'A'  # Approved
                    article.processed_at = 'now()'
                    
                    # Apply the generated properties to the DB row
                    if 'rephrased_title' in processed:
                        article.rephrased_title = processed['rephrased_title']
                    if 'rephrased_content' in processed:
                        article.rephrased_content = processed['rephrased_content']
                    if 'slug' in processed:
                        article.slug = processed['slug']
                    if 'category' in processed:
                        article.category = processed['category']
                        
                    db.commit()
                    logger.info(f"Successfully processed article {article.id}")
                else:
                    logger.warning(f"Failed to process article {article.id}")
                    
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {str(e)}")
                db.rollback()
                
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    process_articles_directly()
