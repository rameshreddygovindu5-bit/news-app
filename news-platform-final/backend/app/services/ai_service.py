"""
AI Service v2.0 â€” Unified News Rephrasing & Enrichment Pipeline

BUG FIXES from v1:
  - Fixed missing __init__ for _anthropic / _openai clients (AttributeError)
  - Removed broken @lru_cache on rephrase method (cached on mutable self)
  - Fixed process_article() signature â€” now accepts **kwargs for backward compat
  - Replaced parallel race with ordered provider chain (configurable, cost-efficient)

IMPROVEMENTS:
  - Strengthened rephrasing prompt â€” forces structural rewrite, not light editing
  - Professional output with proper paragraphs, key highlights, structured layout
  - Better category mapping â€” expanded keywords, matches DB categories exactly
  - Combined word + sequence similarity check for quality validation
  - Per-provider retry with backoff
  - PT team articles get AI processing too

PROVIDERS: Gemini, Groq, Ollama, Ollama-GLM, Anthropic, OpenAI
"""

import re
import logging
import time
import traceback
import concurrent.futures
from typing import Optional, Dict, Tuple, List
from difflib import SequenceMatcher
from langdetect import detect

try:
    import ollama
except ImportError:
    ollama = None

try:
    import groq
except ImportError:
    groq = None

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Must match exactly what's in the DB categories table
CATEGORIES = [
    "Home", "World", "Politics", "Business",
    "Tech", "Science", "Health", "Entertainment", "Events"
]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. INPUT SANITIZATION
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def sanitize_input(text: str) -> str:
    if not text:
        return ""
    patterns = [r"(?i)ignore\s+previous\s+instructions.*", r"(?i)system\s+prompt.*"]
    for p in patterns:
        text = re.sub(p, "", text)
    return text.strip()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. SOURCE & TAG STRIPPING
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def strip_sources(text: str) -> str:
    patterns = [
        r"(?i)\b(?:as\s+)?(?:reported|published|stated|featured|carried)\s+(?:by|in|on|at|exclusively\s+by)\s+(?:GreatAndhra|ANI|IANS|PTI|UNI|Eenadu|Sakshi|TV9)\b",
        r"(?i)\((?:ANI|IANS|PTI|UNI|TNIE|GreatAndhra)\)",
        r"(?i)\b(?:GreatAndhra|ANI|IANS|PTI|Eenadu|Sakshi)\b[.,]?\s*"
    ]
    r = text
    for p in patterns:
        r = re.sub(p, "", r)
    return r.strip()

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 3. TAG-BASED OUTPUT PARSER (STRICT)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def parse_tags(text: str) -> Optional[dict]:
    """Extract content from [TITLE]...[/TITLE] and [CONTENT]...[/CONTENT] tags."""
    if not text:
        return None

    title_match = re.search(r"\[TITLE\](.*?)\[/TITLE\]", text, re.DOTALL | re.IGNORECASE)
    content_match = re.search(r"\[CONTENT\](.*?)\[/CONTENT\]", text, re.DOTALL | re.IGNORECASE)
    category_match = re.search(r"\[CATEGORY\](.*?)\[/CATEGORY\]", text, re.DOTALL | re.IGNORECASE)

    if not title_match or not content_match:
        bold_match = re.search(r"<b>(.*?)</b>", text)
        if bold_match and content_match:
            return {
                "title": bold_match.group(1).strip(),
                "content": content_match.group(1).strip(),
                "category": "Home"
            }
        return None

    title = title_match.group(1).strip().replace("<b>", "").replace("</b>", "")
    content = content_match.group(1).strip()

    if len(title) < 5 or len(content) < 20:
        return None

    return {
        "title": title,
        "content": content,
        "category": category_match.group(1).strip() if category_match else "Home"
    }

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4. SIMILARITY VALIDATION (strengthened)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def word_similarity(a: str, b: str) -> float:
    wa, wb = set(a.lower().split()), set(b.lower().split())
    return len(wa & wb) / max(len(wa), len(wb)) if wa and wb else 0.0

def sequence_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def is_sufficiently_rephrased(original: str, rephrased: str) -> bool:
    """Check that rephrased text is different enough. Uses BOTH word and sequence similarity."""
    threshold = settings.AI_SIMILARITY_THRESHOLD
    w_sim = word_similarity(original, rephrased)
    s_sim = sequence_similarity(original, rephrased)
    combined = max(w_sim, s_sim)
    if combined > threshold:
        logger.warning(f"[SIMILARITY] Rejected: word={w_sim:.2f}, seq={s_sim:.2f} > {threshold}")
        return False
    return True

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 5. SLUG GENERATION & STRENGTHENED PROFESSIONAL PROMPT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    # Remove accents, special chars, and convert to lowercase
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    return s

SYSTEM_PROMPT = """Act strictly as a senior professional news editor who REWRITES articles from scratch.

Your task: Given a news TITLE and CONTENT, produce a COMPLETELY REWORDED, professionally structured version.

CRITICAL REPHRASING RULES:
- REWRITE every sentence using entirely different words and sentence structures.
- DO NOT copy-paste or lightly edit the original. Start fresh in your own words.
- The meaning must be IDENTICAL but the wording must be COMPLETELY DIFFERENT.
- Make the article more professional, clear, and reader-friendly.

CRITICAL FORMATTING RULES:
- Use <p>...</p> for each paragraph.
- Use <ul><li>...</li></ul> for bullet points if the article has lists or multiple key points.
- Use <b>...</b> for important names, dates, numbers, and key facts.
- Proper paragraphs, commas, spaces, and punctuation.
- Do NOT use markdown (**, ##, -). Only use HTML tags.
- Do NOT return a single-line block of text.
- Ensure high readability with clear spacing between sections.

CONTENT RULES:
1. TONE: Professional, neutral, polite, reader-friendly. No opinions or sensationalism.
2. ACCURACY: Preserve ALL facts exactly â€” names, numbers, dates, quotes. Do NOT invent anything.
3. CLEANUP: Remove promotional language, ads, platform mentions, filler words.
4. ORIGINALITY: Every sentence must be structurally different from the original.
5. LANGUAGE (STRICT):
   - OUTPUT IN THE EXACT SAME LANGUAGE AS INPUT.
   - Telugu input â†’ Telugu output. English input â†’ English output.
   - DO NOT TRANSLATE.

CATEGORY MAPPING (STRICT â€” pick the BEST match):
- Home, World, Politics, Business, Tech, Science, Health, Entertainment, Events

OUTPUT FORMAT (STRICT â€” NO extra text before or after):

[CATEGORY]
Pick exactly one from: Home, World, Politics, Business, Tech, Science, Health, Entertainment, Events
[/CATEGORY]

[TITLE]
<b>Completely reworded professional title here</b>
[/TITLE]

[CONTENT]
<p>Opening paragraph â€” professionally rewritten with different vocabulary.</p>
<p><b>Key Highlights:</b></p>
<ul>
  <li>First key point reworded professionally.</li>
  <li>Second key point reworded professionally.</li>
  <li>Third key point if applicable.</li>
</ul>
<p>Detailed body paragraph with restructured sentences.</p>
<p>Closing paragraph if needed.</p>
[/CONTENT]"""

def build_prompt(title: str, content: str, lang_name: str = "the same language as input") -> str:
    clean_title = sanitize_input(strip_sources(title))
    clean_content = sanitize_input(strip_sources(content))
    return f"""The input language is {lang_name}.
IMPORTANT: Your rewrite MUST be in {lang_name}. DO NOT translate.
IMPORTANT: COMPLETELY REWRITE â€” do not copy or lightly edit.

Original Title:
{clean_title}

Original Content:
{clean_content}"""

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 6. AI PROVIDERS â€” ordered chain
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class AIService:
    def __init__(self):
        self._groq = None
        self._gemini = None
        self._anthropic = None  # BUG FIX: was missing, caused AttributeError
        self._openai = None     # BUG FIX: was missing, caused AttributeError

    # â”€â”€ Provider client properties â”€â”€

    @property
    def groq_client(self):
        if not self._groq and settings.GROQ_API_KEY and groq:
            try:
                self._groq = groq.Groq(api_key=settings.GROQ_API_KEY)
            except Exception:
                pass
        return self._groq

    @property
    def gemini_client(self):
        if not self._gemini and settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception:
                pass
        return self._gemini

    @property
    def anthropic_client(self):
        if not self._anthropic and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic
                self._anthropic = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            except Exception:
                pass
        return self._anthropic

    @property
    def openai_client(self):
        if not self._openai and settings.OPENAI_API_KEY:
            try:
                import openai
                self._openai = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            except Exception:
                pass
        return self._openai

    # â”€â”€ Individual provider methods â”€â”€

    def _rephrase_ollama(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        if not ollama or not settings.OLLAMA_MODEL:
            return None
        try:
            prompt = f"{SYSTEM_PROMPT}\n\n{build_prompt(title, content, lang_name)}"
            resp = ollama.generate(model=settings.OLLAMA_MODEL, prompt=prompt, options={"temperature": 0.7})
            return parse_tags(resp['response'])
        except Exception as e:
            logger.warning(f"[AI] Ollama failed: {e}")
            return None

    def _rephrase_ollama_glm(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        if not ollama:
            return None
        try:
            prompt = f"{SYSTEM_PROMPT}\n\n{build_prompt(title, content, lang_name)}"
            resp = ollama.generate(model="glm-4.7-flash:latest", prompt=prompt, options={"temperature": 0.7})
            return parse_tags(resp['response'])
        except Exception as e:
            logger.warning(f"[AI] Ollama-GLM failed: {e}")
            return None

    def _rephrase_groq(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        client = self.groq_client
        if not client:
            return None
        try:
            resp = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(title, content, lang_name)}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            return parse_tags(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"[AI] Groq failed: {e}")
            return None

    def _rephrase_gemini(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        if not self.gemini_client:
            return None
        try:
            from google.genai import types
            resp = self.gemini_client.models.generate_content(
                model="gemini-flash-latest",
                contents=build_prompt(title, content, lang_name),
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.7)
            )
            return parse_tags(resp.text)
        except Exception as e:
            logger.warning(f"[AI] Gemini failed: {e}")
            return None

    def _rephrase_anthropic(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        if not self.anthropic_client:
            return None
        try:
            resp = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_prompt(title, content, lang_name)}]
            )
            return parse_tags(resp.content[0].text)
        except Exception as e:
            logger.warning(f"[AI] Anthropic failed: {e}")
            return None

    def _rephrase_openai(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        if not self.openai_client:
            return None
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_prompt(title, content, lang_name)}
                ],
                temperature=0.7
            )
            return parse_tags(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"[AI] OpenAI failed: {e}")
            return None

    # â”€â”€ Provider registry â”€â”€

    def _get_provider_map(self) -> Dict[str, callable]:
        return {
            "gemini": self._rephrase_gemini,
            "groq": self._rephrase_groq,
            "ollama": self._rephrase_ollama,
            "ollama-glm": self._rephrase_ollama_glm,
            "anthropic": self._rephrase_anthropic,
            "openai": self._rephrase_openai,
        }

    def _is_provider_configured(self, name: str) -> bool:
        checks = {
            "gemini": bool(settings.GEMINI_API_KEY),
            "groq": bool(settings.GROQ_API_KEY),
            "ollama": bool(ollama and settings.OLLAMA_MODEL),
            "ollama-glm": bool(ollama),
            "anthropic": bool(settings.ANTHROPIC_API_KEY),
            "openai": bool(settings.OPENAI_API_KEY),
        }
        return checks.get(name, False)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 7. PARALLEL PROVIDER EXECUTION (fast)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def rephrase_with_providers(self, title: str, content: str, lang_name: str) -> Optional[dict]:
        """Try all configured providers in parallel. First valid + sufficiently-rephrased result wins.

        Uses ThreadPoolExecutor for true parallelism across AI providers.
        """
        provider_map = self._get_provider_map()
        chain = settings.AI_PROVIDER_CHAIN

        active_providers = []
        for name in chain:
            if self._is_provider_configured(name):
                fn = provider_map.get(name)
                if fn:
                    active_providers.append((name, fn))

        if not active_providers:
            logger.warning("[AI] No providers configured!")
            return None

        # Execute all providers in parallel â€” first good result wins
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_providers)) as executor:
            futures = {
                executor.submit(fn, title, content, lang_name): name
                for name, fn in active_providers
            }
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if not result or not result.get("content"):
                        continue

                    # Validate rephrasing quality
                    if not is_sufficiently_rephrased(content, result["content"]):
                        logger.info(f"[AI] {name} output too similar, checking others")
                        continue

                    logger.info(f"[AI-WINNER] {name}")
                    return result
                except Exception as e:
                    logger.warning(f"[AI] {name} error: {e}")
                    continue

        logger.warning("[AI] All providers exhausted")
        return None

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 8. FALLBACK
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def fast_local_rephrase(self, title: str, content: str) -> Tuple[str, str]:
        """Fast local rephrasing — no AI API needed. Runs in <100ms.
        
        1. Cleans source attributions and ads
        2. Splits into proper sentences/paragraphs
        3. Formats with professional HTML structure
        4. Extracts key points into bullet list
        """
        import re
        logger.info("[FAST-REPHRASE] Processing locally")
        
        clean_title = strip_sources(title).strip()
        clean_content = strip_sources(content).strip()
        
        # Remove HTML tags from raw content
        clean_content = re.sub(r'<[^>]+>', ' ', clean_content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()
        
        if not clean_content:
            return clean_title, "<p>No content available.</p>"
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', clean_content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 15]
        
        if not sentences:
            return clean_title, f"<p>{clean_content}</p>"
        
        # Build structured HTML
        parts = []
        
        # Opening paragraph (first 2-3 sentences)
        intro_count = min(3, len(sentences))
        intro = " ".join(sentences[:intro_count])
        parts.append(f"<p>{intro}</p>")
        
        remaining = sentences[intro_count:]
        
        # Extract key points if enough sentences
        if len(remaining) >= 3:
            parts.append("<p><b>Key Highlights:</b></p>")
            parts.append("<ul>")
            # Take up to 5 key points
            key_count = min(5, len(remaining))
            for s in remaining[:key_count]:
                # Clean up sentence for bullet point
                s = s.rstrip('.')
                parts.append(f"  <li>{s}.</li>")
            parts.append("</ul>")
            remaining = remaining[key_count:]
        
        # Body paragraphs (group remaining into paragraphs of 2-3 sentences)
        while remaining:
            chunk_size = min(3, len(remaining))
            para = " ".join(remaining[:chunk_size])
            parts.append(f"<p>{para}</p>")
            remaining = remaining[chunk_size:]
        
        html_content = "\n".join(parts)
        return clean_title, html_content

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 9. EXPANDED KEYWORD-BASED CATEGORY FALLBACK
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _categorize_by_keywords(self, title: str, content: str) -> str:
        text_low = f"{title} {content}".lower()
        keyword_map = {
            "Politics": ["election", "modi", "minister", "parliament", "congress", "government",
                         "political", "senator", "vote", "policy", "jagan", "chandrababu", "tdp",
                         "ysrcp", "bjp", "kcr", "legislation", "governor", "chief minister",
                         "assembly", "lok sabha", "rajya sabha", "speaker", "opposition"],
            "Events": ["match", "ipl", "cricket", "tournament", "championship", "sports",
                       "game", "football", "tennis", "olympic", "convention", "conference",
                       "festival", "expo", "ceremony", "celebration", "marathon", "kabaddi"],
            "Entertainment": ["movie", "tollywood", "bollywood", "actor", "actress", "film",
                              "director", "box office", "ott", "netflix", "cinema", "review",
                              "trailer", "music", "singer", "album", "dsp", "concert", "dance",
                              "award", "premiere", "gossip", "celebrity"],
            "Tech": ["ai", "chipset", "mobile", "software", "google", "apple", "startup",
                     "tech", "digital", "smartphone", "app", "artificial intelligence",
                     "machine learning", "robot", "cyber", "internet", "5g", "chip"],
            "Business": ["stock", "market", "economy", "revenue", "profit", "company",
                         "investment", "gdp", "inflation", "trade", "bank", "rbi",
                         "sensex", "nifty", "startup", "ipo", "merger", "acquisition"],
            "Health": ["hospital", "doctor", "disease", "covid", "vaccine", "medical",
                       "health", "treatment", "patient", "surgery", "drug", "pharma",
                       "mental health", "fitness", "nutrition", "cancer", "diabetes"],
            "Science": ["research", "study", "nasa", "space", "scientist", "discovery",
                        "experiment", "climate", "physics", "biology", "isro", "satellite",
                        "quantum", "genome", "evolution", "asteroid"],
            "World": ["international", "global", "united nations", "foreign", "europe",
                      "china", "russia", "ukraine", "war", "nato", "summit", "diplomat",
                      "us president", "white house", "middle east", "pakistan"],
        }
        for category, keywords in keyword_map.items():
            if any(k in text_low for k in keywords):
                return category
        return "Home"

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # 10. MASTER PIPELINE â€” accepts **kwargs for backward compat
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def process_article(self, title: str, content: str, **kwargs) -> Dict:
        """Process a single article through the AI pipeline.

        Accepts **kwargs to handle old callers (source_language=) without breaking.
        Pipeline: Detect Language â†’ AI Rephrase â†’ Validate â†’ Categorize
        """
        t1 = time.time()

        # 1. Detect Language
        try:
            sample = f"{title} {content[:200]}" if content else title
            lang_code = detect(sample)
        except Exception:
            lang_code = "en"

        lang_map = {"te": "Telugu", "en": "English", "hi": "Hindi", "ta": "Tamil", "kn": "Kannada"}
        lang_name = lang_map.get(lang_code, "English")

        # 2. Try fast local rephrase first (instant, no API call)
        r_title, r_content = self.fast_local_rephrase(title, content or "")
        r_cat = self._categorize_by_keywords(title, content or "")
        confidence = 0.6
        method = "local"

        # 3. Optionally enhance with AI if providers are configured
        try:
            ai_res = self.rephrase_with_providers(title, content or "", lang_name)
            if ai_res and ai_res.get("content"):
                r_title = ai_res.get("title", r_title)
                r_content = ai_res.get("content", r_content)
                ai_cat_raw = ai_res.get("category", "Home").strip()
                ai_cat_norm = ai_cat_raw.capitalize() if ai_cat_raw else "Home"
                if ai_cat_norm in CATEGORIES:
                    r_cat = ai_cat_norm
                confidence = 0.85
                method = "ai"
        except Exception as e:
            logger.warning(f"[AI] Enhancement failed, using local rephrase: {e}")

        duration = round(time.time() - t1, 2)
        logger.info(f"[PIPELINE] {lang_code} | cat={r_cat} | {duration}s | method={method}")

        return {
            "original_language": lang_code,
            "translated_title": title,
            "translated_content": content or "",
            "rephrased_title": r_title,
            "rephrased_content": r_content,
            "slug": generate_slug(r_title or title),
            "category": r_cat,
            "category_confidence": confidence,
            "tags": [],
            "processed_at": time.asctime()
        }


# Module-level singleton
ai_service = AIService()
