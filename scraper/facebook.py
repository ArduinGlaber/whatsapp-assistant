"""
Facebook Scraper Module
======================
Handles browser automation and Facebook login using Selenium.
"""

import logging
import os
import time
import json
from dataclasses import dataclass
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


@dataclass
class Post:
    """Represents a Facebook post."""
    post_id: str
    author: str
    author_username: Optional[str]
    content: str
    image_url: Optional[str]
    timestamp: str
    raw_html: str


class FacebookScraper:
    """
    Facebook scraper using Selenium with Chrome/Chromium.
    
    Handles:
    - Browser automation
    - Login with credentials
    - Group post extraction
    - Cookie persistence
    """
    
    BASE_URL = "https://www.facebook.com"
    LOGIN_URL = "https://www.facebook.com/login"
    
    def __init__(self, headless: bool = True):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser without UI
        """
        self.headless = headless
        self.driver = None
        
    def _get_chrome_options(self) -> Options:
        """Configure Chrome options for headless browsing."""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')
        
        # Anti-detection measures
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        
        # Viewport
        options.add_argument('--window-size=1280,720')
        
        # User agent
        options.add_argument(
            '--user-agent=Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Language
        options.add_argument('--lang=es-ES')
        
        return options
    
    def start(self):
        """Start the browser."""
        options = self._get_chrome_options()
        
        # Try different Chrome paths
        chrome_paths = [
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/usr/bin/google-chrome',
            '/snap/bin/chromium',
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                service = Service(executable_path=path)
                try:
                    self.driver = webdriver.Chrome(service=service, options=options)
                    logger.info(f"Browser started with {path}")
                    return
                except Exception as e:
                    logger.debug(f"Failed to start Chrome at {path}: {e}")
                    continue
        
        # Fallback: try default
        try:
            self.driver = webdriver.Chrome(options=options)
            logger.info("Browser started with default Chrome")
        except Exception as e:
            raise RuntimeError(f"Could not start Chrome: {e}")
        
    def login(self) -> bool:
        """
        Login to Facebook using credentials from environment.
        
        Returns:
            True if login successful, False otherwise
        """
        email = os.getenv('FACEBOOK_EMAIL')
        password = os.getenv('FACEBOOK_PASSWORD')
        
        if not email or not password:
            logger.error("Facebook credentials not found in .env")
            return False
        
        try:
            self.start()
            
            # Try to load existing session
            if self._load_session():
                logger.info("✅ Loaded existing session")
                return True
            
            # Otherwise, do fresh login
            logger.info("🔐 Performing fresh login...")
            self.driver.get(self.LOGIN_URL)
            time.sleep(2)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 10)
            
            # Enter email
            email_input = wait.until(
                EC.presence_of_element_located((By.NAME, 'email'))
            )
            email_input.send_keys(email)
            time.sleep(0.5)
            
            # Enter password
            password_input = self.driver.find_element(By.NAME, 'pass')
            password_input.send_keys(password)
            time.sleep(0.5)
            
            # Click login button - try multiple selectors (Facebook changes these frequently)
            login_selectors = [
                (By.NAME, 'login'),
                (By.CSS_SELECTOR, 'button[name="login"]'),
                (By.CSS_SELECTOR, 'button[type="submit"]'),
                (By.CSS_SELECTOR, 'button[data-testid="royal_login_button"]'),
                (By.CSS_SELECTOR, 'input[type="submit"]'),
                (By.XPATH, '//button[contains(., "Iniciar sesión") or contains(., "Log in") or contains(., "Entrar")]'),
                (By.XPATH, '//button[@type="submit"]'),
            ]
            
            login_button = None
            for selector_type, selector_value in login_selectors:
                try:
                    login_button = self.driver.find_element(selector_type, selector_value)
                    if login_button:
                        break
                except NoSuchElementException:
                    continue
            
            if not login_button:
                # Last resort: submit the form
                logger.warning("Login button not found, trying form submit")
                try:
                    form = self.driver.find_element(By.CSS_SELECTOR, 'form[action*="login"]')
                    form.submit()
                except NoSuchElementException:
                    logger.error("Could not find login form")
                    return False
            else:
                login_button.click()
            
            # Wait for navigation
            time.sleep(5)
            
            # Check current URL for login state
            current_url = self.driver.current_url
            logger.info(f"URL after login attempt: {current_url}")
            
            # Check if we're still on login page or got redirected
            if 'login' in current_url or 'checkpoint' in current_url or 'two-factor' in current_url:
                # Check for error messages
                error_selectors = [
                    'div[role="alert"]',
                    'div[data-testid="royal_login_error"]',
                    'div[class*="error"]',
                ]
                error_msg = None
                for selector in error_selectors:
                    try:
                        error_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        error_msg = error_elem.text
                        break
                    except NoSuchElementException:
                        continue
                
                if error_msg:
                    logger.error(f"❌ Login failed: {error_msg}")
                else:
                    logger.error("❌ Login failed - check credentials or 2FA")
                return False
            else:
                logger.info("✅ Login successful")
                self._save_session()
                return True
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    def _load_session(self) -> bool:
        """
        Try to load a saved session from cookies file.
        
        Returns:
            True if session loaded successfully
        """
        cookies_file = 'data/facebook_cookies.json'
        
        if not os.path.exists(cookies_file):
            return False
            
        try:
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            
            # Load cookies
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    # Remove problematic fields
                    cookie.pop('sameSite', None)
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
            
            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)
            
            # Verify session is valid
            if 'login' not in self.driver.current_url:
                return True
                
        except Exception as e:
            logger.debug(f"Session load failed: {e}")
            
        return False
    
    def _save_session(self):
        """Save current session cookies to file."""
        os.makedirs('data', exist_ok=True)
        
        try:
            cookies = self.driver.get_cookies()
            with open('data/facebook_cookies.json', 'w') as f:
                json.dump(cookies, f)
            logger.info("✅ Session saved")
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")
    
    def scrape_group(self, group_id: str, max_posts: int = 50) -> list[Post]:
        """
        Scrape posts from a Facebook group.
        
        Args:
            group_id: The Facebook group ID
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of Post objects
        """
        posts = []
        group_url = f"{self.BASE_URL}/groups/{group_id}"
        
        logger.info(f"Navigating to {group_url}")
        self.driver.get(group_url)
        time.sleep(5)  # Extra wait for page load
        
        # Scroll to load more posts
        scroll_attempts = 0
        max_scroll_attempts = 50  # Increased for more posts
        
        while len(posts) < max_posts and scroll_attempts < max_scroll_attempts:
            # Scroll down
            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(3)  # Extra wait for lazy loading
            
            # Find post elements (various selectors for different Facebook layouts)
            post_selectors = [
                'div[role="article"]',
                'div[data-pagelet*="FeedUnit"]',
                'div[data-pagelet*="GroupFeedUnit"]',
                'div[class*="x1n2onr6"]',
            ]
            
            post_elements = []
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    post_elements.extend(elements)
                except Exception:
                    pass
            
            # Remove duplicates
            seen = set()
            unique_elements = []
            for elem in post_elements:
                elem_id = id(elem)
                if elem_id not in seen:
                    seen.add(elem_id)
                    unique_elements.append(elem)
            
            for element in unique_elements:
                post = self._extract_post(element)
                if post and post not in posts:
                    posts.append(post)
                    
                    if len(posts) >= max_posts:
                        break
            
            logger.info(f"   Loaded {len(posts)}/{max_posts} posts...")
            
            # Check if we reached the bottom
            old_height = self.driver.execute_script("return document.body.scrollHeight")
            time.sleep(1)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == old_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
        
        return posts[:max_posts]
    
    def _extract_post(self, element) -> Optional[Post]:
        """
        Extract data from a single post element.
        
        Args:
            element: Selenium WebElement
            
        Returns:
            Post object or None if extraction failed
        """
        try:
            # Get post content
            content = ''
            content_selectors = [
                'div[data-ad-preview="message"]',
                'span[dir="auto"]',
                'div[role="presentation"] span',
            ]
            
            for selector in content_selectors:
                try:
                    elems = element.find_elements(By.CSS_SELECTOR, selector)
                    for el in elems:
                        text = el.text.strip()
                        if len(text) > 10:  # Filter out short text
                            content = text
                            break
                except Exception:
                    pass
                if content:
                    break
            
            # Get author
            author = ''
            author_selectors = [
                'a[href*="/user/"]',
                'h3 a',
                'span a[role="link"]',
                'div[role="button"]',
            ]
            
            for selector in author_selectors:
                try:
                    author_elem = element.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip()
                    if author:
                        break
                except NoSuchElementException:
                    continue
            
            # Get author username from href
            author_username = None
            try:
                author_link = element.find_element(By.CSS_SELECTOR, 'a[href*="/user/"]')
                href = author_link.get_attribute('href')
                if '/user/' in href:
                    username = href.split('/user/')[-1].split('/')[0]
                    author_username = username
            except NoSuchElementException:
                pass
            
            # Get image URL
            image_url = None
            image_selectors = [
                'image[href*="scontent"]',
                'img[src*="scontent"]',
                'img[src*="fbcdn"]',
                'div[role="img"] img',
            ]
            
            for selector in image_selectors:
                try:
                    img = element.find_element(By.CSS_SELECTOR, selector)
                    image_url = img.get_attribute('src') or img.get_attribute('href')
                    if image_url and ('scontent' in image_url or 'fbcdn' in image_url):
                        break
                    else:
                        image_url = None
                except NoSuchElementException:
                    continue
            
            # Get timestamp
            timestamp = ''
            time_selectors = [
                'a[href*="/groups/"][role="link"]',
                'span[data-ad-preview="message"] + span',
                'abbr',
            ]
            
            for selector in time_selectors:
                try:
                    time_elem = element.find_element(By.CSS_SELECTOR, selector)
                    timestamp = time_elem.text.strip()
                    if timestamp and len(timestamp) < 20:
                        break
                except NoSuchElementException:
                    continue
            
            # Get post ID from element
            post_id = element.get_attribute('id') or str(hash(content[:50]))
            
            if not content and not image_url:
                return None
                
            return Post(
                post_id=post_id,
                author=author or 'Unknown',
                author_username=author_username,
                content=content,
                image_url=image_url,
                timestamp=timestamp,
                raw_html=element.get_attribute('innerHTML')[:500] if element else ''
            )
            
        except Exception as e:
            logger.debug(f"Post extraction error: {e}")
            return None
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
        logger.info("Browser closed")
