"""
WhatsApp Assistant - Facebook Scraper
=====================================
Scrapes buy/sell groups from Facebook and extracts structured listings.

Usage:
    python -m scraper.main --group-id 774703760229907
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from scraper.facebook import FacebookScraper
from scraper.parser import ListingParser
from scraper.storage import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Scrape Facebook buy/sell groups'
    )
    parser.add_argument(
        '--group-id',
        type=str,
        default='774703760229907',
        help='Facebook Group ID to scrape (default: 774703760229907)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        default=True,
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--max-posts',
        type=int,
        default=200,
        help='Maximum number of posts to scrape (default: 200)'
    )
    parser.add_argument(
        '--max-scrolls',
        type=int,
        default=30,
        help='Maximum scroll attempts (default: 30)'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default='./data/listings.db',
        help='Path to SQLite database'
    )
    return parser.parse_args()


def main():
    """Main entry point for the scraper."""
    args = parse_args()
    
    logger.info("🚀 Starting Facebook Scraper")
    logger.info(f"   Group ID: {args.group_id}")
    logger.info(f"   Max posts: {args.max_posts}")
    logger.info(f"   Headless: {args.headless}")
    
    # Ensure database directory exists
    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize components
    db = Database(str(db_path))
    scraper = FacebookScraper(headless=args.headless)
    parser = ListingParser()
    
    try:
        # Login to Facebook
        logger.info("📱 Logging into Facebook...")
        if not scraper.login():
            logger.error("❌ Login failed")
            sys.exit(1)
        logger.info("✅ Logged in successfully")
        
        # Scrape group
        logger.info(f"🔍 Scraping group {args.group_id}...")
        posts = scraper.scrape_group(
            group_id=args.group_id,
            max_posts=args.max_posts
        )
        logger.info(f"📝 Found {len(posts)} posts")
        
        # Parse and store listings
        saved_count = 0
        for post in posts:
            # Parse the post
            listing = parser.parse(post)
            
            if listing:
                # Store in database
                db.save_listing(listing)
                saved_count += 1
                
                logger.info(
                    f"   ✅ [{listing['type']}] {listing['article']} "
                    f"- {listing.get('price', 'N/A')} {listing.get('currency', '')}"
                )
            else:
                logger.debug(f"   ⏭️  Skipped non-marketplace post")
        
        logger.info(f"\n🎉 Done! Saved {saved_count} listings to database")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
        
    finally:
        scraper.close()
        db.close()


if __name__ == '__main__':
    main()
