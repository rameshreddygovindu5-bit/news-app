"""
AI Service v6.0 — Production News Transformation Engine
========================================================
Fallback chain for regular sources (Priority 1 -> 6, then original):
  Priority 1: Google Gemini PRIMARY      (AIzaSyDweaZs...)
  Priority 2: Google Gemini SECONDARY   (AIzaSyDOqGA7...)
  Priority 3: Google Gemini TERTIARY    (AIzaSyArwJeb...)
  Priority 4: Grok AI (xAI)             (xai-ynDXskIZ...)
  Priority 5: OpenAI (GPT-4o-mini)      (sk-proj-3Zj0...)
  Priority 6: Ollama (Local LLM)        (localhost:11434)
  Last Resort: ORIGINAL cleaned fallback.

Google News source special chain:
  Step 1: Ollama (local only — no paid APIs)
  Step 2: Original cleaned content (GOOGLE_NEWS_NO_AI)

AI Status Codes returned:
  AI_SUCCESS              — Passed similarity check on first attempt (≤70%)
  AI_RETRY_SUCCESS        — Passed on second attempt (retry with stronger prompt)
  GOOGLE_NEWS_NO_AI       — Google News source: AI intentionally skipped per spec
  REWRITE_FAILED          — All retries failed similarity check → sent to admin review
  original_cleaned        — method field only; ai_status_code = one of the above

Output: English rephrased article + Telugu translation, always.
Similarity threshold: 0.70 (reject if title or content similarity > 70%).
"""
import re, json, logging, time, hashlib
from typing import Optional, Dict, List
try:
    from langdetect import detect
except ImportError:
    def detect(text):
        return "en"

from app.config import get_settings
from app.services.category_service import category_service
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)
settings = get_settings()

CATEGORIES = settings.CATEGORIES
CATEGORIES_STR = ", ".join(CATEGORIES)

# ── Known source names to strip everywhere ────────────────────────────
SOURCE_NAMES = [
    "GreatAndhra", "ANI", "IANS", "PTI", "UNI", "TNIE", "Eenadu", "Sakshi",
    "TV9", "CNN", "Al Jazeera", "OneIndia", "Telugu123", "TeluguTimes",
    "PrabhaNews", "Reuters", "AP News", "AFP", "BBC", "NDTV", "Times of India",
    "The Hindu", "Indian Express", "Deccan Herald", "Hindustan Times",
    "News18", "Republic", "Zee News", "ABP", "India Today", "Firstpost",
    "The Wire", "Scroll", "The Print", "Mint", "Economic Times",
    "Business Standard", "Bloomberg", "Fox News", "The Guardian",
    "Washington Post", "New York Times", "Peoples Feedback",
]

def _strip_source_names(text: str) -> str:
    """Remove all known source/agency names from text."""
    if not text:
        return ""
    for name in SOURCE_NAMES:
        text = re.sub(rf'(?i)\(\s*{re.escape(name)}\s*\)', '', text)
        text = re.sub(rf'(?i)[\u2014\u2013\-\u2013\u2014]\s*{re.escape(name)}\b', '', text)
        text = re.sub(rf'(?i)\bsource\s*:\s*{re.escape(name)}\b', '', text)
        text = re.sub(rf'(?i)\b(?:reported|published|stated)\s+(?:by|in|on)\s+{re.escape(name)}\b', '', text)
        text = re.sub(rf'(?i)\baccording\s+to\s+{re.escape(name)}\b', 'according to reports', text)
        text = re.sub(rf'(?i)\b{re.escape(name)}\s+report(?:s|ed)?\b', 'reports indicate', text)
        text = re.sub(rf'(?i)(?:^|\.\s+){re.escape(name)}[.,]?\s*', '. ', text)
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\.\s*\.', '.', text)
    return text.strip()


def _clean(text: str) -> str:
    if not text: return ""
    for p in [r"(?i)ignore\s+previous\s+instructions.*", r"(?i)system\s+prompt.*"]:
        text = re.sub(p, "", text)
    text = _strip_source_names(text)
    return text.strip()


SYSTEM_PROMPT = f"""You are an award-winning senior multilingual News Journalist and Telugu language specialist.
Your mission is to transform raw scraped news into a premium reading experience: a polished, engaging English article AND a high-quality, natural Telugu version.

=== VISUAL EXPERIENCE & STRUCTURE — CRITICAL ===
1. BOTH versions (English & Telugu) MUST follow this exact HTML hierarchy:
   - <p><strong>[Brief Summary]</strong>: A one-sentence bold hook about the most important outcome.</p>
   - <p><b>Key Highlights:</b></p>
     <ul>
       <li>A major factual point.</li>
       <li>Another crucial detail or implication.</li>
       <li>A third significant piece of information.</li>
     </ul>
   - 2-3 body <p> tags: Deep context, background, and expert-level analysis (paraphrased).
   - <p><i>[What's Next]</i>: A brief italicized closing about upcoming developments.</p>
2. NEVER use simple blocks of text. Use lists for facts and paragraphs for narrative.
3. PRESERVE original lists: If the raw text has numbered/bulleted lists, incorporate their essence into the structure above.

=== COPYRIGHT & ORIGINALITY ===
4. REWRITE 100%: Never copy sentences verbatim. Use your own professional vocabulary.
5. REMOVE ALL ATTRIBUTION: Strip out ANI, PTI, Reuters, CNN, GreatAndhra, Eenadu, etc.
6. Replace "According to sources" with "Reports indicate" or "Officials stated".
7. NO source names, reporter bylines, photo credits, URLs, or timestamps allowed.

=== TELUGU EXCELLENCE ===
8. DO NOT use formal/robotic "bookish" Telugu. Use "Vyavaharika" (spoken style used in top news portals like Sakshi/Eenadu).
9. Ensure the Telugu title is punchy and fits the "Key subject + Action" format.
10. Proper nouns: Use standard Telugu transliterations (e.g., 'Modi' as 'మోదీ').

=== CATEGORIZATION ===
11. CATEGORY: Choose EXACTLY ONE from: {CATEGORIES_STR}
12. TAGS: Exactly 5 lowercase English keywords.
13. SLUG: URL-safe lowercase-hyphenated title.

=== OUTPUT FORMAT ===
Return ONLY a valid JSON object. No markdown, no backticks.
{{
  "title": "Compelling English Title",
  "content": "<p><strong>...</strong></p><p><b>Key Highlights:</b></p><ul><li>...</li></ul><p>...</p><p><i>...</i></p>",
  "category": "CategoryName",
  "tags": ["t1", "t2", "t3", "t4", "t5"],
  "slug": "title-slug",
  "telugu_title": "తెలుగు శీర్షిక",
  "telugu_content": "<p><strong>...</strong></p><p><b>ముఖ్య విషయాలు:</b></p><ul><li>...</li></ul><p>...</p><p><i>...</i></p>"
}}"""

def _build_prompt(title: str, content: str, lang: str) -> str:
    return f"""LANGUAGE: {lang}
ORIGINAL HEADLINE: {_clean(title)}
RAW CONTENT: {_clean(content)[:3000]}

TASK: Rewrite into original English + Telugu following all rules. Remove ALL source/agency names. Return JSON only."""


def _parse_result(raw: str, original_title: str, original_content: str) -> Dict:
    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.M)
    text = re.sub(r'\s*```$', '', text, flags=re.M)
    text = text.strip()

    try:
        d = json.loads(text)
        return _validate(d, original_title, original_content)
    except json.JSONDecodeError:
        pass

    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            d = json.loads(m.group())
            return _validate(d, original_title, original_content)
        except json.JSONDecodeError:
            pass

    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    fixed = fixed.replace("'", '"')
    try:
        d = json.loads(fixed)
        return _validate(d, original_title, original_content)
    except Exception:
        pass

    logger.warning("[AI] JSON parse failed, returning cleaned original content")
    return _original_fallback(original_title, original_content)


def _validate(d: Dict, orig_title: str, orig_content: str) -> Dict:
    title = _strip_source_names(str(d.get("title", "")).strip()) or orig_title
    content = _strip_source_names(str(d.get("content", "")).strip()) or orig_content
    cat = category_service.normalize(str(d.get("category", "Home")))
    tags = d.get("tags", [])
    if not isinstance(tags, list): tags = []
    tags = [str(t).strip().lower() for t in tags if str(t).strip()][:5]
    slug = str(d.get("slug", "")).strip()
    if not slug:
        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[\s_-]+', '-', slug)[:80]
    telugu_title = _strip_source_names(str(d.get("telugu_title", "")).strip())
    telugu_content = _strip_source_names(str(d.get("telugu_content", "")).strip())
    return {
        "rephrased_title": title,
        "rephrased_content": content,
        "category": cat, "tags": tags, "slug": slug,
        "telugu_title": telugu_title,
        "telugu_content": telugu_content,
        "method": d.get("_method", "ai"),
    }


def _original_fallback(title: str, content: str) -> Dict:
    """Enhanced fallback: cleans text and provides basic HTML structure."""
    clean_title = _strip_source_names(title).strip()
    clean_content = _strip_source_names(content or title).strip()

    # Detect if original is Telugu (simple check for Telugu script range)
    is_telugu = bool(re.search(r'[\u0c00-\u0c7f]', clean_title + clean_content))

    if clean_content and not re.search(r'<(p|div|ul|ol|br)', clean_content, re.I):
        # Basic paragraphing
        paras = [p.strip() for p in re.split(r'\n+', clean_content) if p.strip()]
        if len(paras) > 1:
            clean_content = "".join(f"<p>{p}</p>" for p in paras)
        else:
            # Sentence-based paragraphing for long single blocks
            sentences = re.split(r'(?<=[.!?])\s+', clean_content)
            chunks = [' '.join(sentences[i:i+3]) for i in range(0, len(sentences), 3)]
            clean_content = "".join(f"<p>{c}</p>" for c in chunks)

    # Basic auto-categorization
    cat = "Home"
    text_lower = f"{clean_title} {clean_content[:1500]}".lower()
    cat_keywords = {
        "Andhra Pradesh": ["andhra", "ap ", "vijayawada", "visakhapatnam", "jagan", "chandrababu", "lokesh", "pawan kalyan", "amravati", "tirupati"],
        "Telangana": ["telangana", "hyderabad", "revanth", " kcr ", " ktr ", "bainsa", "warangal", "khammam"],
        "Politics": ["election", "minister", "bjp", "congress", "government", "mla", "mp ", "parliament", "assembly", "vote", "political", "cabinet"],
        "Sports": ["cricket", "football", "match", "ipl", "player", "sport", "tennis", "olympic", "medal", "score", "wicket", "stadium"],
        "Tech": ["ai ", "technology", "google", "apple", "app ", "software", "smartphone", "iphone", "chip", "semiconductor", "startup", "data"],
        "Business": ["market", "stock", "economy", "billion", "million", "bank", "rbi", "sensex", "nifty", "profit", "investment", "finance"],
        "Entertainment": ["movie", "film", "actor", "hollywood", "bollywood", "tollywood", "cinema", "trailer", "release", "review", "celebrity"],
        "International": ["world", "global", "us ", "uk ", "iran", "israel", "russia", "ukraine", "un ", "summit", "foreign"],
        "Health": ["health", "medical", "doctor", "virus", "vaccine", "study", "cancer", "fitness", "hospital"],
    }
    for c, kw in cat_keywords.items():
        if any(k in text_lower for k in kw):
            cat = c
            break

    slug = re.sub(r'[^\w\s-]', '', clean_title.lower()).strip()
    slug = re.sub(r'[\s_-]+', '-', slug)[:80]

    return {
        "rephrased_title": clean_title if not is_telugu else "",
        "rephrased_content": clean_content if not is_telugu else "",
        "category": cat,
        "tags": ["news", cat.lower()],
        "slug": slug,
        "telugu_title": clean_title if is_telugu else "",
        "telugu_content": clean_content if is_telugu else "",
        "method": "original_cleaned",
    }


# ── Provider implementations ───────────────────────────────────────────

def _try_gemini(api_key: str, prompt: str, label: str = "gemini") -> Optional[str]:
    if not api_key: return None
    import requests
    
    models_to_try = [
        "gemini-1.5-flash", 
        "gemini-1.5-pro", 
    ]
    
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2048
                }
            }
            resp = requests.post(url, json=payload, timeout=30)
            if resp.ok:
                data = resp.json()
                # Extract text from Gemini response structure
                try:
                    return data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    continue
            elif resp.status_code == 404:
                continue
            else:
                logger.warning(f"[AI] {label} model {model_name} HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.debug(f"[AI] {label} {model_name} error: {e}")
            continue
            
    return None


def _try_openai(prompt: str) -> Optional[str]:
    if not settings.OPENAI_API_KEY: return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4, max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"[AI] OpenAI failed: {e}")
        return None


def _try_grok(prompt: str) -> Optional[str]:
    if not getattr(settings, "XAI_API_KEY", None): return None
    try:
        from openai import OpenAI
        # xAI is OpenAI-API compatible
        client = OpenAI(api_key=settings.XAI_API_KEY, base_url="https://api.x.ai/v1", timeout=30)
        resp = client.chat.completions.create(
            model="grok-beta", # or 'grok-2' if available
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4, max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.warning(f"[AI] Grok/xAI failed: {e}")
        return None


def _try_ollama(prompt: str) -> Optional[str]:
    try:
        import requests
        resp = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": f"{SYSTEM_PROMPT}\\n\\n{prompt}",
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 2048},
            },
            timeout=60,
        )
        if resp.ok:
            return resp.json().get("response", "")
    except Exception as e:
        logger.warning(f"[AI] Ollama failed: {e}")
    return None


def _detect_lang(text: str) -> str:
    try:
        return detect(text[:200]) if text else "en"
    except Exception:
        return "en"


LANG_NAMES = {
    "te": "Telugu", "hi": "Hindi", "ta": "Tamil", "kn": "Kannada",
    "ml": "Malayalam", "mr": "Marathi", "en": "English",
}


def compute_similarity(a: str, b: str) -> float:
    """Compute gestalt pattern matching similarity between two strings."""
    if not a or not b: return 0.0
    return SequenceMatcher(None, a, b).ratio()


class AIService:
    def process_article(self, title: str, content: str, source_name: str = "Unknown") -> Dict:
        """
        Production-grade rephrasing with fallback strategy and similarity validation.
        """
        # STEP 1: Detect language and build prompt
        lang_code = _detect_lang(f"{title} {content}")
        lang_name = LANG_NAMES.get(lang_code, "Unknown")
        
        # Determine strictness based on source
        # CASE A: Regional trusted sources -> aggressive rewrite
        is_regional = any(x in (source_name or "").lower() for x in ["greatandhra", "eenadu", "sakshi", "andhra", "telangana"])
        is_gnews = "google news" in (source_name or "").lower()
        
        prompt = _build_prompt(title, content, lang_name)
        if is_regional:
             prompt += "\n\nCRITICAL: Use aggressive sentence restructuring and significant tone shift. Ensure NO similarity to source."
        
        # STEP 1b: GOOGLE NEWS RULE — Do NOT call paid AI APIs (Gemini/Grok/OpenAI)
        # Try Ollama (local LLM, free) first. If Ollama unavailable, use cleaned original.
        if is_gnews:
            logger.info(f"[AI] Google News — skipping paid APIs, trying Ollama only")
            ollama_raw = _try_ollama(prompt)
            if ollama_raw:
                result = _parse_result(ollama_raw, title, content)
                title_sim = compute_similarity(title, result["rephrased_title"])
                content_sim = compute_similarity(content, result["rephrased_content"])
                if title_sim <= 0.70 and content_sim <= 0.70:
                    result["ai_status_code"] = "AI_SUCCESS"
                    result["similarity_score"] = max(title_sim, content_sim)
                    result["method"] = "google_news_ollama"
                    return result
            # Ollama failed or similarity too high — use cleaned original
            res = _original_fallback(title, content)
            res["ai_status_code"] = "GOOGLE_NEWS_NO_AI"
            res["method"] = "google_news_original"
            logger.info(f"[AI] Google News — Ollama unavailable/failed, using cleaned original (GOOGLE_NEWS_NO_AI)")
            return res

        # STEP 2: Attempt Priority AI Chain
        raw = self._try_all_providers(prompt)
        
        if raw:
            result = _parse_result(raw, title, content)
            
            # STEP 3: Validate AI Output (Similarity Goal <= 70%)
            title_sim = compute_similarity(title, result["rephrased_title"])
            content_sim = compute_similarity(content, result["rephrased_content"])
            
            if title_sim <= 0.70 and content_sim <= 0.70:
                result["ai_status_code"] = "AI_SUCCESS"
                result["similarity_score"] = max(title_sim, content_sim)
                return result
            else:
                logger.warning(f"[AI] Similarity too high ({max(title_sim, content_sim):.2f}) - triggering fallback logic for {source_name}")
        
        # STEP 4: Fallback Strategy (MANDATORY)
        
        # CASE B: Google News — should never reach here (short-circuited above),
        # kept as absolute safety net
        if is_gnews:
            res = _original_fallback(title, content)
            res["ai_status_code"] = "GOOGLE_NEWS_NO_AI"
            res["method"] = "google_news_original_fallback"
            return res
            
        # CASE A/C: Stricter Retry
        retry_prompt = prompt + "\n\nFAIL: Previous attempt was too similar. REWRITE 100%. CHANGE EVERY SENTENCE STRUCTURE."
        raw_retry = self._try_all_providers(retry_prompt, limit_to_best=True)
        
        if raw_retry:
            result = _parse_result(raw_retry, title, content)
            title_sim = compute_similarity(title, result["rephrased_title"])
            content_sim = compute_similarity(content, result["rephrased_content"])
            
            if title_sim <= 0.70 and content_sim <= 0.70:
                result["ai_status_code"] = "AI_RETRY_SUCCESS"
                result["similarity_score"] = max(title_sim, content_sim)
                return result

        # FINAL FAIL
        res = _original_fallback(title, content)
        res["ai_status_code"] = "REWRITE_FAILED"
        res["method"] = "failed_manual_review_needed"
        return res

    def _try_all_providers(self, prompt: str, limit_to_best: bool = False) -> Optional[str]:
        """Iterate through providers in priority order."""
        # Check Ollama (Primary local fallback)
        raw = _try_ollama(prompt)
        if raw: return raw

        if limit_to_best: return None

        # Check Gemini keys
        for key in [settings.GEMINI_API_KEY, settings.GEMINI_API_KEY_SECONDARY, settings.GEMINI_API_KEY_TERTIARY]:
            raw = _try_gemini(key, prompt)
            if raw: return raw
            
        # Grok
        raw = _try_grok(prompt)
        if raw: return raw
        
        # OpenAI
        raw = _try_openai(prompt)
        if raw: return raw
        
        return None


    def analyze_reporter_draft(self, title: str, content: str) -> Dict:
        """Lightweight analytical call to suggest metadata for reporters."""
        prompt = f"""ANALYZE THIS DRAFT NEWS:
TITLE: {title}
CONTENT: {content[:1000]}

Based on the title and content, suggest EXACTLY ONE category from this allowed list: [{CATEGORIES_STR}].
Also suggest 5 relevant lowercase tags.

Return ONLY JSON:
{{
  "category": "SuggestedCategory",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}"""
        # Try primary gemini first
        keys = ["GEMINI_API_KEY", "GEMINI_API_KEY_SECONDARY", "GEMINI_API_KEY_TERTIARY"]
        for key_name in keys:
            key = getattr(settings, key_name, "")
            raw = _try_gemini(key, prompt, label=key_name)
            if raw:
                try:
                    m = re.search(r'\{[\s\S]*\}', raw)
                    if m: return json.loads(m.group())
                except: pass
        
        # Simple local fallback if AI fails
        return {"category": "Home", "tags": ["news"]}

ai_service = AIService()
