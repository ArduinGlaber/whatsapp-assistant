"""
Listing Parser Module
=====================
Extracts structured data from Facebook posts using pattern matching and text analysis.
"""

import re
import logging
from typing import Optional

from scraper.ocr import extract_text_from_image

logger = logging.getLogger(__name__)


# Patterns for detecting buy/sell intent
SELL_PATTERNS = [
    r'\bvendo\b',
    r'\bventa\b',
    r'\bcompro\b(?!.*[é])?',  # compra (with accent) but NOT comprobar
    r'\bcompramos\b',
    r'\bcomprar\b',
    r'\binteresad[oa]\s+en\s+vender',
    r'\b buscar\b.*\bcomprar\b',
    r'\b\$[\d]+\b',  # Price pattern
]

BUY_PATTERNS = [
    r'\bcompro\b',
    r'\bcompramos\b', 
    r'\bcomprar\b',
    r'\b busco\b',
    r'\bnecesito\b',
    r'\bquiero\b.*\bcomprar\b',
    r'\b buscando\b',
    r'\binteresad[oa]\s+en\s+comprar',
]

# Pattern for prices (various currencies)
PRICE_PATTERNS = [
    r'\$?\s*([\d,.]+)\s*(CUC|CUP|USD|EUR|€|\$)',
    r'([\d,.]+)\s*(CUC|CUP|USD|EUR|€)',
    r'(?: precio|val[eou]r| cuesta| cuesta|amount)[:\s]*([\d,.]+)',
    r'\$([\d,.]+)',
]

# Pattern for phone numbers
PHONE_PATTERNS = [
    r'(?:tel|phone|móvil|mobile|cel|whatsapp|wa)[:\s]*([\d\s\-()+]{8,})',
    r'([5-7]\d{7})',  # Cuban mobile numbers: 5XXXXXXXX or 7XXXXXXXX
    r'\+53\s*([5-7]\d{7})',
    r'([5-7]\d{3}[\s\-]?\d{4})',
]

# Facebook username pattern
FB_USERNAME_PATTERN = r'(?:@|\b)([a-zA-Z0-9._]{3,30})(?:\s|$|[,.:])'


class ListingParser:
    """
    Parses Facebook posts to extract structured listing information.
    
    Extracts:
    - Listing type (buy/sell)
    - Article name
    - Price and currency
    - Contact information (phone or FB username)
    """
    
    def __init__(self):
        """Initialize parser with compiled regex patterns."""
        self.sell_patterns = [re.compile(p, re.IGNORECASE) for p in SELL_PATTERNS]
        self.buy_patterns = [re.compile(p, re.IGNORECASE) for p in BUY_PATTERNS]
        self.price_patterns = [re.compile(p, re.IGNORECASE) for p in PRICE_PATTERNS]
        self.phone_patterns = [re.compile(p, re.IGNORECASE) for p in PHONE_PATTERNS]
        
    def parse(self, post) -> Optional[dict]:
        """
        Parse a Facebook post and extract listing information.
        
        Args:
            post: Post object from facebook.py
            
        Returns:
            Dictionary with structured listing data, or None if not a marketplace post
        """
        # Combine text and OCR content
        text = post.content
        
        if post.image_url:
            try:
                ocr_text = extract_text_from_image(post.image_url)
                text = f"{text}\n{ocr_text}"
                logger.debug(f"OCR extracted: {ocr_text[:100]}...")
            except Exception as e:
                logger.warning(f"OCR failed: {e}")
        
        # Determine if this is a marketplace post
        listing_type = self._detect_type(text)
        if not listing_type:
            return None
            
        # Extract components
        article = self._extract_article(text)
        if not article:
            # Try to use the raw text as article
            article = text[:100].strip()
            
        price, currency = self._extract_price(text)
        phone = self._extract_phone(text)
        fb_username = self._extract_fb_username(text, post.author_username)
        
        # Use author as fallback for contact
        if not phone and not fb_username:
            fb_username = post.author_username or post.author
            
        return {
            'type': listing_type,
            'article': article,
            'price': price,
            'currency': currency,
            'contact_phone': phone,
            'contact_fb_username': fb_username,
            'original_text': post.content,
            'ocr_text': text if post.image_url else '',
            'post_id': post.post_id,
            'author': post.author,
            'timestamp': post.timestamp,
        }
    
    def _detect_type(self, text: str) -> Optional[str]:
        """
        Detect if this is a buy or sell post.
        
        Returns:
            'V' for venta, 'C' for compra, None if unclear
        """
        # Count matches for each type
        sell_score = sum(1 for p in self.sell_patterns if p.search(text))
        buy_score = sum(1 for p in self.buy_patterns if p.search(text))
        
        if sell_score > buy_score:
            return 'V'
        elif buy_score > sell_score:
            return 'C'
        
        # Default to sell if we have price
        if any(p.search(text) for p in self.price_patterns):
            return 'V'
            
        return None  # Not clearly a marketplace post
    
    def _extract_article(self, text: str) -> Optional[str]:
        """
        Extract the article/item being bought or sold.
        
        Strategy:
        - Remove common keywords (vendo, compro, precio, etc.)
        - Look for the main noun phrase
        - Clean up the result
        """
        # Remove common keywords
        cleaned = text
        
        # Remove buy/sell keywords
        keywords_to_remove = [
            r'\bvendo\b', r'\bventa\b', r'\bcompro\b', r'\bcomprar\b',
            r'\b busco\b', r'\bnecesito\b', r'\bbusco\b',
            r'\b precio\b', r'\bval[eou]r\b', r'\bcuesta\b',
            r'\binteresad[oa]\b',
        ]
        for kw in keywords_to_remove:
            cleaned = re.sub(kw, ' ', cleaned, flags=re.IGNORECASE)
        
        # Remove price patterns
        for p in self.price_patterns:
            cleaned = p.sub(' ', cleaned)
            
        # Remove phone patterns
        for p in self.phone_patterns:
            cleaned = p.sub(' ', cleaned)
            
        # Clean up
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r'^[,\.\-:]+', '', cleaned).strip()
        
        # Take first meaningful part (up to ~80 chars)
        if len(cleaned) > 3:
            return cleaned[:80].strip()
            
        return None
    
    def _extract_price(self, text: str) -> tuple[Optional[float], Optional[str]]:
        """
        Extract price and currency from text.
        
        Returns:
            Tuple of (price as float, currency as string)
        """
        for pattern in self.price_patterns:
            match = pattern.search(text)
            if match:
                # Get price value
                price_str = match.group(1) if match.lastindex >= 1 else match.group(0)
                price_str = re.sub(r'[^\d.,]', '', price_str)
                price_str = price_str.replace(',', '.')
                
                try:
                    price = float(price_str)
                except ValueError:
                    price = None
                
                # Get currency
                currency = None
                if match.lastindex >= 2:
                    currency = match.group(2).upper()
                else:
                    # Try to infer from text
                    currency = self._detect_currency(text)
                    
                return price, currency
                
        return None, None
    
    def _detect_currency(self, text: str) -> Optional[str]:
        """Detect currency from context."""
        text_upper = text.upper()
        
        if 'CUC' in text_upper:
            return 'CUC'
        elif 'CUP' in text_upper:
            return 'CUP'
        elif 'USD' in text_upper or '$' in text:
            return 'USD'
        elif 'EUR' in text_upper or '€' in text:
            return 'EUR'
            
        # Default to CUC for Cuban context
        return 'CUC'
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """
        Extract phone number from text.
        
        Returns:
            Cleaned phone number string or None
        """
        for pattern in self.phone_patterns:
            match = pattern.search(text)
            if match:
                phone = match.group(1) if match.lastindex >= 1 else match.group(0)
                # Clean up
                phone = re.sub(r'[^\d+]', '', phone)
                
                # Ensure it starts with country code if Cuban number
                if len(phone) == 8:  # 5XXXXXXXX or 7XXXXXXXX
                    phone = '+53' + phone
                    
                return phone
                
        return None
    
    def _extract_fb_username(self, text: str, author_username: str = None) -> Optional[str]:
        """
        Extract Facebook username from text.
        
        Args:
            text: Post text
            author_username: Username from author link
            
        Returns:
            Facebook username or None
        """
        # Look for @username pattern
        match = re.search(FB_USERNAME_PATTERN, text)
        if match:
            return match.group(1)
            
        # Use author username if available
        return author_username
