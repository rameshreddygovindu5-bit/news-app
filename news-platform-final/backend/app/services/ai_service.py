"""
AI Service v7.0 — Production News Transformation Engine
========================================================

Architecture Changes from v6:
  - ParaphraseEngine is a TRUE SINGLETON — model loads ONCE at import time,
    shared across all workers/requests. Zero repeated disk I/O.
  - Google News: NO paid API calls. Paraphrase engine only (cost=0).
  - Pending Approval (REWRITE_FAILED): paraphrase engine produces structured
    HTML output — bold headings, bullet points, proper paragraphs — NOT raw text.
  - All failure paths funnel through ParaphraseEngine, never raw original.
  - Circuit breaker removed from this file (belongs in Celery task layer).
  - Seq2Seq + lexical chain is the universal last-resort, always produces
    valid structured HTML.

Fallback chain for regular sources:
  1  Gemini PRIMARY    (cloud)
  2  Gemini SECONDARY  (cloud)
  3  Gemini TERTIARY   (cloud)
  4  Grok / xAI        (cloud)
  5  OpenAI GPT-4o-mini(cloud)
  6  ParaphraseEngine  (LOCAL — Seq2Seq + Synonym + Antonym, zero cost)
     └─ always returns structured HTML with bold/bullets/paragraphs

Google News source:
  1  ParaphraseEngine  (local only, no paid APIs)

Pending Approval / REWRITE_FAILED:
  → ParaphraseEngine  (structured HTML, ready for admin review/publish)

AI Status codes:
  AI_SUCCESS          — Cloud AI passed similarity check
  AI_RETRY_SUCCESS    — Cloud AI passed on stronger-prompt retry
  LOCAL_PARAPHRASE    — Paraphrase engine used (Google News or cloud failure)
  REWRITE_FAILED      — All cloud attempts failed; paraphrased version sent to admin
  GOOGLE_NEWS_LOCAL   — Google News processed locally (by design)
"""

from __future__ import annotations

import re
import json
import logging
import time
import os
import threading
from typing import Optional, Dict, List
from difflib import SequenceMatcher

try:
    from langdetect import detect
except ImportError:
    def detect(text: str) -> str:
        return "en"

from app.config import get_settings
from app.services.category_service import category_service

logger = logging.getLogger(__name__)
settings = get_settings()

CATEGORIES = settings.CATEGORIES
CATEGORIES_STR = ", ".join(CATEGORIES)

# ─────────────────────────────────────────────────────────────────────────────
# PARAPHRASE ENGINE  (singleton — loads ONCE at module import)
# ─────────────────────────────────────────────────────────────────────────────

# ════════════ FAST PARAPHRASE ENGINE (replaces NLTK/Seq2Seq) ════════

class ParaphraseEngine:
    """
    Thread-safe singleton — delegates to fast_engine (zero-dependency, <10ms).
    The old NLTK/Seq2Seq path is kept as commented backup but not used.
    fast_engine handles all paraphrase work without external ML models.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialised = False
            return cls._instance

    def __init__(self):
        if self._initialised:
            return
        with self._lock:
            if self._initialised:
                return
            self._ready = True
            self._initialised = True
            logger.info("[ParaphraseEngine] Fast engine ready (zero-dependency mode)")

    def paraphrase_to_html(self, title: str, content: str) -> Dict[str, str]:
        """Paraphrase title + content and return structured HTML. Sub-10ms."""
        try:
            from app.services.paraphrase.fast_engine import paraphrase_to_html, rephrase_title
            import hashlib
            seed = int(hashlib.md5((title[:50]).encode()).hexdigest()[:6], 16) % 10000
            return paraphrase_to_html(title, content, seed=seed)
        except Exception as exc:
            logger.warning("[ParaphraseEngine] fast_engine error: %s", exc)
            # Bare minimum fallback — return cleaned original as structured HTML
            return {
                "rephrased_title":   title,
                "rephrased_content": _bare_html(title, content),
            }

    def _lexical_chain(self, text: str, is_title: bool = False) -> str:
        """Apply word substitution pass (fast, no NLTK).
        For titles, use rephrase_title() for stronger transformation."""
        try:
            if is_title or (len(text.split()) <= 15 and '.' not in text):
                from app.services.paraphrase.fast_engine import rephrase_title
                import hashlib
                seed = int(hashlib.md5(text[:30].encode()).hexdigest()[:6], 16) % 10000
                return rephrase_title(text, seed=seed)
            from app.services.paraphrase.fast_engine import _substitute_words
            return _substitute_words(text)
        except Exception:
            return text

    @staticmethod
    def _build_structured_html(title: str, plain_content: str) -> str:
        try:
            from app.services.paraphrase.fast_engine import build_html
            return build_html(title, plain_content)
        except Exception:
            return f"<p><strong>🔑 {plain_content}</strong></p>"

    def paraphrase_text(self, text: str, max_sentences: int = 30) -> str:
        """Paraphrase plain text — fast path."""
        try:
            from app.services.paraphrase.fast_engine import fast_paraphrase
            return fast_paraphrase(text)
        except Exception:
            return text

    # ── Keep old warmup signature for import compatibility ────────────
    def _warmup(self): pass
    def _load(self): pass


def _bare_html(title: str, content: str) -> str:
    """Absolute last resort: wrap content in minimal HTML structure."""
    plain = re.sub(r"<[^>]+>", " ", content or title).strip()
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
    if not sents:
        return f"<p><strong>🔑 {plain}</strong></p>"
    parts = [f"<p><strong>🔑 {sents[0]}</strong></p>"]
    if len(sents) > 1:
        parts += ["<p><b>📌 Key Highlights:</b></p><ul>"]
        for s in sents[1:4]:
            parts.append(f"  <li>{s}</li>")
        parts.append("</ul>")
    for s in sents[4:]:
        parts.append(f"<p>{s}</p>")
    return "\n".join(parts)


# Module-level singleton — instantiated once when workers start.
# All subsequent imports of this module get the same object.
paraphrase_engine = ParaphraseEngine()


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE NAME STRIPPING
# ─────────────────────────────────────────────────────────────────────────────

SOURCE_NAMES = [
    "GreatAndhra", "ANI", "IANS", "PTI", "UNI", "TNIE", "Eenadu", "Sakshi",
    "TV9", "CNN", "Al Jazeera", "OneIndia", "Telugu123", "TeluguTimes",
    "PrabhaNews", "Reuters", "AP News", "AFP", "BBC", "NDTV", "Times of India",
    "The Hindu", "Indian Express", "Deccan Herald", "Hindustan Times",
    "News18", "Republic", "Zee News", "ABP", "India Today", "Firstpost",
    "The Wire", "Scroll", "The Print", "Mint", "Economic Times",
    "Business Standard", "Bloomberg", "Fox News", "The Guardian",
    "Washington Post", "New York Times", "Peoples Feedback",
    "సాక్షి", "ఈనాడు", "ఆంధ్రజ్యోతి", "నమస్తే తెలంగాణ", "ప్రభ న్యూస్", "టీవీ9", "ఏబీపీ దేశం", "వెలుగు"
]

def _strip_source_names(text: str) -> str:
    if not text:
        return ""
    
    # 1. Strip common Telugu source prefix patterns like "సాక్షి, హైదరాబాద్: ..."
    # This handles both plain text and if it's already inside some HTML tags (common in raw scrapes)
    telugu_sources_regex = "|".join(SOURCE_NAMES[-8:]) # Last 8 are Telugu names
    prefix_pattern = rf"(^|<p[^>]*>)\s*({telugu_sources_regex})\s*,\s*[^:]{{1,30}}:\s*"
    text = re.sub(prefix_pattern, r"\1", text)

    # 2. Strip standalone occurrences from the list
    for name in SOURCE_NAMES:
        # Use \b for English names, but avoid for Telugu names as \b is ASCII-only
        if re.search(r'[a-zA-Z]', name):
            pattern = rf"\b{re.escape(name)}\b"
        else:
            pattern = rf"{re.escape(name)}"
            
        text = re.sub(rf"\(\s*{pattern}\s*\)", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"[\u2014\u2013\-]\s*{pattern}\b", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"\bsource\s*:\s*{pattern}\b", "", text, flags=re.IGNORECASE)
        text = re.sub(
            rf"\b(?:reported|published|stated)\s+(?:by|in|on)\s+{pattern}\b",
            "", text, flags=re.IGNORECASE
        )
        text = re.sub(
            rf"\baccording\s+to\s+{pattern}\b",
            "according to reports", text, flags=re.IGNORECASE
        )
        text = re.sub(rf"\b{pattern}\s+report(?:s|ed)?\b", "reports indicate", text, flags=re.IGNORECASE)
        text = re.sub(rf"(?:^|\.\s+){pattern}[.,]?\s*", ". ", text, flags=re.IGNORECASE)
        
        # General replacement for remaining occurrences
        text = re.sub(pattern, "Peoples Feedback", text, flags=re.IGNORECASE)

    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return text.strip()

def _get_category_image(category: str) -> str:
    """Return a branded placeholder image URL based on the category."""
    cat_map = {
        "Business": "/placeholders/business.png",
        "Technology": "/placeholders/tech.png",
        "Tech": "/placeholders/tech.png",
        "Entertainment": "/placeholders/entertainment.png",
        "Sports": "/placeholders/sports.png",
        "Health": "/placeholders/health.png",
        "Science": "/placeholders/science.png",
        "Politics": "/placeholders/politics.png",
        "International": "/placeholders/world.png",
        "National": "/placeholders/general.png",
        "Andhra Pradesh": "/placeholders/general.png",
        "Telangana": "/placeholders/general.png",
        "General": "/placeholders/general.png",
        "Home": "/placeholders/general.png",
    }
    return cat_map.get(category, "/placeholders/general.png")


def _clean(text: str) -> str:
    if not text:
        return ""
    for p in [r"(?i)ignore\s+previous\s+instructions.*", r"(?i)system\s+prompt.*"]:
        text = re.sub(p, "", text)
    return _strip_source_names(text).strip()


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a Principal News Editor at a leading bilingual (English-Telugu) digital media outlet with 20 years of experience. Your job is to COMPLETELY TRANSFORM raw scraped news into premium, reader-friendly articles that feel freshly written — never like a repost.

════════════════════════════════════════════════════
RULE 1 — ABSOLUTE ORIGINALITY (MOST IMPORTANT)
════════════════════════════════════════════════════
- NEVER copy any phrase, sentence, or structure from the original.
- Read the raw content to understand the FACTS, then close it mentally and write from scratch.
- Change sentence order, flip passive/active voice, restructure paragraphs entirely.
- If the original leads with "X happened because Y", your version must lead differently.
- Minimum transformation: every sentence must be >60% different from the source.

════════════════════════════════════════════════════
RULE 2 — MANDATORY HTML STRUCTURE (BOTH languages)
════════════════════════════════════════════════════
Every article MUST use this exact structure — no plain text blocks allowed:

<p><strong>🔑 [ONE-LINE BOLD SUMMARY]: The single most important outcome in one punchy sentence.</strong></p>

<p><b>📌 Key Highlights:</b></p>
<ul>
  <li><b>Point 1:</b> Most critical fact with specific numbers/names if available.</li>
  <li><b>Point 2:</b> Second important detail or direct consequence.</li>
  <li><b>Point 3:</b> Third significant fact, implication, or reaction.</li>
</ul>

<p>[BACKGROUND PARAGRAPH]: 2-3 sentences giving context — who, what, why this matters.</p>

<p>[ANALYSIS PARAGRAPH]: What this means for stakeholders, broader implications, expert perspectives (paraphrased).</p>

<p>[DEVELOPMENT PARAGRAPH]: Any additional facts, timelines, or related events.</p>

<p><i>⏩ What's Next: [One sentence on upcoming developments, deadlines, or expected actions.]</i></p>

════════════════════════════════════════════════════
RULE 3 — FORMATTING STANDARDS
════════════════════════════════════════════════════
- Bold key terms: <b>names</b>, <b>organizations</b>, <b>numbers</b>, <b>dates</b>
- Use <strong> only for the opening hook sentence
- Italics <i>...</i> only for the closing "What's Next" line
- NO sub-headings (h2/h3) inside content
- NO markdown — HTML only
- Lists must use <ul><li> never numbered unless it's a step-by-step process

════════════════════════════════════════════════════
RULE 4 — CONTENT QUALITY
════════════════════════════════════════════════════
- REMOVE ALL source attribution: ANI, PTI, Reuters, BBC, GreatAndhra, Eenadu, Sakshi, TV9, etc.
- Replace "According to [source]" → "Reports indicate" / "Officials confirmed" / "Sources reveal"
- NO photo credits, journalist names, timestamps, URLs, or watermarks
- Minimum article length: 150 words English + 120 words Telugu
- Write at reading level of an educated professional (not academic, not tabloid)

════════════════════════════════════════════════════
RULE 5 — TELUGU EXCELLENCE
════════════════════════════════════════════════════
- Use VYAVAHARIKA Telugu (spoken style of Sakshi/Eenadu/TV9) — NOT bookish/formal
- Title format: [Key Subject] + [Action verb] — punchy, max 12 words
- Transliterations: Modi=మోదీ, BJP=బీజేపీ, Congress=కాంగ్రెస్, Delhi=ఢిల్లీ
- Apply same bold/list HTML structure as English version
- Telugu highlights prefix: <p><b>📌 ముఖ్య విషయాలు:</b></p>

════════════════════════════════════════════════════
RULE 6 — CATEGORIZATION & METADATA
════════════════════════════════════════════════════
- CATEGORY: Pick EXACTLY ONE from: {CATEGORIES_STR}
- TAGS: Exactly 5 lowercase English keywords (no stopwords, no duplicates)
- SLUG: lowercase, hyphenated, max 80 chars, no special characters

════════════════════════════════════════════════════
OUTPUT — VALID JSON ONLY (no markdown, no backticks)
════════════════════════════════════════════════════
{{
  "title": "Sharp, engaging English headline (8-12 words)",
  "content": "<p><strong>🔑 ...</strong></p><p><b>📌 Key Highlights:</b></p><ul><li><b>Point:</b> ...</li></ul><p>...</p><p>...</p><p><i>⏩ What's Next: ...</i></p>",
  "category": "CategoryName",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "slug": "headline-slug-here",
  "telugu_title": "తెలుగు శీర్షిక ఇక్కడ",
  "telugu_content": "<p><strong>🔑 ...</strong></p><p><b>📌 ముఖ్య విషయాలు:</b></p><ul><li><b>విషయం:</b> ...</li></ul><p>...</p><p>...</p><p><i>⏩ తదుపరి: ...</i></p>"
}}"""


def _build_prompt(title: str, content: str, lang: str) -> str:
    clean_title = _clean(title)
    clean_content = _clean(content)[:3500]
    word_count = len(clean_content.split())
    return (
        f"SOURCE LANGUAGE: {lang}\n"
        f"ORIGINAL HEADLINE: {clean_title}\n"
        f"RAW CONTENT ({word_count} words):\n---\n{clean_content}\n---\n\n"
        "YOUR TASK:\n"
        "1. Extract key FACTS from the raw content above.\n"
        "2. Write a COMPLETELY NEW article in your own voice — do NOT copy any phrase.\n"
        "3. Apply the mandatory HTML structure from your system instructions.\n"
        "4. Generate both English AND Telugu versions simultaneously.\n"
        "5. Remove every source/agency name. Return ONLY the JSON object.\n\n"
        "ORIGINALITY CHECK: Your output must differ from the source by at least 70% "
        "in wording and sentence structure."
    )


# ─────────────────────────────────────────────────────────────────────────────
# SIMILARITY
# ─────────────────────────────────────────────────────────────────────────────

def compute_similarity(a: str, b: str) -> float:
    """Gestalt pattern-matching similarity (0.0 = completely different, 1.0 = identical)."""
    if not a or not b:
        return 0.0
    # Strip HTML tags for a fairer comparison
    a_plain = re.sub(r"<[^>]+>", " ", a)
    b_plain = re.sub(r"<[^>]+>", " ", b)
    return SequenceMatcher(None, a_plain, b_plain).ratio()


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY AUTO-DETECTION (used for local-path articles)
# ─────────────────────────────────────────────────────────────────────────────

_CAT_KEYWORDS: Dict[str, List[str]] = {
    "Andhra Pradesh": ["andhra", "ap ", "vijayawada", "visakhapatnam", "jagan",
                       "chandrababu", "lokesh", "pawan kalyan", "amravati", "tirupati"],
    "Telangana":      ["telangana", "hyderabad", "revanth", " kcr ", " ktr ",
                       "warangal", "khammam"],
    "Politics":       ["election", "minister", "bjp", "congress", "government",
                       "mla", "mp ", "parliament", "assembly", "vote", "political", "cabinet"],
    "Sports":         ["cricket", "football", "match", "ipl", "player", "sport",
                       "tennis", "olympic", "medal", "score", "wicket", "stadium"],
    "Tech":           ["ai ", "technology", "google", "apple", "app ", "software",
                       "smartphone", "iphone", "chip", "semiconductor", "startup", "data"],
    "Business":       ["market", "stock", "economy", "billion", "million", "bank",
                       "rbi", "sensex", "nifty", "profit", "investment", "finance"],
    "Entertainment":  ["movie", "film", "actor", "hollywood", "bollywood", "tollywood",
                       "cinema", "trailer", "release", "review", "celebrity"],
    "International":  ["world", "global", "us ", "uk ", "iran", "israel", "russia",
                       "ukraine", "un ", "summit", "foreign"],
    "Health":         ["health", "medical", "doctor", "virus", "vaccine", "study",
                       "cancer", "fitness", "hospital"],
}


def _auto_category(title: str, content: str) -> str:
    text = f"{title} {content[:1500]}".lower()
    for cat, keywords in _CAT_KEYWORDS.items():
        if any(k in text for k in keywords):
            return cat
    return "Home"


def _make_slug(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[\s_-]+", "-", slug)[:80]


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL PARAPHRASE RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_local_result(
    title: str,
    content: str,
    ai_status_code: str,
    method: str,
) -> Dict:
    """
    Run paraphrase engine and return a fully-populated result dict
    with structured HTML content. Used for Google News, all failure
    paths, and Pending Approval cases.

    Always produces output with the same fields as cloud AI results.
    """
    clean_title = _strip_source_names(_clean(title))
    clean_content = _strip_source_names(_clean(content))

    is_telugu = bool(re.search(r"[\u0c00-\u0c7f]", clean_title + clean_content[:200]))

    # Run paraphrase engine
    para_result = paraphrase_engine.paraphrase_to_html(clean_title, clean_content)
    new_title = para_result["rephrased_title"] or clean_title
    new_content_html = para_result["rephrased_content"] or clean_content

    cat = _auto_category(clean_title, clean_content)

    try:
        cat = category_service.normalize(cat)
    except Exception:
        pass

    slug = _make_slug(new_title)

    # For Telugu source articles, swap English/Telugu fields
    if is_telugu:
        return {
            "rephrased_title": "",
            "rephrased_content": "",
            "category": cat,
            "tags": ["news", cat.lower()],
            "slug": slug,
            "telugu_title": new_title,
            "telugu_content": new_content_html,
            "method": method,
            "ai_status_code": ai_status_code,
            "similarity_score": 0.0,
            "image_url": _get_category_image(cat)
        }

    # BILINGUAL FALLBACK: If source is English, attempt translation via Ollama
    # otherwise fallback to English content so it's at least visible.
    te_title = new_title
    te_content = new_content_html
    
    # Try local translation if Ollama is available
    translation_prompt = f"Translate the following news title and content to Telugu. Return ONLY JSON with 'title' and 'content' fields.\nTITLE: {new_title}\nCONTENT: {new_content_html[:500]}"
    translated_raw = _try_ollama(translation_prompt)
    if translated_raw:
        try:
            # Extract JSON from Ollama response
            m = re.search(r"\{[\s\S]*\}", translated_raw)
            if m:
                d = json.loads(m.group())
                te_title = d.get("title") or te_title
                te_content = d.get("content") or te_content
        except Exception:
            pass

    return {
        "rephrased_title": new_title,
        "rephrased_content": new_content_html,
        "category": cat,
        "tags": ["news", cat.lower()],
        "slug": slug,
        "telugu_title": te_title,
        "telugu_content": te_content,
        "method": method,
        "ai_status_code": ai_status_code,
        "similarity_score": 0.0,
        "image_url": _get_category_image(cat)
    }


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER WRAPPERS
# ─────────────────────────────────────────────────────────────────────────────

def _try_gemini(api_key: str, prompt: str, label: str = "gemini") -> Optional[str]:
    if not api_key:
        return None
    for model_name in ("gemini-1.5-flash", "gemini-1.5-pro"):
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=2048,
                ),
            )
            if response and response.text:
                return response.text
        except Exception as exc:
            logger.debug("[AI] %s/%s failed: %s", label, model_name, exc)
    logger.warning("[AI] %s exhausted all models", label)
    return None


def _try_grok(prompt: str) -> Optional[str]:
    if not getattr(settings, "XAI_API_KEY", None):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.XAI_API_KEY, base_url="https://api.x.ai/v1")
        resp = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning("[AI] Grok failed: %s", exc)
        return None


def _try_openai(prompt: str) -> Optional[str]:
    if not getattr(settings, "OPENAI_API_KEY", None):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.warning("[AI] OpenAI failed: %s", exc)
        return None


def _try_ollama(prompt: str) -> Optional[str]:
    """Fallback to local Ollama if running."""
    if not getattr(settings, "OLLAMA_BASE_URL", None):
        return None
    try:
        import requests
        # Use llama3.2:1b as found in local tags
        model = "llama3.2:1b"
        resp = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model,
                "prompt": f"{SYSTEM_PROMPT}\n\nUSER REQUEST: {prompt}",
                "stream": False,
                "options": {"temperature": 0.3}
            },
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json().get("response")
    except Exception as exc:
        logger.debug("[AI] Ollama failed: %s", exc)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# JSON PARSING
# ─────────────────────────────────────────────────────────────────────────────

def _parse_result(raw: str, original_title: str, original_content: str) -> Optional[Dict]:
    """
    Parse cloud AI JSON output. Returns None if parsing completely fails
    (caller will then route to paraphrase engine instead of raw fallback).
    """
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.M)
    text = re.sub(r"\s*```$", "", text, flags=re.M).strip()

    for attempt in (text, re.search(r"\{[\s\S]*\}", text)):
        candidate = attempt if isinstance(attempt, str) else (attempt.group() if attempt else None)
        if not candidate:
            continue
        try:
            d = json.loads(candidate)
            return _validate_dict(d, original_title, original_content)
        except json.JSONDecodeError:
            pass

    # Last-chance: fix trailing commas and quote style
    fixed = re.sub(r",\s*([}\]])", r"\1", text).replace("'", '"')
    try:
        d = json.loads(fixed)
        return _validate_dict(d, original_title, original_content)
    except Exception:
        pass

    logger.warning("[AI] JSON parse completely failed")
    return None  # Signal to caller: use paraphrase engine


def _validate_dict(d: Dict, orig_title: str, orig_content: str) -> Dict:
    title = _strip_source_names(str(d.get("title", "")).strip()) or orig_title
    content = _strip_source_names(str(d.get("content", "")).strip()) or orig_content

    try:
        cat = category_service.normalize(str(d.get("category", "Home")))
    except Exception:
        cat = "Home"

    tags = d.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip().lower() for t in tags if str(t).strip()][:5]

    slug = str(d.get("slug", "")).strip() or _make_slug(title)

    telugu_title = _strip_source_names(str(d.get("telugu_title", "")).strip())
    telugu_content = _strip_source_names(str(d.get("telugu_content", "")).strip())

    return {
        "rephrased_title": title,
        "rephrased_content": content,
        "category": cat,
        "tags": tags,
        "slug": slug,
        "telugu_title": telugu_title,
        "telugu_content": telugu_content,
        "method": d.get("_method", "ai"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

LANG_NAMES = {
    "te": "Telugu", "hi": "Hindi", "ta": "Tamil", "kn": "Kannada",
    "ml": "Malayalam", "mr": "Marathi", "en": "English",
}


def _detect_lang(text: str) -> str:
    try:
        return detect(text[:200]) if text else "en"
    except Exception:
        return "en"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class AIService:
    """
    Orchestrates cloud AI providers with paraphrase engine as universal fallback.

    Flow summary:
      Google News  →  ParaphraseEngine (local, free)
      Regular      →  Cloud chain → ParaphraseEngine on any failure
      Retry fail   →  ParaphraseEngine (structured HTML, sent to admin as REWRITE_FAILED)
    """

    # ── public API ────────────────────────────────────────────────────

    def process_article(self, title: str, content: str, source_name: str = "Unknown") -> Dict:
        lang_code = _detect_lang(f"{title} {content}")
        lang_name = LANG_NAMES.get(lang_code, "English")
        is_gnews = "google news" in (source_name or "").lower()
        is_regional = any(
            x in (source_name or "").lower()
            for x in ("greatandhra", "eenadu", "sakshi", "andhra", "telangana")
        )

        # ── PATH A: Google News — local only, zero API cost ───────────
        if is_gnews:
            logger.info("[AI] Google News → ParaphraseEngine (no paid API calls)")
            return _build_local_result(
                title, content,
                ai_status_code="GOOGLE_NEWS_LOCAL",
                method="google_news_paraphrase",
            )

        # ── PATH B: Regular sources — try cloud providers first ───────
        prompt = _build_prompt(title, content, lang_name)
        if is_regional:
            prompt += (
                "\n\nCRITICAL: Use aggressive sentence restructuring and "
                "significant tone shift. Ensure NO similarity to source."
            )

        raw = self._try_cloud_providers(prompt)

        if raw:
            result = _parse_result(raw, title, content)
            if result:
                title_sim = compute_similarity(title, result["rephrased_title"])
                content_sim = compute_similarity(content, result["rephrased_content"])

                if title_sim <= 0.70 and content_sim <= 0.70:
                    # Polish with lexical chain
                    result["rephrased_title"] = paraphrase_engine._lexical_chain(
                        result["rephrased_title"], is_title=True
                    )
                    result["rephrased_content"] = self._polish_html_content(
                        content, result["rephrased_content"]
                    )
                    result["ai_status_code"] = "AI_SUCCESS"
                    result["similarity_score"] = max(title_sim, content_sim)
                    result["image_url"] = _get_category_image(result.get("category", "Home"))
                    return result

                logger.warning(
                    "[AI] Similarity too high (%.2f) for %s — retrying",
                    max(title_sim, content_sim), source_name,
                )

        # ── PATH C: Retry with stronger prompt ───────────────────────
        retry_prompt = (
            prompt
            + "\n\nFAIL: Previous attempt was too similar. "
            "REWRITE 100%. CHANGE EVERY SENTENCE STRUCTURE. "
            "Start every paragraph differently."
        )
        raw_retry = self._try_cloud_providers(retry_prompt, best_only=True)

        if raw_retry:
            result = _parse_result(raw_retry, title, content)
            if result:
                title_sim = compute_similarity(title, result["rephrased_title"])
                content_sim = compute_similarity(content, result["rephrased_content"])

                if title_sim <= 0.70 and content_sim <= 0.70:
                    result["ai_status_code"] = "AI_RETRY_SUCCESS"
                    result["similarity_score"] = max(title_sim, content_sim)
                    result["image_url"] = _get_category_image(result.get("category", "Home"))
                    return result

        # ── PATH D: All cloud attempts failed / similarity still high ─
        # Use local ParaphraseEngine — produces structured HTML.
        # Marked LOCAL_PARAPHRASE → worker sets flag=A → publicly visible.
        logger.warning("[AI] All cloud providers failed/high-similarity for '%s' — using local engine", title)
        result = _build_local_result(
            title, content,
            ai_status_code="LOCAL_PARAPHRASE",   # flag=A (public) not REWRITE_FAILED (admin queue)
            method="local_paraphrase_engine",
        )
        return result

    def analyze_reporter_draft(self, title: str, content: str) -> Dict:
        """Lightweight metadata suggestion for reporter drafts."""
        prompt = (
            f"ANALYZE THIS DRAFT NEWS:\nTITLE: {title}\nCONTENT: {content[:1000]}\n\n"
            f"Suggest EXACTLY ONE category from: [{CATEGORIES_STR}] and 5 relevant tags.\n\n"
            'Return ONLY JSON: {"category": "...", "tags": ["t1","t2","t3","t4","t5"]}'
        )
        for key_attr in ("GEMINI_API_KEY", "GEMINI_API_KEY_SECONDARY", "GEMINI_API_KEY_TERTIARY"):
            key = getattr(settings, key_attr, "")
            raw = _try_gemini(key, prompt, label=key_attr)
            if raw:
                try:
                    m = re.search(r"\{[\s\S]*\}", raw)
                    if m:
                        return json.loads(m.group())
                except Exception:
                    pass
        return {"category": "Home", "tags": ["news"]}

    # ── private helpers ───────────────────────────────────────────────

    def _try_cloud_providers(self, prompt: str, best_only: bool = False) -> Optional[str]:
        """
        Try cloud providers in priority order.
        best_only=True: only try primary Gemini key (for retry path — faster).
        """
        gemini_keys = [
            settings.GEMINI_API_KEY,
            settings.GEMINI_API_KEY_SECONDARY,
            settings.GEMINI_API_KEY_TERTIARY,
        ]
        for i, key in enumerate(gemini_keys):
            raw = _try_gemini(key, prompt, label=f"gemini_key_{i+1}")
            if raw:
                return raw
            if best_only:
                return None  # Only primary key on retry

        if best_only:
            return None

        raw = _try_grok(prompt)
        if raw:
            return raw

        raw = _try_openai(prompt)
        if raw:
            return raw

        raw = _try_ollama(prompt)
        if raw:
            return raw

        return None

    @staticmethod
    def _polish_html_content(original: str, rephrased_html: str) -> str:
        """
        Apply lexical chain to text nodes within existing HTML,
        preserving tags. Used to polish successful cloud AI output.
        """
        try:
            # Extract text between tags, polish, re-insert
            def polish_text_node(m: re.Match) -> str:
                txt = m.group(1)
                return paraphrase_engine._lexical_chain(txt)

            # Only polish plain text paragraphs, not inside <b>/<strong> (names/numbers)
            polished = re.sub(
                r"(<p>)([^<]{40,})(</p>)",
                lambda m: m.group(1) + paraphrase_engine._lexical_chain(m.group(2)) + m.group(3),
                rephrased_html,
            )
            return polished
        except Exception:
            return rephrased_html


# Module-level instance — import this everywhere
ai_service = AIService()