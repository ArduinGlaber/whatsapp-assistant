"""
OCR Module
=========
Extracts text from images using Tesseract OCR.
"""

import logging
import os
import tempfile
from pathlib import Path

import requests
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def extract_text_from_image(image_url: str, lang: str = 'spa+eng') -> str:
    """
    Download image and extract text using Tesseract OCR.
    
    Args:
        image_url: URL of the image to process
        lang: Tesseract language codes (default: Spanish + English)
        
    Returns:
        Extracted text from the image
        
    Raises:
        Exception: If image download or OCR fails
    """
    if not image_url:
        return ""
    
    try:
        # Download image
        logger.debug(f"Downloading image from {image_url[:50]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(response.content)
            temp_path = f.name
            
        try:
            # Open and process image
            img = Image.open(temp_path)
            
            # Optional: Preprocess image for better OCR
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # Increase contrast slightly
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.2)
            
            # Run OCR
            text = pytesseract.image_to_string(
                img,
                lang=lang,
                config='--psm 6'  # Assume uniform block of text
            )
            
            # Clean up
            text = text.strip()
            
            logger.debug(f"OCR extracted {len(text)} characters")
            
            return text
            
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to download image: {e}")
        return ""
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""


def extract_text_from_file(image_path: str, lang: str = 'spa+eng') -> str:
    """
    Extract text from a local image file.
    
    Args:
        image_path: Path to the local image file
        lang: Tesseract language codes
        
    Returns:
        Extracted text
    """
    try:
        img = Image.open(image_path)
        
        if img.mode != 'L':
            img = img.convert('L')
            
        text = pytesseract.image_to_string(
            img,
            lang=lang,
            config='--psm 6'
        )
        
        return text.strip()
        
    except Exception as e:
        logger.warning(f"OCR failed for {image_path}: {e}")
        return ""


def check_tesseract() -> bool:
    """
    Check if Tesseract is properly installed.
    
    Returns:
        True if Tesseract is available
    """
    try:
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract version: {version}")
        return True
    except Exception as e:
        logger.error(f"Tesseract not found: {e}")
        logger.error("Install with: apt install tesseract-ocr tesseract-ocr-spa")
        return False


def check_tesseract_languages() -> list[str]:
    """
    Check which languages are available in Tesseract.
    
    Returns:
        List of available language codes
    """
    try:
        return pytesseract.get_languages()
    except Exception:
        return []
