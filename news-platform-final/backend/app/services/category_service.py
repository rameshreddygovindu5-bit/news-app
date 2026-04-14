"""
Category Service — Single source of truth for category normalization.
CANONICAL_CATEGORIES must stay in sync with config.py and frontend CATS.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

CANONICAL_CATEGORIES: List[str] = [
    "Home", "World", "Politics", "Business", "Tech",
    "Health", "Science", "Entertainment", "Events", "Sports",
    "Surveys", "Polls",
]

CATEGORY_MAP: Dict[str, str] = {
    # Tech
    "technology": "Tech", "it": "Tech", "ai": "Tech", "gadgets": "Tech",
    "sci-tech": "Tech", "innovation": "Tech", "digital": "Tech",
    # World
    "international": "World", "global": "World", "foreign": "World", "world news": "World",
    # Politics
    "government": "Politics", "elections": "Politics", "election": "Politics",
    "policy": "Politics", "political": "Politics", "andhra-news": "Politics",
    "telangana-news": "Politics", "india-news": "Politics", "national": "Politics",
    # Business
    "finance": "Business", "economy": "Business", "market": "Business",
    "markets": "Business", "stocks": "Business", "investment": "Business",
    "trade": "Business", "economic": "Business", "money": "Business",
    # Entertainment
    "movies": "Entertainment", "movie": "Entertainment", "film": "Entertainment",
    "bollywood": "Entertainment", "tollywood": "Entertainment", "hollywood": "Entertainment",
    "television": "Entertainment", "tv": "Entertainment", "music": "Entertainment",
    "celebrity": "Entertainment", "gossip": "Entertainment", "culture": "Entertainment",
    "arts": "Entertainment", "lifestyle": "Entertainment", "fashion": "Entertainment",
    "style": "Entertainment", "reviews": "Entertainment",
    # Health
    "medical": "Health", "medicine": "Health", "wellness": "Health",
    "fitness": "Health", "covid": "Health", "disease": "Health", "healthcare": "Health",
    # Science
    "research": "Science", "space": "Science", "nature": "Science",
    "environment": "Science", "climate": "Science", "ecology": "Science",
    # Sports
    "sports": "Sports", "sport": "Sports", "cricket": "Sports", "football": "Sports",
    "soccer": "Sports", "tennis": "Sports", "basketball": "Sports",
    "kabaddi": "Sports", "ipl": "Sports",
    # Events
    "events": "Events", "festivals": "Events", "festival": "Events", "event": "Events",
    # Surveys
    "surveys": "Surveys", "survey": "Surveys", "results": "Surveys",
    # Polls
    "polls": "Polls", "poll": "Polls", "voting": "Polls",
    # Home
    "general": "Home", "breaking": "Home", "latest": "Home", "news": "Home",
    "education": "Home", "crime": "Home", "local": "Home",
    "opinion": "Home", "analysis": "Home", "other": "Home",
}


class CategoryService:
    @staticmethod
    def normalize(cat: str) -> str:
        if not cat: return "Home"
        c = cat.strip().lower()
        for canon in CANONICAL_CATEGORIES:
            if canon.lower() == c: return canon
        if c in CATEGORY_MAP: return CATEGORY_MAP[c]
        for key, val in CATEGORY_MAP.items():
            if key in c or c in key: return val
        return "Home"

    @staticmethod
    def get_all() -> List[str]: return list(CANONICAL_CATEGORIES)
    @staticmethod
    def is_valid(cat: str) -> bool: return cat in CANONICAL_CATEGORIES


category_service = CategoryService()
