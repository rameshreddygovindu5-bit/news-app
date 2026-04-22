
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from sqlalchemy import select
import re

db = SyncSessionLocal()
try:
    q = db.execute(select(NewsArticle.id, NewsArticle.telugu_title, NewsArticle.flag, NewsArticle.original_language).where(NewsArticle.flag.in_(['A', 'Y']))).all()
    telugu_count = 0
    te_sources_count = 0
    for r in q:
        if r[1] and re.search(r'[\u0c00-\u0c7f]', r[1]):
            telugu_count += 1
        if r[3] == 'te':
            te_sources_count += 1
    print(f"Total processed articles (A/Y): {len(q)}")
    print(f"Articles with actual Telugu characters in title: {telugu_count}")
    print(f"Articles with original_language='te': {te_sources_count}")
finally:
    db.close()
