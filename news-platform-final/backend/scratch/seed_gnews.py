from app.database import SyncSessionLocal
from app.models.models import NewsSource
import json

db = SyncSessionLocal()
sources = [
    {
        "id": 13, "name": "Google News - World", "url": "https://news.google.com", 
        "scraper_type": "googlenews", "language": "en", "is_enabled": True, "is_paused": False,
        "credibility_score": 0.9, "priority": 1, 
        "scraper_config": {"topic": "WORLD", "max_articles": 10, "target_category": "World"},
        "scrape_interval_minutes": 60, "ai_processing_interval_minutes": 30
    },
    {
        "id": 14, "name": "Google News - U.S.", "url": "https://news.google.com", 
        "scraper_type": "googlenews", "language": "en", "is_enabled": True, "is_paused": False,
        "credibility_score": 0.9, "priority": 1, 
        "scraper_config": {"topic": "NATION", "max_articles": 10, "target_category": "U.S."},
        "scrape_interval_minutes": 60, "ai_processing_interval_minutes": 30
    },
    {
        "id": 15, "name": "Google News - Business", "url": "https://news.google.com", 
        "scraper_type": "googlenews", "language": "en", "is_enabled": True, "is_paused": False,
        "credibility_score": 0.9, "priority": 1, 
        "scraper_config": {"topic": "BUSINESS", "max_articles": 10, "target_category": "Business"},
        "scrape_interval_minutes": 60, "ai_processing_interval_minutes": 30
    },
    {
        "id": 16, "name": "Google News - Technology", "url": "https://news.google.com", 
        "scraper_type": "googlenews", "language": "en", "is_enabled": True, "is_paused": False,
        "credibility_score": 0.9, "priority": 1, 
        "scraper_config": {"topic": "TECHNOLOGY", "max_articles": 10, "target_category": "Tech"},
        "scrape_interval_minutes": 60, "ai_processing_interval_minutes": 30
    },
    {
        "id": 17, "name": "Google News - India", "url": "https://news.google.com", 
        "scraper_type": "googlenews", "language": "en", "is_enabled": True, "is_paused": False,
        "credibility_score": 0.9, "priority": 1, 
        "scraper_config": {"search_query": "Latest India News", "max_articles": 10, "target_category": "India"},
        "scrape_interval_minutes": 60, "ai_processing_interval_minutes": 30
    }
]

for s in sources:
    existing = db.query(NewsSource).filter(NewsSource.id == s['id']).first()
    if existing:
        for k, v in s.items():
            setattr(existing, k, v)
    else:
        db.add(NewsSource(**s))
    db.commit()

print("Sources 13-17 updated successfully (with correct Dictionary config).")
db.close()
