"""
YouTube Transcript Service — Fetch captions, translate, rephrase.

Uses youtube-transcript-api v1.x (new API: instance-based, .fetch() method).
"""

import re
import logging
from typing import Dict, Optional
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def fetch_transcript(video_id: str) -> Dict:
    """Fetch YouTube transcript using v1.x API (instance-based)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {"error": "youtube-transcript-api not installed", "text": "", "language": ""}

    api = YouTubeTranscriptApi()

    # Try languages in priority order
    for langs in [('en',), ('te',), ('hi',), ('en', 'te', 'hi')]:
        try:
            transcript = api.fetch(video_id, languages=langs)
            snippets = list(transcript)
            if snippets:
                full_text = " ".join(s.text for s in snippets)
                full_text = re.sub(r'\[.*?\]', '', full_text)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                return {
                    "text": full_text,
                    "language": langs[0] if len(langs) == 1 else "en",
                    "segments": len(snippets),
                    "error": None,
                }
        except Exception:
            continue

    # Last resort — try any available transcript
    try:
        transcript_list = api.list(video_id)
        for t in transcript_list:
            try:
                transcript = t.fetch()
                snippets = list(transcript)
                full_text = " ".join(s.text for s in snippets)
                full_text = re.sub(r'\[.*?\]', '', full_text)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                return {
                    "text": full_text,
                    "language": t.language_code,
                    "segments": len(snippets),
                    "error": None,
                }
            except Exception:
                continue
    except Exception as e:
        return {"text": "", "language": "", "segments": 0, "error": str(e)}

    return {"text": "", "language": "", "segments": 0, "error": "No transcript available"}


def translate_text(text: str, source_lang: str, target_lang: str = "en") -> str:
    if source_lang == target_lang:
        return text
    try:
        from deep_translator import GoogleTranslator
        chunks = [text[i:i+4500] for i in range(0, len(text), 4500)]
        return " ".join(GoogleTranslator(source=source_lang, target=target_lang).translate(c) for c in chunks)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text


def process_youtube_video(url: str) -> Dict:
    """Full pipeline: extract ID → fetch transcript → translate → rephrase."""
    video_id = extract_video_id(url)
    if not video_id:
        return {"error": "Invalid YouTube URL", "video_id": None}

    result = fetch_transcript(video_id)
    if result.get("error") and not result.get("text"):
        return {"error": f"Could not fetch transcript: {result['error']}", "video_id": video_id}

    raw_text = result["text"]
    detected_lang = result["language"]

    # Translate if needed
    translated_text = translate_text(raw_text, detected_lang, "en") if detected_lang != "en" else raw_text

    # AI rephrase
    ai_result = ai_service.process_article(
        title=translated_text[:200],
        content=translated_text,
    )

    return {
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "raw_transcript": raw_text,
        "transcript_language": detected_lang,
        "translated_text": translated_text,
        "rephrased_title": ai_result.get("rephrased_title", ""),
        "rephrased_content": ai_result.get("rephrased_content", ""),
        "telugu_title": ai_result.get("telugu_title", ""),
        "telugu_content": ai_result.get("telugu_content", ""),
        "category": ai_result.get("category", "Home"),
        "detected_language": ai_result.get("original_language", "en"),
        "error": None,
    }
