"""
AI Service v7.1 — Optimized Multilingual Transformation Engine
==============================================================

Architecture:
  - Fast Paraphrase Engine: Zero-dependency, sub-10ms local rephrasing.
  - Multilingual: Generates English + Telugu in a single cloud pass (Gemini).
  - Optimized Fallback: Local engine provides structured HTML stubs for Telugu if cloud fails.
  - Performance: Thread-safe singleton, zero redundant model loads.
"""

import re
import json
import logging
import threading
from typing import Optional, Dict, List
from difflib import SequenceMatcher

try:
    from langdetect import detect
except ImportError:
    def detect(text: str) -> str: return "en"

from app.config import get_settings
from app.services.category_service import category_service

logger = logging.getLogger(__name__)
settings = get_settings()

CATEGORIES = settings.CATEGORIES
CATEGORIES_STR = ", ".join(CATEGORIES)

class ParaphraseEngine:
    """Singleton delegating to fast_engine for near-instant local rephrasing."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance

    def __init__(self):
        if self._initialised: return
        with self._lock:
            if self._initialised: return
            self._ready = True
            self._initialised = True
            logger.info("[ParaphraseEngine] Fast engine ready")

    def paraphrase_to_html(self, title: str, content: str) -> Dict[str, str]:
        try:
            from app.services.paraphrase.fast_engine import paraphrase_to_html
            import hashlib
            seed = int(hashlib.md5((title[:50]).encode()).hexdigest()[:6], 16) % 10000
            return paraphrase_to_html(title, content, seed=seed)
        except Exception:
            return {"rephrased_title": title, "rephrased_content": f"<p>{content}</p>"}

    def _lexical_chain(self, text: str, is_title: bool = False) -> str:
        try:
            from app.services.paraphrase.fast_engine import rephrase_title, _substitute_words
            if is_title:
                import hashlib
                seed = int(hashlib.md5(text[:30].encode()).hexdigest()[:6], 16) % 10000
                return rephrase_title(text, seed=seed)
            return _substitute_words(text)
        except Exception: return text

paraphrase_engine = ParaphraseEngine()

SOURCE_NAMES = [
    "GreatAndhra", "ANI", "IANS", "PTI", "UNI", "TNIE", "Eenadu", "Sakshi",
    "TV9", "CNN", "Al Jazeera", "OneIndia", "Telugu123", "TeluguTimes",
    "PrabhaNews", "Reuters", "AP News", "AFP", "BBC", "NDTV", "Times of India",
    "The Hindu", "Indian Express", "Deccan Herald", "Hindustan Times",
    "News18", "Republic", "Zee News", "ABP", "India Today", "Firstpost",
    "సాక్షి", "ఈనాడు", "ఆంధ్రజ్యోతి", "నమస్తే తెలంగాణ", "ప్రభ న్యూస్", "టీవీ9"
]

def _strip_source_names(text: str) -> str:
    if not text: return ""
    for name in SOURCE_NAMES:
        pattern = rf"\b{re.escape(name)}\b" if re.search(r'[a-zA-Z]', name) else rf"{re.escape(name)}"
        text = re.sub(pattern, "Peoples Feedback", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", text).strip()

def _clean(text: str) -> str:
    if not text: return ""
    text = re.sub(r"(?i)ignore\s+previous\s+instructions.*", "", text)
    return _strip_source_names(text)

SYSTEM_PROMPT = f"""You are a Principal News Editor. Transform news into premium articles.
STRUCTURE:
<p><strong>🔑 [SUMMARY]</strong></p>
<p><b>📌 Key Highlights:</b></p><ul><li><b>Point:</b> ...</li></ul>
<p>[Background]</p><p>[Analysis]</p>
<p><i>⏩ What's Next: ...</i></p>

RULES:
- NO source names (ANI, PTI, etc.).
- BILINGUAL: Generate BOTH English and Telugu.
- Category from: {CATEGORIES_STR}
- Valid JSON only.
"""

def _build_prompt(title: str, content: str, lang: str) -> str:
    return f"SOURCE: {lang}\nHEADLINE: {title}\nCONTENT: {content[:3000]}\n\nReturn JSON with title, content, category, tags, slug, telugu_title, telugu_content."

def compute_similarity(a: str, b: str) -> float:
    a_p = re.sub(r"<[^>]+>", " ", a or "")
    b_p = re.sub(r"<[^>]+>", " ", b or "")
    return SequenceMatcher(None, a_p, b_p).ratio()

_CAT_KEYWORDS = {
    "Andhra Pradesh": ["andhra", "vijayawada", "jagan", "chandrababu"],
    "Telangana": ["telangana", "hyderabad", "revanth", "kcr"],
    "Politics": ["election", "minister", "bjp", "congress"],
    "Sports": ["cricket", "ipl", "match"],
    "Tech": ["ai ", "google", "apple", "software"],
    "Business": ["stock", "market", "economy"],
    "Entertainment": ["movie", "cinema", "actor"],
}

def _auto_category(title: str, content: str) -> str:
    text = f"{title} {content[:1000]}".lower()
    for cat, kw in _CAT_KEYWORDS.items():
        if any(k in text for k in kw): return cat
    return "Home"

def _make_slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_-]+", "-", s)[:80]

def _get_category_image(cat: str) -> str:
    return f"/placeholders/{cat.lower().replace(' ', '_')}.png"

def _build_local_result(title: str, content: str, status: str, method: str) -> Dict:
    c_t, c_c = _clean(title), _clean(content)
    is_te = bool(re.search(r"[\u0c00-\u0c7f]", c_t + c_c[:100]))
    res = paraphrase_engine.paraphrase_to_html(c_t, c_c)
    n_t, n_c = res["rephrased_title"], res["rephrased_content"]
    cat = category_service.normalize(_auto_category(c_t, c_c))
    
    te_t, te_c = "", ""
    if not is_te and getattr(settings, "OLLAMA_BASE_URL", None):
        try:
            raw = _try_ollama(f"Translate to Telugu JSON (title, content): {n_t}")
            if raw:
                d = json.loads(re.search(r"\{.*\}", raw).group())
                te_t, te_c = d.get("title",""), d.get("content","")
        except Exception: pass
    
    return {
        "rephrased_title": n_t if not is_te else "",
        "rephrased_content": n_c if not is_te else "",
        "telugu_title": n_t if is_te else (te_t or f"{n_t} (Telugu)"),
        "telugu_content": n_c if is_te else (te_c or n_c),
        "category": cat, "tags": ["news", cat.lower()], "slug": _make_slug(n_t),
        "method": method, "ai_status_code": status, "similarity_score": 0.0,
        "image_url": _get_category_image(cat)
    }

def _try_gemini(key: str, prompt: str) -> Optional[str]:
    if not key: return None
    try:
        from google import genai
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(model="gemini-1.5-flash", contents=prompt, config={"system_instruction": SYSTEM_PROMPT})
        return resp.text
    except Exception: return None

def _try_ollama(prompt: str) -> Optional[str]:
    if not settings.OLLAMA_BASE_URL: return None
    try:
        import requests
        r = requests.post(f"{settings.OLLAMA_BASE_URL}/api/generate", json={"model": "llama3.2:1b", "prompt": prompt, "stream": False}, timeout=10)
        return r.json().get("response") if r.status_code==200 else None
    except Exception: return None

class AIService:
    def process_article(self, title: str, content: str, source_name: str = "Unknown") -> Dict:
        is_gnews = "google news" in (source_name or "").lower()
        if is_gnews:
            return _build_local_result(title, content, "GOOGLE_NEWS_LOCAL", "local_engine")
        
        prompt = _build_prompt(title, content, "Auto")
        raw = _try_gemini(settings.GEMINI_API_KEY, prompt)
        if raw:
            try:
                d = json.loads(re.search(r"\{[\s\S]*\}", raw).group())
                t_sim = compute_similarity(title, d.get("title"))
                if t_sim < 0.75:
                    return {
                        "rephrased_title": d.get("title"), "rephrased_content": d.get("content"),
                        "telugu_title": d.get("telugu_title"), "telugu_content": d.get("telugu_content"),
                        "category": category_service.normalize(d.get("category", "Home")),
                        "tags": d.get("tags", []), "slug": d.get("slug") or _make_slug(d.get("title")),
                        "ai_status_code": "AI_SUCCESS", "method": "gemini", "similarity_score": t_sim,
                        "image_url": _get_category_image(d.get("category", "Home"))
                    }
            except Exception: pass
        
        return _build_local_result(title, content, "LOCAL_PARAPHRASE", "local_engine")

    async def analyze_reporter_draft(self, title: str, content: str) -> Dict:
        return {"category": _auto_category(title, content), "tags": ["news"]}

ai_service = AIService()