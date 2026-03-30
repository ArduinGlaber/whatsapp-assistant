"""
WhatsApp Assistant - Facebook Scraper
=====================================
Scrapes buy/sell groups from Facebook and extracts structured listings. 

Usage:
    python -m scraper.main --group-id 774703760229907
    python -m scraper.main --upload  # Solo sube la DB a GitHub
"""

import argparse
import logging
import os
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


def upload_to_github(db_path: str) -> bool:
    """Upload database to GitHub Release using GitHub CLI or curl."""
    import subprocess
    
    logger.info("📤 Subiendo base de datos a GitHub...")
    
    # Check if gh CLI is available
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True)
        has_gh = result.returncode == 0
    except FileNotFoundError:
        has_gh = False
    
    if has_gh:
        # Use gh CLI
        try:
            # Get release by tag
            result = subprocess.run([
                'gh', 'release', 'view', 'v1.0.0',
                '--json', 'id', '-q', '.id'
            ], capture_output=True, text=True, cwd=os.path.dirname(db_path) or '.')
            
            if result.returncode == 0 and result.stdout.strip():
                release_id = result.stdout.strip()
                # Upload asset
                subprocess.run([
                    'gh', 'release', 'upload', 'v1.0.0', db_path, '--clobber'
                ], check=True, cwd=os.path.dirname(db_path) or '.')
                logger.info("✅ Base de datos subida a GitHub (gh CLI)")
                return True
            else:
                logger.warning("⚠️ Release v1.0.0 no existe. Creando...")
                subprocess.run([
                    'gh', 'release', 'create', 'v1.0.0',
                    '--title', 'Latest Listings Database',
                    '--notes', 'Base de datos de listings',
                    db_path
                ], cwd=os.path.dirname(db_path) or '.', check=True)
                logger.info("✅ Release creado y DB subida")
                return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error con gh CLI: {e}")
            return False
    else:
        # Fallback: try git commands
        logger.info("💡 gh CLI no encontrado. Intentar con git...")
        try:
            # Just add and commit if this is a git repo
            subprocess.run(['git', 'add', db_path], check=False)
            subprocess.run(['git', 'commit', '-m', 'Update listings database', '-n'], check=False)
            subprocess.run(['git', 'push'], check=False)
            logger.info("✅ DB guardada (git commit)")
            return True
        except Exception as e:
            logger.warning(f"⚠️ No se pudo subir a GitHub: {e}")
            logger.info("   La base de datos está en: " + db_path)
            return False


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
    parser.add_argument(
        '--upload',
        action='store_true',
        help='Solo subir la DB a GitHub sin scrapear'
    )
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='No subir la DB a GitHub despues de scrapear'
    )
    return parser.parse_args()


def main():
    """Main entry point for the scraper."""
    args = parse_args()
    
    # Modo solo upload
    if args.upload:
        logger.info("📤 Modo upload - subiendo DB a GitHub...")
        upload_to_github(args.db_path)
        return
    
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
        
        # Upload to GitHub if not disabled
        if not args.no_upload:
            upload_to_github(str(db_path))
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
        
    finally:
        scraper.close()
        db.close()


if __name__ == '__main__':
    main()
