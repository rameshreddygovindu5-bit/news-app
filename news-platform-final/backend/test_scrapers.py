#!/usr/bin/env python
"""
Test script to verify all web scrapers are working correctly.
"""
import asyncio
import logging
import sys
from datetime import datetime
from app.scrapers.base_scraper import ScraperFactory

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    'scraper_config': {
        'max_articles': 5,  # Limit to 5 articles for quick testing
        'request_delay': 1.0,  # 1 second delay between requests
        'max_retries': 2,
        'fetch_full_content': False,  # Don't fetch full content for testing
        'sequential_mode': True  # Use sequential mode to avoid blocking
    }
}

# List of scrapers to test
SCRAPERS_TO_TEST = [
    ('tv9 telugu', 'te'),
    ('sakshi', 'te'),
    ('eenadu', 'te'),
    ('telugutimes telugu', 'te'),
    ('telugutimes english', 'en'),
    ('telugu123', 'te'),
    ('prabhanews', 'te'),
    ('oneindia telugu', 'te'),
    ('oneindia english', 'en'),
    ('greatandhra', 'te'),
    ('aljazeera', 'en'),
    ('times of india', 'en')
]

async def test_scraper(name: str, language: str):
    """Test a single scraper."""
    print(f"\n{'='*60}")
    print(f"Testing {name} ({language})")
    print(f"{'='*60}")
    
    try:
        # Create scraper instance
        config = {
            'name': name,
            'language': language,
            **TEST_CONFIG
        }
        
        scraper = ScraperFactory.create(config)
        
        # Run scraper
        start_time = datetime.now()
        articles = await scraper.scrape()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # Report results
        print(f"Scraped {len(articles)} articles in {duration:.2f} seconds")
        
        if articles:
            # Show first article details
            first = articles[0]
            print(f"\nFirst article:")
            print(f"  Title: {first.title[:100]}...")
            print(f"  URL: {first.url}")
            print(f"  Published: {first.published_at}")
            print(f"  Content length: {len(first.content)} chars")
            print(f"  Has image: {'Yes' if first.image_url else 'No'}")
            
            # Validate articles
            valid_count = sum(1 for a in articles if a.is_valid())
            print(f"\nValid articles: {valid_count}/{len(articles)}")
            
            return len(articles) > 0
        else:
            print("No articles scraped")
            return False
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Test all scrapers."""
    print("Starting web scraper tests...")
    print(f"Testing {len(SCRAPERS_TO_TEST)} scrapers\n")
    
    results = {}
    
    for name, language in SCRAPERS_TO_TEST:
        try:
            success = await test_scraper(name, language)
            results[name] = success
        except Exception as e:
            print(f"CRITICAL ERROR testing {name}: {e}")
            results[name] = False
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    total = len(results)
    working = sum(results.values())
    failed = total - working
    
    print(f"Total scrapers tested: {total}")
    print(f"Working: {working}")
    print(f"Failed: {failed}")
    
    print("\nDetailed results:")
    for name, success in results.items():
        status = "WORKING" if success else "FAILED"
        print(f"  {name}: {status}")
    
    # Return exit code based on results
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
