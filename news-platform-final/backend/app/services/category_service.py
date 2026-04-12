from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Canonical categories linked to the Database
CANONICAL_CATEGORIES = [
    "Home", "World", "Politics", "Business", "Tech", 
    "Health", "Science", "Entertainment", "Events"
]

# Mapping from various AI/Scraper variations to Canonical
CATEGORY_MAP = {
    "technology": "Tech",
    "science & technology": "Tech",
    "it": "Tech",
    "international": "World",
    "global": "World",
    "foreign": "World",
    "government": "Politics",
    "elections": "Politics",
    "finance": "Business",
    "economy": "Business",
    "movies": "Entertainment",
    "film": "Entertainment",
    "culture": "Entertainment",
    "sports": "Events",
    "cricket": "Events",
    "festivals": "Events",
    "lifestyle": "Home",
    "general": "Home",
    "breaking": "Home",
    "education": "Home",
    "national": "Home",
    "crime": "Home",
}

class CategoryService:
    @staticmethod
    def normalize(cat: str) -> str:
        if not cat:
            return "Home"
        
        c = cat.strip().lower()
        
        # Check canonical first (case-insensitive)
        for canon in CANONICAL_CATEGORIES:
            if canon.lower() == c:
                return canon
        
        # Check map
        if c in CATEGORY_MAP:
            return CATEGORY_MAP[c]
        
        # Partial match
        for key, val in CATEGORY_MAP.items():
            if key in c or c in key:
                return val
        
        return "Home"

    @staticmethod
    def get_all() -> List[str]:
        return CANONICAL_CATEGORIES

category_service = CategoryService()
