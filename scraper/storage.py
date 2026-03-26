"""
Database Module
==============
SQLite storage for listings and conversation history.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for WhatsApp Assistant.
    
    Tables:
    - groups: Facebook groups to scrape
    - listings: Buy/sell listings extracted from posts
    - conversations: WhatsApp conversations
    - messages: Individual messages in conversations
    - scraping_logs: Log of scraping operations
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()
        
    def _connect(self):
        """Establish database connection."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        self.conn.execute('PRAGMA foreign_keys = ON')
        
        logger.info(f"Connected to database: {self.db_path}")
        
    def _init_schema(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Groups table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                group_id TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_scraped_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER REFERENCES groups(id),
                post_id TEXT,
                type TEXT NOT NULL CHECK(type IN ('V', 'C')),
                article TEXT NOT NULL,
                price REAL,
                currency TEXT,
                contact_phone TEXT,
                contact_fb_username TEXT,
                original_text TEXT,
                ocr_text TEXT,
                is_available INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for faster searches
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_listings_article 
            ON listings(article COLLATE NOCASE)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_listings_type 
            ON listings(type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_listings_available 
            ON listings(is_available)
        ''')
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_jid TEXT UNIQUE NOT NULL,
                contact_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER REFERENCES conversations(id),
                sender TEXT NOT NULL CHECK(sender IN ('U', 'B')),  -- U=User, B=Bot
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index for message retrieval
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, created_at)
        ''')
        
        # Scraping logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER REFERENCES groups(id),
                started_at TEXT NOT NULL,
                completed_at TEXT,
                posts_found INTEGER DEFAULT 0,
                posts_saved INTEGER DEFAULT 0,
                errors TEXT,
                status TEXT DEFAULT 'running'
            )
        ''')
        
        # Insert default group if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO groups (name, url, group_id) 
            VALUES ('Marketplace', 'https://facebook.com/groups/774703760229907/', '774703760229907')
        ''')
        
        self.conn.commit()
        logger.info("Database schema initialized")
        
    def save_listing(self, listing: dict) -> int:
        """
        Save a listing to the database.
        
        Args:
            listing: Dictionary with listing data
            
        Returns:
            ID of the inserted row
        """
        cursor = self.conn.cursor()
        
        # Check for duplicate post_id
        if listing.get('post_id'):
            cursor.execute(
                'SELECT id FROM listings WHERE post_id = ? AND group_id = ?',
                (listing['post_id'], 1)  # TODO: Get group_id properly
            )
            existing = cursor.fetchone()
            if existing:
                logger.debug(f"Listing {listing['post_id']} already exists, skipping")
                return existing['id']
        
        cursor.execute('''
            INSERT INTO listings (
                post_id, type, article, price, currency,
                contact_phone, contact_fb_username,
                original_text, ocr_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing.get('post_id'),
            listing['type'],
            listing['article'],
            listing.get('price'),
            listing.get('currency'),
            listing.get('contact_phone'),
            listing.get('contact_fb_username'),
            listing.get('original_text', ''),
            listing.get('ocr_text', '')
        ))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def search_listings(
        self,
        query: str,
        listing_type: str = 'V',
        limit: int = 10
    ) -> list[dict]:
        """
        Search listings by article name.
        
        Args:
            query: Search query (will use LIKE %query%)
            listing_type: 'V' for sales, 'C' for purchases
            limit: Maximum number of results
            
        Returns:
            List of matching listings
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT 
                article, price, currency,
                contact_phone, contact_fb_username
            FROM listings
            WHERE is_available = 1
              AND type = ?
              AND article LIKE ?
            ORDER BY scraped_at DESC
            LIMIT ?
        ''', (listing_type, f'%{query}%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_conversation(self, contact_jid: str) -> Optional[dict]:
        """Get or create a conversation by contact JID."""
        cursor = self.conn.cursor()
        
        cursor.execute(
            'SELECT * FROM conversations WHERE contact_jid = ?',
            (contact_jid,)
        )
        row = cursor.fetchone()
        
        if row:
            return dict(row)
            
        # Create new conversation
        cursor.execute(
            'INSERT INTO conversations (contact_jid) VALUES (?)',
            (contact_jid,)
        )
        self.conn.commit()
        
        cursor.execute(
            'SELECT * FROM conversations WHERE id = ?',
            (cursor.lastrowid,)
        )
        return dict(cursor.fetchone())
        
    def save_message(
        self,
        conversation_id: int,
        sender: str,
        content: str
    ) -> int:
        """
        Save a message to conversation history.
        
        Args:
            conversation_id: ID of the conversation
            sender: 'U' for user, 'B' for bot
            content: Message content
            
        Returns:
            ID of the inserted message
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (conversation_id, sender, content)
            VALUES (?, ?, ?)
        ''', (conversation_id, sender, content))
        
        # Update conversation timestamp
        cursor.execute('''
            UPDATE conversations 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (conversation_id,))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def get_conversation_history(
        self,
        conversation_id: int,
        limit: int = 20
    ) -> list[dict]:
        """
        Get recent messages from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Number of recent messages to retrieve
            
        Returns:
            List of messages, oldest first
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT sender, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        ''', (conversation_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
        
    def log_scraping_start(self, group_id: int) -> int:
        """Log the start of a scraping operation."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO scraping_logs (group_id, started_at, status)
            VALUES (?, ?, 'running')
        ''', (group_id, datetime.now().isoformat()))
        
        self.conn.commit()
        return cursor.lastrowid
        
    def log_scraping_complete(
        self,
        log_id: int,
        posts_found: int,
        posts_saved: int,
        errors: str = None,
        status: str = 'completed'
    ):
        """Log completion of a scraping operation."""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE scraping_logs
            SET completed_at = ?,
                posts_found = ?,
                posts_saved = ?,
                errors = ?,
                status = ?
            WHERE id = ?
        ''', (
            datetime.now().isoformat(),
            posts_found,
            posts_saved,
            errors,
            status,
            log_id
        ))
        
        # Update group's last_scraped_at
        cursor.execute('''
            UPDATE groups
            SET last_scraped_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), 1))  # TODO: Get correct group_id
        
        self.conn.commit()
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
