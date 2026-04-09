from app.scrapers.base_scraper import ScraperFactory, BaseScraper, RSSScaper, HTMLScraper, ScrapedArticle
from app.scrapers.content_extractor import extract_article

# Each import triggers ScraperFactory.register()
from app.scrapers.greatandhra_scraper import GreatAndhraScraper
from app.scrapers.eenadu_scraper import EenaduScraper
from app.scrapers.sakshi_scraper import SakshiScraper
from app.scrapers.tv9_scraper import TV9TeluguScraper
from app.scrapers.prabhanews_scraper import PrabhaNewsScraper
from app.scrapers.telugu123_scraper import Telugu123Scraper
from app.scrapers.telugutimes_scraper import TeluguTimesScraper
from app.scrapers.oneindia_scraper import OneIndiaScraper
from app.scrapers.aljazeera_scraper import AlJazeeraScraper
