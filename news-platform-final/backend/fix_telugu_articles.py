
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from sqlalchemy import update

db = SyncSessionLocal()
try:
    # Update articles where telugu_title is empty but rephrased_title exists
    # This specifically targets articles processed by LOCAL_PARAPHRASE
    stmt = update(NewsArticle).where(
        (NewsArticle.telugu_title == '') | (NewsArticle.telugu_title == None),
        NewsArticle.rephrased_title != '',
        NewsArticle.rephrased_title != None,
        NewsArticle.flag.in_(['A', 'Y'])
    ).values(
        telugu_title=NewsArticle.rephrased_title,
        telugu_content=NewsArticle.rephrased_content
    )
    result = db.execute(stmt)
    db.commit()
    print(f"Updated {result.rowcount} articles with English fallback for Telugu view.")
finally:
    db.close()
