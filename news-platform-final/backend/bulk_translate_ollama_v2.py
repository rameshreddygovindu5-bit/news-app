
import re
import json
import requests
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from sqlalchemy import select, update

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"

def translate_via_ollama(title, content):
    prompt = f"Translate the following news title and content to Telugu. Return ONLY JSON with 'title' and 'content' fields.\nTITLE: {title}\nCONTENT: {content[:300]}"
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2}
            },
            timeout=40
        )
        if resp.status_code == 200:
            raw = resp.json().get("response", "")
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                d = json.loads(m.group())
                return d.get("title"), d.get("content")
    except Exception as e:
        print(f"Ollama error: {e}")
    return None, None

def main():
    db = SyncSessionLocal()
    try:
        # Get all approved articles
        q = db.execute(select(NewsArticle).where(
            NewsArticle.flag.in_(['A', 'Y'])
        )).scalars().all()
        
        to_translate = []
        for art in q:
            # Check if title has English letters
            if art.telugu_title and re.search(r'[a-zA-Z]', art.telugu_title):
                to_translate.append(art)
        
        print(f"Found {len(to_translate)} articles needing Telugu translation.")
        
        count = 0
        for art in to_translate[:20]: # Process 20 at a time
            print(f"Translating [{art.id}] {art.telugu_title[:50]}...")
            te_title, te_content = translate_via_ollama(art.telugu_title, art.telugu_content or "")
            
            if te_title:
                # Use a new session for each update to ensure commit
                with SyncSessionLocal() as session:
                    session.execute(update(NewsArticle).where(NewsArticle.id == art.id).values(
                        telugu_title=te_title,
                        telugu_content=te_content or art.telugu_content
                    ))
                    session.commit()
                count += 1
                print(f"  -> Done: {te_title[:50]}")
            else:
                print(f"  -> Failed translation for {art.id}")
                
        print(f"Successfully translated {count} articles.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
