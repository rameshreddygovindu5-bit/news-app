"""
AI Service v5.0 — Production News Transformation Engine
========================================================
Fallback chain (Priority 1 → 4, then original):
  Priority 1: Google Gemini PRIMARY key
  Priority 2: Google Gemini SECONDARY key
  Priority 3: OpenAI GPT-4o-mini
  Priority 4: Ollama local LLM
  Last Resort: ORIGINAL content — cleaned of source names, reformatted to
               avoid copyright issues, paragraphs preserved.

Output: English rephrased article + Telugu translation, always.
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
    text_lower = f"{clean_title} {clean_content[:500]}".lower()
    cat_keywords = {
        "Sports": ["cricket", "football", "match", "ipl", "player", "sport"],
        "Tech": ["ai ", "technology", "google", "apple", "app ", "software"],
        "Politics": ["election", "minister", "bjp", "congress", "government"],
        "Business": ["market", "stock", "economy", "billion", "million", "bank"],
        "Entertainment": ["movie", "film", "actor", "hollywood", "bollywood"],
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
    try:
        # Use new Client SDK (v2 API style)
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.4,
                max_output_tokens=2048,
            )
        )
        if not response or not response.text:
            return None
        return response.text
    except Exception as e:
        logger.warning(f"[AI] {label} failed: {e}")
        return None


def _try_openai(prompt: str) -> Optional[str]:
    if not settings.OPENAI_API_KEY: return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
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


class AIService:
    def process_article(self, title: str, content: str) -> Dict:
        """Process through AI chain: P1 Gemini -> P2 Gemini2 -> P3 Gemini3 -> P4 OpenAI -> P5 Ollama -> Original cleaned."""
        lang_code = _detect_lang(f"{title} {content}")
        lang_name = LANG_NAMES.get(lang_code, "Unknown")
        prompt = _build_prompt(title, content, lang_name)

        raw: Optional[str] = None

        # Priority 1: Gemini PRIMARY
        raw = _try_gemini(settings.GEMINI_API_KEY, prompt, "Gemini-Primary")
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "gemini_primary"
            logger.info(f"[AI] P1-Gemini-Primary OK: {title[:50]}")
            return result

        # Priority 2: Gemini SECONDARY
        raw = _try_gemini(settings.GEMINI_API_KEY_SECONDARY, prompt, "Gemini-Secondary")
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "gemini_secondary"
            logger.info(f"[AI] P2-Gemini-Secondary OK: {title[:50]}")
            return result

        # Priority 3: Gemini TERTIARY
        tertiary_key = getattr(settings, "GEMINI_API_KEY_TERTIARY", "")
        raw = _try_gemini(tertiary_key, prompt, "Gemini-Tertiary")
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "gemini_tertiary"
            logger.info(f"[AI] P3-Gemini-Tertiary OK: {title[:50]}")
            return result

        # Priority 4: OpenAI
        raw = _try_openai(prompt)
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "openai"
            logger.info(f"[AI] P4-OpenAI OK: {title[:50]}")
            return result

        # Priority 5: Ollama local
        raw = _try_ollama(prompt)
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "ollama"
            logger.info(f"[AI] P5-Ollama OK: {title[:50]}")
            return result

        # Last Resort: Original cleaned
        logger.warning(f"[AI] All providers failed — cleaned original: {title[:50]}")
        return _original_fallback(title, content)


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
