
import re
import json
import requests
from app.database import SyncSessionLocal
from app.models.models import NewsArticle
from sqlalchemy import select, update

# Configuration
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
        # Find articles that need translation (telugu_title has English chars)
        q = db.execute(select(NewsArticle).where(
            NewsArticle.telugu_title.regexp_match('[a-zA-Z]'),
            NewsArticle.flag.in_(['A', 'Y'])
        )).scalars().all()
        
        print(f"Found {len(q)} articles needing Telugu translation.")
        
        count = 0
        for art in q[:50]: # Limit to 50 for now to avoid long wait
            print(f"Translating [{art.id}] {art.telugu_title[:50]}...")
            te_title, te_content = translate_via_ollama(art.telugu_title, art.telugu_content or "")
            
            if te_title:
                db.execute(update(NewsArticle).where(NewsArticle.id == art.id).values(
                    telugu_title=te_title,
                    telugu_content=te_content or art.telugu_content
                ))
                db.commit()
                count += 1
                print(f"  -> Done: {te_title[:50]}")
            else:
                print(f"  -> Failed translation for {art.id}")
                
        print(f"Successfully translated {count} articles.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
