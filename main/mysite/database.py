"""
Database module for HurairahGPT - SQLite-based embedded database.

This module provides:
- SQLite database connection management
- Schema initialization and migrations
- CRUD operations for users, sessions, and rate limits
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List, Generator
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'hurairahgpt.db')
SCHEMA_VERSION = 1


class DatabaseError(Exception):
    """Custom exception for database operations."""
    pass


def get_db_path() -> str:
    """Get the database file path."""
    return DATABASE_PATH


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    
    Yields:
        sqlite3.Connection: Database connection with row factory set.
    
    Example:
        with get_connection() as db:
            db.execute("SELECT * FROM users")
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Database operation failed: {e}")
    finally:
        conn.close()


def init_db() -> None:
    """
    Initialize the database schema.
    
    Creates all required tables if they don't exist:
    - users: User accounts and preferences
    - sessions: Chat sessions per user
    - messages: Individual messages in sessions
    - rate_limits: Rate limiting data
    - migration_log: Tracks migration history
    """
    schema_sql = """
    -- Users table: stores user accounts and preferences
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        theme TEXT DEFAULT 'dark',
        personality TEXT DEFAULT 'default',
        tier TEXT DEFAULT 'free',
        image_usage_count INTEGER DEFAULT 0,
        image_usage_last_reset TEXT,
        upgrade_history TEXT,  -- JSON array of upgrade events
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- Sessions table: stores chat sessions per user
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT UNIQUE NOT NULL,
        name TEXT DEFAULT 'New Chat',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Messages table: stores individual messages in sessions
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        content TEXT NOT NULL,
        sender TEXT NOT NULL,  -- 'user' or 'bot'
        time TEXT NOT NULL,
        metadata TEXT,  -- JSON for additional message data (e.g., image_info)
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
    );

    -- Rate limits table: stores rate limiting data
    CREATE TABLE IF NOT EXISTS rate_limits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identifier TEXT UNIQUE NOT NULL,  -- IP address or user email
        limit_type TEXT NOT NULL,  -- 'ip' or 'user'
        request_count INTEGER DEFAULT 0,
        window_start TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- Migration log table: tracks migration history
    CREATE TABLE IF NOT EXISTS migration_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_name TEXT NOT NULL,
        migration_version INTEGER NOT NULL,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
        records_migrated INTEGER DEFAULT 0,
        errors TEXT,  -- JSON array of errors
        UNIQUE(migration_name, migration_version)
    );

    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_rate_limits_identifier ON rate_limits(identifier);
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """
    
    with get_connection() as db:
        db.executescript(schema_sql)
        
        # Insert initial migration record if not exists
        db.execute("""
            INSERT OR IGNORE INTO migration_log 
            (migration_name, migration_version, status) 
            VALUES (?, ?, ?)
        """, ("initial_schema", SCHEMA_VERSION, "completed"))
    
    logger.info(f"Database initialized at {DATABASE_PATH}")


def get_db_version() -> int:
    """Get the current database schema version."""
    with get_connection() as db:
        result = db.execute("""
            SELECT migration_version FROM migration_log 
            WHERE migration_name = 'initial_schema'
            ORDER BY migration_version DESC LIMIT 1
        """).fetchone()
        return result['migration_version'] if result else 0


# ============ User Operations ============

def create_user(email: str, password_hash: Optional[str] = None, 
                theme: str = 'dark', personality: str = 'default',
                tier: str = 'free') -> int:
    """
    Create a new user.
    
    Args:
        email: User's email address (unique)
        password_hash: Optional password hash
        theme: UI theme preference
        personality: AI personality preference
        tier: User tier (free, premium, etc.)
    
    Returns:
        int: The new user's ID
    
    Raises:
        DatabaseError: If user creation fails
    """
    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO users (email, password_hash, theme, personality, tier)
            VALUES (?, ?, ?, ?, ?)
        """, (email, password_hash, theme, personality, tier))
        return cursor.lastrowid


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by email address.
    
    Args:
        email: User's email address
    
    Returns:
        dict: User data or None if not found
    """
    with get_connection() as db:
        result = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(result) if result else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID.
    
    Args:
        user_id: User's database ID
    
    Returns:
        dict: User data or None if not found
    """
    with get_connection() as db:
        result = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(result) if result else None


def update_user(user_id: int, **kwargs) -> bool:
    """
    Update user data.
    
    Args:
        user_id: User's database ID
        **kwargs: Field-value pairs to update
    
    Returns:
        bool: True if update successful
    """
    allowed_fields = {'theme', 'personality', 'tier', 'image_usage_count', 
                      'image_usage_last_reset', 'upgrade_history', 'password_hash'}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    set_clause = ', '.join([f"{k} = ?" for k in updates])
    values = list(updates.values()) + [user_id]
    
    with get_connection() as db:
        db.execute(f"UPDATE users SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
    return True


def delete_user(user_id: int) -> bool:
    """
    Delete a user and all associated data.
    
    Args:
        user_id: User's database ID
    
    Returns:
        bool: True if deletion successful
    """
    with get_connection() as db:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return True


# ============ Session Operations ============

def create_session(user_id: int, session_id: str, name: str = 'New Chat') -> int:
    """
    Create a new chat session.
    
    Args:
        user_id: Owner's user ID
        session_id: Unique session identifier (UUID)
        name: Session name
    
    Returns:
        int: The new session's ID
    """
    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO sessions (user_id, session_id, name)
            VALUES (?, ?, ?)
        """, (user_id, session_id, name))
        return cursor.lastrowid


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a session by session_id.
    
    Args:
        session_id: Session's unique identifier
    
    Returns:
        dict: Session data or None if not found
    """
    with get_connection() as db:
        result = db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return dict(result) if result else None


def get_user_sessions(user_id: int) -> List[Dict[str, Any]]:
    """
    Get all sessions for a user.
    
    Args:
        user_id: User's database ID
    
    Returns:
        list: List of session dictionaries
    """
    with get_connection() as db:
        results = db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in results]


def update_session(session_id: str, **kwargs) -> bool:
    """
    Update session data.
    
    Args:
        session_id: Session's unique identifier
        **kwargs: Field-value pairs to update
    
    Returns:
        bool: True if update successful
    """
    allowed_fields = {'name'}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not updates:
        return False
    
    set_clause = ', '.join([f"{k} = ?" for k in updates])
    values = list(updates.values()) + [session_id]
    
    with get_connection() as db:
        db.execute(f"UPDATE sessions SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?", values)
    return True


def delete_session(session_id: str) -> bool:
    """
    Delete a session and all associated messages.
    
    Args:
        session_id: Session's unique identifier
    
    Returns:
        bool: True if deletion successful
    """
    with get_connection() as db:
        db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    return True


# ============ Message Operations ============

def add_message(session_id: str, content: str, sender: str, 
                time: str, metadata: Optional[Dict[str, Any]] = None) -> int:
    """
    Add a message to a session.
    
    Args:
        session_id: Session's unique identifier
        content: Message content
        sender: 'user' or 'bot'
        time: Message timestamp
        metadata: Optional additional message data
    
    Returns:
        int: The new message's ID
    """
    metadata_json = json.dumps(metadata) if metadata else None
    
    with get_connection() as db:
        cursor = db.execute("""
            INSERT INTO messages (session_id, content, sender, time, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, content, sender, time, metadata_json))
        return cursor.lastrowid


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all messages for a session.
    
    Args:
        session_id: Session's unique identifier
    
    Returns:
        list: List of message dictionaries
    """
    with get_connection() as db:
        results = db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        ).fetchall()
        return [dict(r) for r in results]


# ============ Rate Limit Operations ============

def get_rate_limit(identifier: str) -> Optional[Dict[str, Any]]:
    """
    Get rate limit data for an identifier.
    
    Args:
        identifier: IP address or user email
    
    Returns:
        dict: Rate limit data or None if not found
    """
    with get_connection() as db:
        result = db.execute(
            "SELECT * FROM rate_limits WHERE identifier = ?",
            (identifier,)
        ).fetchone()
        return dict(result) if result else None


def set_rate_limit(identifier: str, limit_type: str, request_count: int, 
                   window_start: str) -> bool:
    """
    Set or update rate limit data.
    
    Args:
        identifier: IP address or user email
        limit_type: 'ip' or 'user'
        request_count: Number of requests in window
        window_start: Start of the rate limit window
    
    Returns:
        bool: True if successful
    """
    with get_connection() as db:
        db.execute("""
            INSERT OR REPLACE INTO rate_limits (identifier, limit_type, request_count, window_start)
            VALUES (?, ?, ?, ?)
        """, (identifier, limit_type, request_count, window_start))
    return True


def increment_rate_limit(identifier: str) -> int:
    """
    Increment request count for an identifier.
    
    Args:
        identifier: IP address or user email
    
    Returns:
        int: New request count
    """
    with get_connection() as db:
        db.execute("""
            UPDATE rate_limits 
            SET request_count = request_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE identifier = ?
        """, (identifier,))
        
        result = db.execute(
            "SELECT request_count FROM rate_limits WHERE identifier = ?",
            (identifier,)
        ).fetchone()
        return result['request_count'] if result else 0


# ============ Utility Functions ============

def user_exists(email: str) -> bool:
    """Check if a user exists by email."""
    with get_connection() as db:
        result = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        return result is not None


def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    with get_connection() as db:
        result = db.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return result is not None


def get_all_users() -> List[Dict[str, Any]]:
    """Get all users from the database."""
    with get_connection() as db:
        results = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in results]


def get_stats() -> Dict[str, int]:
    """Get database statistics."""
    with get_connection() as db:
        return {
            'user_count': db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            'session_count': db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            'message_count': db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
        }


if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    print(f"Database initialized at {DATABASE_PATH}")
    print(f"Current schema version: {get_db_version()}")
