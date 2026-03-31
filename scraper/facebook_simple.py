"""
Facebook Scraper sin Selenium
===========================
Usa requests + BeautifulSoup en lugar de Selenium/Chrome.
Más ligero, no necesita chromedriver.
"""

import logging
import os
import time
import json
import re
from dataclasses import dataclass
from typing import Optional, List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


@dataclass
class Post:
    """Representa un post de Facebook."""
    post_id: str
    author: str
    author_username: Optional[str]
    content: str
    image_url: Optional[str]
    timestamp: str
    raw_html: str


class FacebookScraperSimple:
    """
    Scraper simple usando requests.
    """
    
    BASE_URL = "https://m.facebook.com"
    GROUP_URL = "https://m.facebook.com/groups/{group_id}"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
    
    def login(self) -> bool:
        """Login usando requests."""
        email = os.getenv('FACEBOOK_EMAIL')
        password = os.getenv('FACEBOOK_PASSWORD')
        
        if not email or not password:
            logger.error("Facebook credentials not found")
            return False
        
        # Try to load existing session
        if self._load_session():
            logger.info("✅ Session loaded")
            return True
        
        logger.info("🔐 Logging in...")
        
        # Get login page
        login_url = f"{self.BASE_URL}/login"
        try:
            response = self.session.get(login_url, timeout=30)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find form inputs
            lsd = soup.find('input', {'name': 'lsd'})
            lsd_value = lsd['value'] if lsd else ''
            
            # Submit login
            login_data = {
                'email': email,
                'pass': password,
                'lsd': lsd_value,
                'login': 'Iniciar sesión',
            }
            
            # Look for form action
            form = soup.find('form', {'id': 'login_form'}) or soup.find('form')
            if form and form.get('action'):
                action = form['action']
                if not action.startswith('http'):
                    action = self.BASE_URL + action
            else:
                action = f"{self.BASE_URL}/login/device-based/validate-lsd"
            
            response = self.session.post(action, data=login_data, timeout=30, allow_redirects=True)
            
            # Check if logged in
            if 'login' not in response.url.lower() and 'checkpoint' not in response.url.lower():
                logger.info(f"✅ Login successful: {response.url}")
                self._save_session()
                return True
            else:
                logger.error(f"❌ Login failed: {response.url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    def _load_session(self) -> bool:
        """Cargar sesión guardada."""
        cookies_file = 'data/facebook_cookies_simple.json'
        if not os.path.exists(cookies_file):
            return False
        
        try:
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            self.session.cookies.update(cookies)
            
            # Verify session
            response = self.session.get(self.BASE_URL, timeout=30)
            if 'login' not in response.url.lower():
                logger.info("✅ Session valid")
                return True
        except Exception as e:
            logger.debug(f"Session load failed: {e}")
        
        return False
    
    def _save_session(self):
        """Guardar sesión."""
        os.makedirs('data', exist_ok=True)
        try:
            with open('data/facebook_cookies_simple.json', 'w') as f:
                json.dump(dict(self.session.cookies), f)
            logger.info("✅ Session saved")
        except Exception as e:
            logger.warning(f"Could not save session: {e}")
    
    def scrape_group(self, group_id: str, max_posts: int = 50) -> List[Post]:
        """Scrape posts de un grupo."""
        posts = []
        url = self.GROUP_URL.format(group_id=group_id)
        
        logger.info(f"📄 Scraping {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find posts - mobile Facebook structure
            article_selectors = [
                'article[data-sigil="story-body"]',
                'div[data-sigil="feed-story"]',
                'article',
                'div[data-pagelet*="TimelineFeedUnit"]',
            ]
            
            post_elements = []
            for selector in article_selectors:
                post_elements.extend(soup.select(selector))
            
            logger.info(f"📝 Found {len(post_elements)} potential posts")
            
            for i, elem in enumerate(post_elements[:max_posts]):
                post = self._extract_post(elem)
                if post:
                    posts.append(post)
                    logger.info(f"   [{i+1}] {post.content[:50]}...")
            
        except Exception as e:
            logger.error(f"❌ Scraping error: {e}")
        
        return posts
    
    def _extract_post(self, elem) -> Optional[Post]:
        """Extraer datos de un post."""
        try:
            # Content
            content = ''
            for tag in ['p', 'div[data-sigil="story-message"]', 'span[dir="auto"]']:
                elems = elem.select(tag)
                for e in elems:
                    text = e.get_text(strip=True)
                    if len(text) > 10:
                        content = text
                        break
                if content:
                    break
            
            # Author
            author = ''
            for selector in ['strong a', 'span[data-sigil="who"]', 'h3 a']:
                elems = elem.select(selector)
                for e in elems:
                    text = e.get_text(strip=True)
                    if text and len(text) < 50:
                        author = text
                        break
                if author:
                    break
            
            # Timestamp
            timestamp = ''
            for selector in ['abbr', 'span[title]', 'a[href*="?__xt"]']:
                elems = elem.select(selector)
                for e in elems:
                    text = e.get_text(strip=True) or e.get('title', '')
                    if text:
                        timestamp = text
                        break
                if timestamp:
                    break
            
            # Image
            image_url = None
            for selector in ['img[data-sigil*="image"]', 'img[src*="scontent"]', 'a[href*="photo"] img']:
                img = elem.select_one(selector)
                if img:
                    image_url = img.get('src') or img.get('data-src')
                    if image_url and ('scontent' in image_url or 'fbcdn' in image_url):
                        break
                    image_url = None
            
            # Post ID
            post_id = elem.get('data-sigil', '') or elem.get('id', '') or str(hash(content[:30]))
            
            if not content and not image_url:
                return None
            
            return Post(
                post_id=post_id,
                author=author or 'Unknown',
                author_username=None,
                content=content,
                image_url=image_url,
                timestamp=timestamp,
                raw_html=str(elem)[:500]
            )
            
        except Exception as e:
            logger.debug(f"Post extraction error: {e}")
            return None
    
    def close(self):
        """Cerrar sesión."""
        self.session.close()
