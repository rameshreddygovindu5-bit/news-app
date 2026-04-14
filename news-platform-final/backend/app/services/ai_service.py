"""
AI Service v4.0 — Production News Transformation Engine
========================================================
Fallback chain (first success wins):
  1. Google Gemini PRIMARY key
  2. Google Gemini SECONDARY key
  3. OpenAI GPT-4o-mini
  4. Ollama local LLM
  5. ORIGINAL content (no AI — stored as-is, clearly marked)

Output: English rephrased article + Telugu translation, always.
Parallel processing supported for batches.
"""
import re, json, logging, time, hashlib
from typing import Optional, Dict, List
from langdetect import detect

from app.config import get_settings
from app.services.category_service import category_service

logger = logging.getLogger(__name__)
settings = get_settings()

CATEGORIES = settings.CATEGORIES
CATEGORIES_STR = ", ".join(CATEGORIES)

# ── Input sanitization ────────────────────────────────────────────────
def _clean(text: str) -> str:
    if not text: return ""
    for p in [r"(?i)ignore\s+previous\s+instructions.*", r"(?i)system\s+prompt.*"]:
        text = re.sub(p, "", text)
    for p in [
        r"(?i)\b(?:as\s+)?(?:reported|published|stated)\s+(?:by|in|on)\s+\w+\b",
        r"(?i)\((?:ANI|IANS|PTI|UNI|TNIE|GreatAndhra|CNN)\)",
        r"(?i)\b(?:GreatAndhra|ANI|IANS|PTI|Eenadu|Sakshi|TV9|CNN)\b[.,]?\s*",
    ]:
        text = re.sub(p, "", text)
    return text.strip()

# ── System prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a senior multilingual News Journalist, SEO Specialist, and Telugu language expert working for Peoples Feedback news platform.

YOUR TASK: Transform raw scraped news into TWO versions — a polished English article AND a Telugu translation.

═══ ENGLISH ARTICLE RULES ═══
1. REWRITE 100%: Never copy the original title or any sentence verbatim. Every sentence must be original.
2. TITLE: Write a compelling, click-worthy English headline (8–12 words). Use active voice. Include key subject + action.
3. STRUCTURE — use proper HTML tags for rich display:
   • Opening <p>: Hook readers with the most important fact (who/what/when/where/why in first 2 sentences)
   • <p><b>Key Highlights:</b></p><ul>: 3–5 concise bullet facts
   • 2–3 body <p>: Context, background, implications, quotes (paraphrased)
   • Closing <p>: What happens next / why it matters to readers
4. SEO: Natural keywords in title and opening paragraph. No stuffing.
5. CLEAN: Remove ALL source names, reporter credits, photo captions, URLs, ads, timestamps.
6. TONE: Professional, neutral journalism. No sensationalism. Facts-first.

═══ TELUGU TRANSLATION RULES ═══  
7. Translate the rephrased English into natural, everyday Telugu (not literal word-for-word).
8. Telugu title: Concise (8–12 words in Telugu script).
9. Telugu content: Same HTML structure as English (<p>, <ul>, <li>).
10. Use simple, clear Telugu that general readers understand — avoid overly formal/archaic words.
11. Keep proper nouns (person names, place names) in their common Telugu form or in English.

═══ CATEGORIZATION ═══
12. CATEGORY: Choose EXACTLY ONE from: {CATEGORIES_STR}
    Rules: Politics=government/elections, Business=economy/finance, Tech=technology/AI/gadgets,
    Health=medicine/wellness, Science=research/space/environment, Entertainment=movies/music/celebrity,
    Sports=cricket/football/games, Events=festivals/events, World=international, Home=everything else
13. TAGS: Exactly 5 lowercase English keywords (no hashtags, no commas within a tag)
14. SLUG: URL-safe title (lowercase, hyphens only, max 8 meaningful words, no stopwords)

═══ OUTPUT — CRITICAL ═══
Return ONLY a valid JSON object. No markdown, no backticks, no explanation text before or after.
{{
  "title": "Compelling English headline here",
  "content": "<p>Opening hook paragraph...</p><p><b>Key Highlights:</b></p><ul><li>Key fact 1</li><li>Key fact 2</li><li>Key fact 3</li></ul><p>Context paragraph...</p><p>Closing paragraph...</p>",
  "category": "ExactCategoryName",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "slug": "seo-friendly-slug-here",
  "telugu_title": "తెలుగు శీర్షిక ఇక్కడ",
  "telugu_content": "<p>తెలుగు ప్రారంభ పేరా...</p><ul><li>ముఖ్య విషయం 1</li><li>ముఖ్య విషయం 2</li></ul><p>వివరాలు...</p>"
}}"""

def _build_prompt(title: str, content: str, lang: str) -> str:
    return f"""LANGUAGE: {lang}
ORIGINAL HEADLINE: {_clean(title)}
RAW CONTENT: {_clean(content)[:3000]}

TASK: Rewrite into English + Telugu following all rules. Return JSON only."""


def _parse_result(raw: str, original_title: str, original_content: str) -> Dict:
    """Parse AI JSON output with multiple fallback strategies."""
    text = raw.strip()
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.M)
    text = re.sub(r'\s*```$', '', text, flags=re.M)
    text = text.strip()

    # Try direct parse
    try:
        d = json.loads(text)
        return _validate(d, original_title, original_content)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            d = json.loads(m.group())
            return _validate(d, original_title, original_content)
        except json.JSONDecodeError:
            pass

    # Try fixing common issues (trailing commas, single quotes)
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    fixed = fixed.replace("'", '"')
    try:
        d = json.loads(fixed)
        return _validate(d, original_title, original_content)
    except Exception:
        pass

    logger.warning("[AI] JSON parse failed, returning original content")
    return _original_fallback(original_title, original_content)


def _validate(d: Dict, orig_title: str, orig_content: str) -> Dict:
    """Ensure all required fields are present and valid."""
    title = str(d.get("title", "")).strip() or orig_title
    content = str(d.get("content", "")).strip() or orig_content
    cat = category_service.normalize(str(d.get("category", "Home")))
    tags = d.get("tags", [])
    if not isinstance(tags, list): tags = []
    tags = [str(t).strip().lower() for t in tags if str(t).strip()][:5]
    slug = str(d.get("slug", "")).strip()
    if not slug:
        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
        slug = re.sub(r'[\s_-]+', '-', slug)[:80]
    return {
        "rephrased_title": title,
        "rephrased_content": content,
        "category": cat,
        "tags": tags,
        "slug": slug,
        "telugu_title": str(d.get("telugu_title", "")).strip(),
        "telugu_content": str(d.get("telugu_content", "")).strip(),
        "method": d.get("_method", "ai"),
    }


def _original_fallback(title: str, content: str) -> Dict:
    """Return original content when all AI providers fail."""
    slug = re.sub(r'[^\w\s-]', '', title.lower()).strip()
    slug = re.sub(r'[\s_-]+', '-', slug)[:80]
    return {
        "rephrased_title": title,
        "rephrased_content": content or title,
        "category": "Home",
        "tags": [],
        "slug": slug,
        "telugu_title": "",
        "telugu_content": "",
        "method": "original",
    }


# ── Provider implementations ───────────────────────────────────────────

def _try_gemini(api_key: str, prompt: str, label: str = "gemini") -> Optional[str]:
    if not api_key: return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=SYSTEM_PROMPT,
            generation_config={"temperature": 0.4, "max_output_tokens": 2048},
        )
        resp = model.generate_content(prompt)
        return resp.text
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
                "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
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


# ── Main process_article ───────────────────────────────────────────────

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
        """
        Process a single article through the AI chain.
        Returns dict with rephrased_title, rephrased_content, telugu_title,
        telugu_content, category, tags, slug, method.
        """
        lang_code = _detect_lang(f"{title} {content}")
        lang_name = LANG_NAMES.get(lang_code, "Unknown")
        prompt = _build_prompt(title, content, lang_name)

        raw: Optional[str] = None

        # 1. Gemini PRIMARY
        raw = _try_gemini(settings.GEMINI_API_KEY, prompt, "Gemini-Primary")
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "gemini_primary"
            logger.info(f"[AI] ✓ Gemini-Primary: {title[:50]}")
            return result

        # 2. Gemini SECONDARY
        raw = _try_gemini(settings.GEMINI_API_KEY_SECONDARY, prompt, "Gemini-Secondary")
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "gemini_secondary"
            logger.info(f"[AI] ✓ Gemini-Secondary: {title[:50]}")
            return result

        # 3. OpenAI
        raw = _try_openai(prompt)
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "openai"
            logger.info(f"[AI] ✓ OpenAI: {title[:50]}")
            return result

        # 4. Ollama local
        raw = _try_ollama(prompt)
        if raw:
            result = _parse_result(raw, title, content)
            result["method"] = "ollama"
            logger.info(f"[AI] ✓ Ollama: {title[:50]}")
            return result

        # 5. Original content fallback
        logger.warning(f"[AI] All providers failed — keeping original: {title[:50]}")
        return _original_fallback(title, content)


ai_service = AIService()
