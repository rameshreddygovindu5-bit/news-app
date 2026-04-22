
from app.database import SyncSessionLocal
from app.models.models import NewsArticle, NewsSource
from sqlalchemy import select, func

db = SyncSessionLocal()
try:
    total = db.query(func.count(NewsArticle.id)).scalar()
    print(f"Total articles: {total}")
    
    # Check if they have sources
    with_source = db.query(NewsArticle).join(NewsSource).count()
    print(f"Articles with valid source join: {with_source}")
    
    # Check statuses
    statuses = db.query(NewsArticle.ai_status, func.count(NewsArticle.id)).group_by(NewsArticle.ai_status).all()
    print(f"Statuses: {statuses}")
    
    # Check if flags are being reset
    y_count = db.query(NewsArticle).filter(NewsArticle.flag == 'Y').count()
    print(f"Current flag=Y: {y_count}")

finally:
    db.close()
