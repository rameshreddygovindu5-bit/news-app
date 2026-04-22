import sys
import logging
from datetime import datetime, timezone

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from app.services.ai_service import AIService

db = SyncSessionLocal()
ai = AIService()

# Get 10 pending articles
arts = db.query(NewsArticle).filter(NewsArticle.ai_status == 'pending').limit(10).all()
print(f"Manually processing {len(arts)} articles...")

for a in arts:
    try:
        source_name = a.source.name if a.source else "Unknown"
        print(f"Processing: {a.original_title[:50]}...")
        res = ai.process_article(a.original_title, a.original_content, source_name=source_name)
        
        a.rephrased_title = res.get("rephrased_title") or a.original_title
        a.rephrased_content = res.get("rephrased_content") or a.original_content
        a.telugu_title = res.get("telugu_title", "")
        a.telugu_content = res.get("telugu_content", "")
        a.category = res.get("category", a.category)
        a.ai_status = res.get("ai_status_code", "completed")
        a.flag = "A" # Mark as Processed
        a.processed_at = datetime.now(timezone.utc)
        print(f"  -> Success: {a.ai_status}")
    except Exception as e:
        print(f"  -> Failed: {e}")

db.commit()
db.close()
print("Manual batch complete.")
