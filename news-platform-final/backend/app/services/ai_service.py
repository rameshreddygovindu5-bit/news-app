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


SYSTEM_PROMPT = f"""You are a senior multilingual News Journalist, SEO Specialist, and Telugu language expert working for an independent news platform.

YOUR TASK: Transform raw scraped news into TWO versions — a polished English article AND a Telugu translation.

=== COPYRIGHT & ORIGINALITY — CRITICAL ===
1. REWRITE 100%: Never copy the original title or any sentence verbatim. Every sentence MUST be original.
2. Paraphrase all facts into your own words — change sentence structure, word choice, and phrasing completely.
3. REMOVE all source names, agency credits (ANI, Reuters, PTI, CNN, etc.), reporter bylines, photo credits, URLs, timestamps, ads, and any attribution.
4. Replace "According to [Source]" with neutral phrasing like "Reports indicate", "Officials stated", or present the facts directly.
5. DO NOT mention any news agency, publication, or website name anywhere in the output.

=== ENGLISH ARTICLE RULES ===
6. TITLE: Write a compelling, click-worthy English headline (8-12 words). Active voice. Key subject + action.
7. STRUCTURE — use proper HTML tags. PRESERVE the logical structure of the original:
   - If the original uses numbered lists (1. 2. 3.), use <ol><li> in output
   - If the original uses bullet points, use <ul><li> in output
   - If the original uses alphabetical ordering (a. b. c.), preserve it with appropriate markup
   - Opening <p>: Hook readers with the most important fact
   - <p><b>Key Highlights:</b></p><ul>: 3-5 concise bullet facts
   - 2-3 body <p>: Context, background, implications (paraphrased quotes, never direct)
   - Closing <p>: What happens next / why it matters
8. PARAGRAPHS: Maintain proper paragraph breaks. Each distinct topic or idea in its own <p> tag. Do NOT merge everything into one block.
9. SEO: Natural keywords in title and opening paragraph.
10. TONE: Professional, neutral journalism. Facts-first.

=== TELUGU TRANSLATION RULES ===
11. Translate the rephrased English into natural, everyday Telugu (not literal word-for-word).
12. Telugu title: Concise (8-12 words in Telugu script).
13. Telugu content: Same HTML structure as English (<p>, <ul>, <li>, <ol>).
14. Use simple, clear Telugu. Keep proper nouns in common Telugu form or English.

=== CATEGORIZATION ===
15. CATEGORY: Choose EXACTLY ONE from: {CATEGORIES_STR}
16. TAGS: Exactly 5 lowercase English keywords
17. SLUG: URL-safe title (lowercase, hyphens, max 8 words)

=== OUTPUT — CRITICAL ===
Return ONLY a valid JSON object. No markdown, no backticks, no text before or after.
{{
  "title": "Compelling English headline here",
  "content": "<p>Opening hook paragraph...</p><p><b>Key Highlights:</b></p><ul><li>Key fact 1</li></ul><p>Context paragraph...</p><p>Closing paragraph...</p>",
  "category": "ExactCategoryName",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "slug": "seo-friendly-slug-here",
  "telugu_title": "తెలుగు శీర్షిక ఇక్కడ",
  "telugu_content": "<p>తెలుగు ప్రారంభ పేరా...</p><ul><li>ముఖ్య విషయం 1</li></ul><p>వివరాలు...</p>"
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
    """Return cleaned, formatted original content when all AI providers fail.
    Applies: source-name removal, paragraph formatting, sentence splitting,
    bold highlights on key phrases, list structure preservation,
    basic auto-categorization, and proper slug generation."""
    clean_title = _strip_source_names(title).strip()
    clean_content = _strip_source_names(content or title).strip()

    # Format content with proper HTML paragraph structure
    if clean_content and not re.search(r'<(p|div|ul|ol|br)', clean_content, re.I):
        # Detect and preserve numbered/alphabetical lists
        lines = re.split(r'\n', clean_content)
        formatted_parts = []
        current_list_type = None  # 'ol' or 'ul' or None
        current_items = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                # Close any open list
                if current_list_type and current_items:
                    tag = current_list_type
                    formatted_parts.append(f'<{tag}>{"".join(f"<li>{it}</li>" for it in current_items)}</{tag}>')
                    current_items = []
                    current_list_type = None
                continue

            # Check for numbered list items (1. 2. 3. or 1) 2) 3))
            num_match = re.match(r'^(\d+)[.)\]]\s+(.+)', stripped)
            # Check for alphabetical list items (a. b. c. or a) b))
            alpha_match = re.match(r'^([a-zA-Z])[.)\]]\s+(.+)', stripped)
            # Check for bullet list items (- or * or •)
            bullet_match = re.match(r'^[-*•]\s+(.+)', stripped)

            if num_match:
                if current_list_type != 'ol' and current_items:
                    tag = current_list_type or 'p'
                    if tag == 'p':
                        formatted_parts.append(f'<p>{" ".join(current_items)}</p>')
                    else:
                        formatted_parts.append(f'<{tag}>{"".join(f"<li>{it}</li>" for it in current_items)}</{tag}>')
                    current_items = []
                current_list_type = 'ol'
                current_items.append(num_match.group(2).strip())
            elif alpha_match and len(alpha_match.group(1)) == 1:
                if current_list_type != 'ol' and current_items:
                    tag = current_list_type or 'p'
                    if tag == 'p':
                        formatted_parts.append(f'<p>{" ".join(current_items)}</p>')
                    else:
                        formatted_parts.append(f'<{tag}>{"".join(f"<li>{it}</li>" for it in current_items)}</{tag}>')
                    current_items = []
                current_list_type = 'ol'
                current_items.append(alpha_match.group(2).strip())
            elif bullet_match:
                if current_list_type != 'ul' and current_items:
                    tag = current_list_type or 'p'
                    if tag == 'p':
                        formatted_parts.append(f'<p>{" ".join(current_items)}</p>')
                    else:
                        formatted_parts.append(f'<{tag}>{"".join(f"<li>{it}</li>" for it in current_items)}</{tag}>')
                    current_items = []
                current_list_type = 'ul'
                current_items.append(bullet_match.group(1).strip())
            else:
                # Regular paragraph line
                if current_list_type and current_items:
                    tag = current_list_type
                    formatted_parts.append(f'<{tag}>{"".join(f"<li>{it}</li>" for it in current_items)}</{tag}>')
                    current_items = []
                    current_list_type = None
                formatted_parts.append(f'<p>{stripped}</p>')

        # Close any remaining list
        if current_list_type and current_items:
            tag = current_list_type
            formatted_parts.append(f'<{tag}>{"".join(f"<li>{it}</li>" for it in current_items)}</{tag}>')
        elif current_items:
            formatted_parts.append(f'<p>{" ".join(current_items)}</p>')

        if formatted_parts:
            clean_content = ''.join(formatted_parts)
        else:
            # Fallback: split by sentences for readability
            paragraphs = re.split(r'\n\s*\n', clean_content)
            paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 10]
            if paragraphs:
                if len(paragraphs) == 1 and len(paragraphs[0]) > 300:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraphs[0])
                    chunks = []
                    current = []
                    for s in sentences:
                        current.append(s)
                        if len(current) >= 3:
                            chunks.append(' '.join(current))
                            current = []
                    if current:
                        chunks.append(' '.join(current))
                    clean_content = ''.join(f'<p>{c}</p>' for c in chunks)
                else:
                    clean_content = ''.join(f'<p>{p}</p>' for p in paragraphs)

    # Add bold highlights to the first sentence of first paragraph for emphasis
    if '<p>' in clean_content:
        def bold_first_sentence(match):
            inner = match.group(1)
            # Bold the first sentence only
            parts = re.split(r'(?<=[.!?])\s+', inner, maxsplit=1)
            if len(parts) > 1:
                return f'<p><b>{parts[0]}</b> {parts[1]}</p>'
            return f'<p><b>{inner}</b></p>'
        # Only bold the first paragraph
        clean_content = re.sub(r'<p>(.*?)</p>', bold_first_sentence, clean_content, count=1, flags=re.S)

    # Basic auto-categorization from keywords
    cat = "Home"
    text_lower = f"{clean_title} {clean_content[:500]}".lower()
    cat_keywords = {
        "Sports": ["cricket", "football", "tennis", "ipl", "match", "player", "team", "sport", "game", "nba", "nfl"],
        "Tech": ["technology", "software", "ai ", "google", "apple", "microsoft", "startup", "app ", "cyber", "digital", "data"],
        "Politics": ["election", "minister", "government", "congress", "bjp", "parliament", "vote", "political", "policy", "senate"],
        "Business": ["market", "stock", "economy", "revenue", "company", "billion", "million", "trade", "invest", "bank", "financial"],
        "Health": ["health", "medical", "doctor", "hospital", "disease", "vaccine", "drug", "patient", "treatment", "who "],
        "Entertainment": ["movie", "film", "actor", "actress", "bollywood", "hollywood", "music", "celebrity", "oscar", "grammy"],
        "Science": ["research", "study", "scientist", "space", "nasa", "planet", "climate", "environment", "fossil"],
        "World": ["ukraine", "russia", "china", "europe", "international", "global", "un ", "nato", "foreign"],
    }
    for c, keywords in cat_keywords.items():
        if any(kw in text_lower for kw in keywords):
            cat = c
            break

    # Generate slug
    slug = re.sub(r'[^\w\s-]', '', clean_title.lower()).strip()
    slug = re.sub(r'[\s_-]+', '-', slug)[:80]

    # Generate basic tags
    words = re.findall(r'\b[a-z]{4,}\b', text_lower)
    word_freq = {}
    stopwords = {"that", "this", "with", "from", "have", "been", "were", "will", "also", "which", "their", "about", "said", "more", "than", "into", "after", "some", "when", "would", "could"}
    for w in words:
        if w not in stopwords:
            word_freq[w] = word_freq.get(w, 0) + 1
    tags = sorted(word_freq, key=word_freq.get, reverse=True)[:5]

    logger.warning(f"[AI] FALLBACK: Using cleaned original for '{clean_title[:50]}' — configure AI API keys for proper rephrasing")

    return {
        "rephrased_title": clean_title,
        "rephrased_content": clean_content,
        "category": cat,
        "tags": tags,
        "slug": slug,
        "telugu_title": "",
        "telugu_content": "",
        "method": "original_cleaned",
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


ai_service = AIService()
