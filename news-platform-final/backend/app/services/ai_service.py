"""
AI Service v3.0 — Production News Transformation Engine

Pipeline: Scrape → Detect Language → Translate to English → AI Rephrase → Categorize → Tag → Slug

Providers (in order):
  1. Google Gemini (PRIMARY) — fast, free tier
  2. OpenAI GPT-4o-mini (FALLBACK) — reliable, paid
  3. Fast Local Rephrase (LAST RESORT) — no API, instant

Output is ALWAYS English-only, fully original, publication-ready.
"""

import re
import json
import logging
import time
import concurrent.futures
from typing import Optional, Dict, Tuple, List
from difflib import SequenceMatcher
from langdetect import detect

from app.config import get_settings
from app.services.category_service import category_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Sync with settings.CATEGORIES
CATEGORIES = settings.CATEGORIES
CATEGORIES_STR = ", ".join(CATEGORIES)

# ─────────────────────────────────────────────
# 1. INPUT SANITIZATION
# ─────────────────────────────────────────────

def sanitize_input(text: str) -> str:
    if not text:
        return ""
    for p in [r"(?i)ignore\s+previous\s+instructions.*", r"(?i)system\s+prompt.*"]:
        text = re.sub(p, "", text)
    return text.strip()


def strip_sources(text: str) -> str:
    for p in [
        r"(?i)\b(?:as\s+)?(?:reported|published|stated|featured|carried)\s+(?:by|in|on|at)\s+\w+\b",
        r"(?i)\((?:ANI|IANS|PTI|UNI|TNIE|GreatAndhra)\)",
        r"(?i)\b(?:GreatAndhra|ANI|IANS|PTI|Eenadu|Sakshi|TV9)\b[.,]?\s*",
    ]:
        text = re.sub(p, "", text)
    return text.strip()


# ─────────────────────────────────────────────
# 2. PRODUCTION SYSTEM PROMPT (from requirements doc)
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a professional News Journalist and SEO Expert.
Your task is to transform raw scraped news content into a COMPLETELY ORIGINAL news article.

Strict Guidelines to Avoid Copyright Issues:
1. REWRITE EVERYTHING: You must rewrite the title and content 100%. Do NOT use any phrasing from the original source.
2. TITLE: Create a fresh, journalistic English title. Never use the original headline as is.
3. LANGUAGE: If the input is in Telugu or any other language, translate AND rewrite it into high-quality English.
4. STRUCTURE: 
   - Start with a compelling opening paragraph.
   - Use a "Key Highlights" section with a <ul> list.
   - Use 3-5 distinct paragraphs (<p> tags).
5. CATEGORIES: You MUST classify the article into EXACTLY ONE of these categories: {CATEGORIES_STR}.
   - Choose the most relevant one. Use "Home" only as a last resort.
6. NO TRACES: Remove any mentions of the original source website, reporter names, or photo credits.

FINAL OUTPUT: You must respond ONLY with a clean JSON object in this format:
{{
  "title": "A 100% original English headline",
  "content": "<p>Professional intro...</p><p><b>Key Highlights:</b></p><ul><li>Fact 1</li></ul><p>Detail paragraph 1...</p><p>Closing...</p>",
  "category": "One of: {CATEGORIES_STR}",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "slug": "original-seo-friendly-slug"
}}"""


def build_prompt(title: str, content: str, lang_name: str) -> str:
    t = sanitize_input(strip_sources(title))
    c = sanitize_input(strip_sources(content))
    return f"""SOURCE DATA:
Language: {lang_name}
Original Headline: {t}
Raw Content: {c}

TASK:
1. Translate to English if needed.
2. Rewrite the headline to be 100% unique but factually accurate.
3. Completely rephrase the article body into professional journalistic English.
4. Classify it strictly into one of: {CATEGORIES_STR}.
5. Return the JSON object only."""


# ─────────────────────────────────────────────
# 3. OUTPUT PARSING (JSON primary, tag fallback)
# ─────────────────────────────────────────────

def parse_ai_output(text: str) -> Optional[dict]:
    """Parse AI output — tries JSON first, then [TAG] format."""
    if not text:
        return None

    # Try JSON parse
    try:
        # Strip markdown fences
        clean = re.sub(r'```json\s*', '', text)
        clean = re.sub(r'```\s*', '', clean).strip()
        # Find JSON object
        match = re.search(r'\{[^{}]*"title"[^{}]*"content"[^{}]*\}', clean, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if data.get("title") and data.get("content"):
                return {
                    "title": data["title"].strip(),
                    "content": data["content"].strip(),
                    "category": data.get("category", "Home").strip(),
                    "tags": data.get("tags", []),
                    "slug": data.get("slug", ""),
                }
    except (json.JSONDecodeError, AttributeError):
        pass

    # Try full text as JSON
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and data.get("title") and data.get("content"):
            return {
                "title": data["title"].strip(),
                "content": data["content"].strip(),
                "category": data.get("category", "Home").strip(),
                "tags": data.get("tags", []),
                "slug": data.get("slug", ""),
            }
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: [TAG] format
    title_m = re.search(r"\[TITLE\](.*?)\[/TITLE\]", text, re.DOTALL | re.IGNORECASE)
    content_m = re.search(r"\[CONTENT\](.*?)\[/CONTENT\]", text, re.DOTALL | re.IGNORECASE)
    cat_m = re.search(r"\[CATEGORY\](.*?)\[/CATEGORY\]", text, re.DOTALL | re.IGNORECASE)

    if title_m and content_m:
        t = title_m.group(1).strip().replace("<b>", "").replace("</b>", "")
        c = content_m.group(1).strip()
        if len(t) >= 5 and len(c) >= 20:
            return {
                "title": t,
                "content": c,
                "category": cat_m.group(1).strip() if cat_m else "Home",
                "tags": [],
                "slug": "",
            }

    return None


# ─────────────────────────────────────────────
# 4. QUALITY VALIDATION
# ─────────────────────────────────────────────

def is_sufficiently_rephrased(original: str, rephrased: str) -> bool:
    threshold = settings.AI_SIMILARITY_THRESHOLD
    orig_words = set(original.lower().split())
    reph_words = set(rephrased.lower().split())
    if orig_words and reph_words:
        word_sim = len(orig_words & reph_words) / max(len(orig_words), len(reph_words))
    else:
        word_sim = 0.0
    seq_sim = SequenceMatcher(None, original.lower()[:500], rephrased.lower()[:500]).ratio()
    combined = max(word_sim, seq_sim)
    if combined > threshold:
        logger.warning(f"[SIMILARITY] Rejected: word={word_sim:.2f}, seq={seq_sim:.2f} > {threshold}")
        return False
    return True


# ─────────────────────────────────────────────
# 5. SLUG & TAG GENERATION
# ─────────────────────────────────────────────

def generate_slug(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title.lower())
    return re.sub(r"[\s_-]+", "-", s).strip("-")[:120]


def generate_tags(title: str, content: str, category: str) -> List[str]:
    """Generate tags from title + content keywords."""
    text = f"{title} {content}".lower()
    text = re.sub(r'<[^>]+>', ' ', text)  # strip HTML
    words = re.findall(r'\b[a-z]{3,15}\b', text)
    # Count word frequency, exclude stop words
    stops = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was",
             "one", "our", "out", "has", "have", "had", "this", "that", "with", "from",
             "they", "been", "said", "will", "would", "could", "about", "which", "their",
             "also", "more", "than", "into", "over", "such", "after", "been", "other"}
    freq = {}
    for w in words:
        if w not in stops and len(w) > 3:
            freq[w] = freq.get(w, 0) + 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:7]
    tags = [w for w, _ in top]
    if category.lower() not in tags:
        tags.insert(0, category.lower())
    return tags[:8]


# ─────────────────────────────────────────────
# 6. AI SERVICE CLASS
# ─────────────────────────────────────────────

class AIService:
    def __init__(self):
        self._gemini = None
        self._gemini_secondary = None
        self._openai = None

    # ── Provider clients ──

    @property
    def gemini_client(self):
        if not self._gemini and settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"[GEMINI-PRIMARY] Init failed: {e}")
        return self._gemini

    @property
    def gemini_secondary_client(self):
        if not self._gemini_secondary and settings.GEMINI_API_KEY_SECONDARY:
            try:
                from google import genai
                self._gemini_secondary = genai.Client(api_key=settings.GEMINI_API_KEY_SECONDARY)
            except Exception as e:
                logger.warning(f"[GEMINI-SECONDARY] Init failed: {e}")
        return self._gemini_secondary

    @property
    def openai_client(self):
        if not self._openai and settings.OPENAI_API_KEY:
            try:
                import openai
                self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"[OPENAI] Init failed: {e}")
        return self._openai

    # ── Ollama (LOCAL FALLBACK) ──

    def _rephrase_ollama(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        import requests
        try:
            url = f"{settings.OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": "llama3.2:1b",
                "prompt": f"System: {SYSTEM_PROMPT}\n\nUser: {build_prompt(title, content, lang_name)}",
                "stream": False,
                "format": "json"
            }
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                result = parse_ai_output(data.get("response", ""))
                if result:
                    result["method"] = "ollama"
                    logger.info(f"[OLLAMA] ✓ Processed: {result['title'][:60]}...")
                return result
        except Exception as e:
            logger.warning(f"[OLLAMA] Failed: {e}")
        return None

    # ── Gemini (PRIMARY) ──

    def _rephrase_gemini(self, title: str, content: str, lang_name: str, use_secondary: bool = False) -> Optional[dict]:
        client = self.gemini_secondary_client if use_secondary else self.gemini_client
        tag = "GEMINI-SEC" if use_secondary else "GEMINI-PRI"
        
        if not client:
            return None
        try:
            from google.genai import types
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=build_prompt(title, content, lang_name),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                    max_output_tokens=2048,
                ),
            )
            result = parse_ai_output(resp.text)
            if result:
                result["method"] = tag.lower()
                logger.info(f"[{tag}] ✓ Processed: {result['title'][:60]}...")
            return result
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "rate" in err_str or "limit" in err_str:
                logger.warning(f"[{tag}] QUOTA EXCEEDED: {e}")
                raise  # Re-raise so rephrase_with_providers catches and falls through
            logger.warning(f"[{tag}] Failed: {e}")
            return None

    # ── OpenAI (FALLBACK) ──

    def _rephrase_openai(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        if not self.openai_client:
            return None
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(title, content, lang_name)},
                ],
                temperature=0.7,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            result = parse_ai_output(resp.choices[0].message.content)
            if result:
                result["method"] = "openai"
                logger.info(f"[OPENAI] ✓ Processed: {result['title'][:60]}...")
            return result
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "429" in err_str or "rate" in err_str or "limit" in err_str:
                logger.warning(f"[OPENAI] QUOTA EXCEEDED: {e}")
                raise
            logger.warning(f"[OPENAI] Failed: {e}")
        return None

    # ── Provider execution ──

    def rephrase_with_providers(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        """Sequential provider chain based on settings.AI_PROVIDER_CHAIN.
        
        Order: Defined by settings.AI_PROVIDER_CHAIN (default: ["gemini", "openai"])
        Local Rephrase (Fast/Regex) is the ultimate fallback if all AI providers fail.
        """
        chain = settings.AI_PROVIDER_CHAIN
        if not chain:
            chain = ["gemini", "openai"]  # Default fallback chain

        # Map chain names to functions
        provider_map = {
            "gemini": [
                ("GEMINI-PRIMARY", lambda: self._rephrase_gemini(title, content, lang_name, use_secondary=False)),
                ("GEMINI-SECONDARY", lambda: self._rephrase_gemini(title, content, lang_name, use_secondary=True)),
            ],
            "openai": [("OPENAI", lambda: self._rephrase_openai(title, content, lang_name))],
            "ollama": [("OLLAMA", lambda: self._rephrase_ollama(title, content, lang_name))],
        }

        # Build execution list based on chain
        to_execute = []
        for p_name in chain:
            p_name = p_name.lower()
            if p_name in provider_map:
                to_execute.extend(provider_map[p_name])

        for name, fn in to_execute:
            try:
                result = fn()
                if self._is_valid_ai_res(result, content):
                    # No need to override "method" here as it's set in the provider functions
                    logger.info(f"[AI-WINNER] {name}")
                    return result
                else:
                    logger.info(f"[AI] {name}: empty or invalid result, trying next")
            except Exception as e:
                err_str = str(e).lower()
                if any(x in err_str for x in ["quota", "rate", "429", "limit", "insufficient"]):
                    logger.warning(f"[AI] {name}: QUOTA/RATE LIMIT — falling through")
                else:
                    logger.warning(f"[AI] {name}: technical error ({e}) — trying next")
                continue

        logger.warning("[AI] All configured providers exhausted")
        return None



    def _is_valid_ai_res(self, res: Optional[dict], original_content: str) -> bool:
        if res and res.get("content") and len(res["content"]) > 50:
            return True
        return False

    # ── Fast Local Rephrase (no API) ──

    def fast_local_rephrase(self, title: str, content: str) -> Tuple[str, str]:
        """Instant local rephrasing — no AI API needed."""
        logger.info("[FAST-REPHRASE] Regex transformation")
        c_title = strip_sources(title).strip().capitalize()
        c_content = strip_sources(content).strip()
        c_content = re.sub(r'<[^>]+>', ' ', c_content) # Strip HTML
        c_content = re.sub(r'\s+', ' ', c_content).strip()

        if not c_content:
            return c_title, f"<p>{c_content or c_title}</p>"

        sentences = re.split(r'(?<=[.!?])\s+', c_content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if not sentences:
            return c_title, f"<p>{c_content}</p>"

        parts = [f"<p>{' '.join(sentences[:2])}</p>"]
        if len(sentences) > 2:
            parts.append("<p><b>Key Highlights:</b></p><ul>")
            for s in sentences[2:7]:
                parts.append(f"<li>{s}</li>")
            parts.append("</ul>")
        if len(sentences) > 7:
            parts.append(f"<p>{' '.join(sentences[7:12])}</p>")
        
        return c_title, "\n".join(parts)

    # ── Keyword categorization ──

    def _categorize_by_keywords(self, title: str, content: str) -> str:
        text_low = f"{title} {content}".lower()
        kw = {
            "Politics": ["election", "modi", "minister", "parliament", "congress", "government",
                         "political", "vote", "policy", "jagan", "chandrababu", "tdp", "ysrcp",
                         "bjp", "kcr", "legislation", "governor", "chief minister", "assembly"],
            "Events": ["match", "ipl", "cricket", "tournament", "championship", "sports",
                       "game", "football", "tennis", "olympic", "festival", "conference",
                       "celebration", "marathon", "kabaddi", "world cup"],
            "Entertainment": ["movie", "tollywood", "bollywood", "actor", "actress", "film",
                              "director", "box office", "ott", "netflix", "cinema", "trailer",
                              "music", "singer", "concert", "award", "celebrity", "gossip"],
            "Tech": ["ai", "chipset", "mobile", "software", "google", "apple", "startup",
                     "tech", "digital", "smartphone", "app", "artificial intelligence",
                     "machine learning", "robot", "cyber", "internet", "5g"],
            "Business": ["stock", "market", "economy", "revenue", "profit", "company",
                         "investment", "gdp", "inflation", "trade", "bank", "rbi",
                         "sensex", "nifty", "ipo", "merger", "acquisition"],
            "Health": ["hospital", "doctor", "disease", "covid", "vaccine", "medical",
                       "health", "treatment", "patient", "surgery", "drug", "pharma",
                       "cancer", "diabetes", "mental health", "fitness"],
            "Science": ["research", "study", "nasa", "space", "scientist", "discovery",
                        "climate", "physics", "biology", "isro", "satellite", "quantum"],
            "World": ["international", "global", "united nations", "foreign", "europe",
                      "china", "russia", "ukraine", "war", "nato", "summit", "diplomat",
                      "us president", "white house", "middle east", "pakistan"],
        }
        for cat, keywords in kw.items():
            if any(k in text_low for k in keywords):
                return category_service.normalize(cat)
        return "Home"

    # ─────────────────────────────────────────────
    # MASTER PIPELINE
    # ─────────────────────────────────────────────

    def process_article(self, title: str, content: str, **kwargs) -> Dict:
        """Full article processing pipeline.

        1. Detect language
        2. Try AI rephrase (Gemini → OpenAI)
        3. Fall back to fast local rephrase
        4. Categorize + tag + slug
        """
        t1 = time.time()

        # 1. Detect language
        try:
            lang_code = detect(f"{title} {(content or '')[:200]}")
        except Exception:
            lang_code = "en"

        lang_map = {"te": "Telugu", "en": "English", "hi": "Hindi", "ta": "Tamil", "kn": "Kannada"}
        lang_name = lang_map.get(lang_code, "English")

        # 2. AI Rephrase (Gemini primary → OpenAI fallback)
        method = "none"
        r_title = r_content = r_cat = None
        tags = []
        slug = ""

        try:
            ai_res = self.rephrase_with_providers(title, content or "", lang_name)
            if ai_res and ai_res.get("content"):
                r_title = ai_res["title"]
                r_content = ai_res["content"]
                # Validate category from AI using central service
                r_cat = category_service.normalize(ai_res.get("category", "Home"))
                tags = ai_res.get("tags", [])
                slug = ai_res.get("slug", "")
                method = ai_res.get("method", "ai")
        except Exception as e:
            logger.warning(f"[AI] All providers failed: {e}")

        # 3. Fallback to fast local rephrase (Force this only if All AI fails)
        if not r_content:
            logger.warning(f"[PIPELINE] Fallback to LOCAL processing for: {title[:50]}...")
            r_title, r_content = self.fast_local_rephrase(title, content or "")
            r_cat = self._categorize_by_keywords(title, content or "")
            method = "local"

        # 4. Generate tags and slug if not from AI
        if not tags:
            tags = generate_tags(r_title or title, content or "", r_cat or "Home")
        if not slug:
            slug = generate_slug(r_title or title)

        duration = round(time.time() - t1, 2)
        logger.info(f"[PIPELINE] {lang_code} | cat={r_cat} | {duration}s | method={method}")

        return {
            "original_language": lang_code,
            "translated_title": title,
            "translated_content": content or "",
            "rephrased_title": r_title or title,
            "rephrased_content": r_content or content or "",
            "slug": slug,
            "category": r_cat or "Home",
            "category_confidence": 0.85 if method != "local" else 0.4,
            "tags": tags,
            "method": method,
            "processed_at": datetime.now().isoformat(),
        }


# Module-level singleton
ai_service = AIService()
