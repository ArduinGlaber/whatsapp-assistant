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
    MOBILE_BASE = "https://m.facebook.com"
    MOBILE_LOGIN = "https://m.facebook.com/login.php"
    
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
        
    def _dismiss_popups(self):
        """Dismiss any popups that might block login (cookies, notifications, etc)."""
        popup_selectors = [
            ('button[data-testid="cookie-policy-dialog-accept-button"]', 'Accept cookies'),
            ('button[title="Aceptar todo"]', 'Accept all'),
            ('button[title="Accept All"]', 'Accept All'),
            ('button[aria-label="Aceptar"]', 'Accept (es)'),
            ('button[aria-label="Accept"]', 'Accept (en)'),
            ('div[role="dialog"] button', 'Dialog button'),
            ('div[data-pagelet*="CookieConsent"] button', 'Cookie consent'),
            ('div[data-testid="cookie-policy-dialog"] button', 'Cookie policy'),
            ('div[aria-modal="true"] button:first-child', 'Modal first button'),
        ]
        
        for selector, name in popup_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        time.sleep(1)
                        logger.info(f"✅ Dismissed: {name}")
                        return True
            except Exception:
                pass
        return False
    
    def login(self) -> bool:
        """
        Login to Facebook using credentials from environment.
        Uses mobile version (m.facebook.com) which has less anti-bot protection.
        
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
            
            # Try to load existing session (mobile)
            if self._load_session_mobile():
                logger.info("✅ Loaded existing mobile session")
                return True
            
            # Use mobile version for login - simpler and less blocked
            logger.info("🔐 Performing mobile login...")
            self.driver.get(self.MOBILE_LOGIN)
            time.sleep(3)
            
            # Wait for page
            wait = WebDriverWait(self.driver, 15)
            
            # Mobile email input
            try:
                email_input = wait.until(
                    EC.element_to_be_clickable((By.NAME, 'email'))
                )
                email_input.click()
                email_input.clear()
                email_input.send_keys(email)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Email input issue: {e}")
                # Try alternative selectors for mobile
                alt_selectors = [
                    'input[name="email"]',
                    'input[id="m_login_email"]',
                    'input[type="text"]',
                    'input[name="username"]',
                ]
                for sel in alt_selectors:
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, sel)
                        if el.is_displayed():
                            el.click()
                            el.clear()
                            el.send_keys(email)
                            break
                    except Exception:
                        continue
            
            # Mobile password input
            try:
                password_input = self.driver.find_element(By.NAME, 'pass')
                password_input.click()
                password_input.clear()
                password_input.send_keys(password)
            except Exception:
                alt_selectors = [
                    'input[name="pass"]',
                    'input[id="m_login_password"]',
                    'input[type="password"]',
                ]
                for sel in alt_selectors:
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, sel)
                        if el.is_displayed():
                            el.click()
                            el.clear()
                            el.send_keys(password)
                            break
                    except Exception:
                        continue
            
            time.sleep(0.5)
            
            # Mobile login button - simpler selectors
            login_selectors = [
                (By.NAME, 'login'),
                (By.CSS_SELECTOR, 'button[name="login"]'),
                (By.CSS_SELECTOR, 'button[type="submit"]'),
                (By.CSS_SELECTOR, 'input[type="submit"]'),
                (By.XPATH, '//button[contains(text(), "Iniciar sesi")]'),
                (By.XPATH, '//input[@type="submit"]'),
            ]
            
            login_button = None
            for selector_type, selector_value in login_selectors:
                try:
                    el = wait.until(EC.element_to_be_clickable((selector_type, selector_value)))
                    login_button = el
                    break
                except Exception:
                    continue
            
            if not login_button:
                # Try form submit
                try:
                    form = self.driver.find_element(By.CSS_SELECTOR, 'form')
                    form.submit()
                except NoSuchElementException:
                    logger.error("Could not find login form")
                    return False
            else:
                login_button.click()
            
            # Wait for navigation
            time.sleep(5)
            
            current_url = self.driver.current_url
            logger.info(f"URL after login: {current_url}")
            
            # Check for login failure or verification pages
            if any(x in current_url for x in ['login', 'checkpoint', 'two_step_verification', 'authentication', 'confirm', 'verify']):
                error_msg = None
                try:
                    error_elem = self.driver.find_element(By.CSS_SELECTOR, 'div[class*="error"], #error, [role="alert"]')
                    error_msg = error_elem.text
                except Exception:
                    pass
                
                if error_msg:
                    logger.error(f"❌ Login failed: {error_msg}")
                else:
                    logger.error(f"❌ Login failed - Facebook requires verification (2FA, phone confirm, etc)")
                    logger.error(f"   URL: {current_url}")
                return False
            
            # Verify we're actually logged in by checking for logged-in elements
            try:
                # Look for profile, home, or other logged-in indicators
                logged_in_indicators = [
                    'a[href*="/profile"]',
                    'a[href*="/me"]',
                    'div[data-sigil="profile-cover"]',
                    'div[data-sigil="logged_in"]',
                    'a[href*="logout"]',
                    'a[title="Inicio"]',  # Home button (Spanish)
                ]
                
                is_logged_in = False
                for selector in logged_in_indicators:
                    try:
                        elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if elem.is_displayed():
                            is_logged_in = True
                            logger.info(f"✅ Verified logged in (found: {selector})")
                            break
                    except NoSuchElementException:
                        continue
                
                if not is_logged_in:
                    # Try getting page source to see what's actually there
                    page_text = self.driver.page_source[:500]
                    logger.warning(f"⚠️ Could not verify login - page may not be logged in")
                    logger.warning(f"   Page preview: {page_text[:200]}...")
                    # Still try to continue - maybe we'll get lucky
                
                logger.info("✅ Login successful")
                self._save_session_mobile()
                return True
                
            except Exception as e:
                logger.error(f"❌ Login verification error: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            return False
    
    def _load_session_mobile(self) -> bool:
        """Try to load a saved mobile session from cookies file."""
        cookies_file = 'data/facebook_mobile_cookies.json'
        
        if not os.path.exists(cookies_file):
            return False
            
        try:
            self.driver.get(self.MOBILE_BASE)
            time.sleep(2)
            
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
            
            for cookie in cookies:
                try:
                    cookie.pop('sameSite', None)
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
            
            self.driver.refresh()
            time.sleep(3)
            
            # Mobile login check
            if 'login' not in self.driver.current_url:
                logger.info("✅ Mobile session loaded")
                return True
                
        except Exception as e:
            logger.debug(f"Mobile session load failed: {e}")
            
        return False
    
    def _save_session_mobile(self):
        """Save mobile session cookies to file."""
        os.makedirs('data', exist_ok=True)
        
        try:
            cookies = self.driver.get_cookies()
            with open('data/facebook_mobile_cookies.json', 'w') as f:
                json.dump(cookies, f)
            logger.info("✅ Mobile session saved")
        except Exception as e:
            logger.warning(f"Failed to save mobile session: {e}")
    
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
        Scrape posts from a Facebook group using mobile version.
        
        Args:
            group_id: The Facebook group ID
            max_posts: Maximum number of posts to scrape
            
        Returns:
            List of Post objects
        """
        posts = []
        # Use mobile version for scraping - simpler HTML structure
        group_url = f"{self.MOBILE_BASE}/groups/{group_id}"
        
        logger.info(f"Navigating to {group_url}")
        self.driver.get(group_url)
        time.sleep(5)
        
        # Scroll to load more posts
        scroll_attempts = 0
        max_scroll_attempts = 50
        
        while len(posts) < max_posts and scroll_attempts < max_scroll_attempts:
            self.driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
            time.sleep(3)
            
            # Mobile post selectors - simpler than desktop
            post_selectors = [
                'div[data-sigil="feed-story"]',
                'div[data-sigil*="story"]',
                'article',
                'div[id*="story"]',
                'div[class*="userContentWrapper"]',
                'div[data-pagelet*="FeedUnit"]',
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
                post = self._extract_post_mobile(element)
                if post and post not in posts:
                    posts.append(post)
                    
                    if len(posts) >= max_posts:
                        break
            
            logger.info(f"   Loaded {len(posts)}/{max_posts} posts...")
            
            old_height = self.driver.execute_script("return document.body.scrollHeight")
            time.sleep(1)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == old_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
        
        return posts[:max_posts]
    
    def _extract_post_mobile(self, element) -> Optional[Post]:
        """Extract data from a mobile post element."""
        try:
            # Get post content
            content = ''
            content_selectors = [
                'p',
                'div[data-sigil="story-message"]',
                'div[data-sigil="feed-story-message"]',
                'span[dir="auto"]',
            ]
            
            for selector in content_selectors:
                try:
                    elems = element.find_elements(By.CSS_SELECTOR, selector)
                    for el in elems:
                        text = el.text.strip()
                        if len(text) > 10:
                            content = text
                            break
                except Exception:
                    pass
                if content:
                    break
            
            # Get author
            author = ''
            author_selectors = [
                'a[data-sigil*="author"]',
                'strong a',
                'h3 a',
                'span[data-sigil="who"]',
            ]
            
            for selector in author_selectors:
                try:
                    author_elem = element.find_element(By.CSS_SELECTOR, selector)
                    author = author_elem.text.strip()
                    if author:
                        break
                except NoSuchElementException:
                    continue
            
            # Get image URL
            image_url = None
            image_selectors = [
                'img[data-sigil*="image"]',
                'img[src*="scontent"]',
                'img[src*="fbcdn"]',
            ]
            
            for selector in image_selectors:
                try:
                    img = element.find_element(By.CSS_SELECTOR, selector)
                    image_url = img.get_attribute('src')
                    if image_url and ('scontent' in image_url or 'fbcdn' in image_url):
                        break
                    else:
                        image_url = None
                except NoSuchElementException:
                    continue
            
            # Get timestamp
            timestamp = ''
            time_selectors = [
                'abbr',
                'span[data-sigil="timestamp"]',
                'span[title]',
            ]
            
            for selector in time_selectors:
                try:
                    time_elem = element.find_element(By.CSS_SELECTOR, selector)
                    timestamp = time_elem.text.strip() or time_elem.get_attribute('title') or ''
                    if timestamp and len(timestamp) < 30:
                        break
                except NoSuchElementException:
                    continue
            
            post_id = element.get_attribute('id') or str(hash(content[:50]))[:20]
            
            if not content and not image_url:
                return None
                
            return Post(
                post_id=post_id,
                author=author or 'Unknown',
                author_username=None,
                content=content,
                image_url=image_url,
                timestamp=timestamp,
                raw_html=element.get_attribute('innerHTML')[:500] if element else ''
            )
            
        except Exception as e:
            logger.debug(f"Mobile post extraction error: {e}")
            return None
    
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
