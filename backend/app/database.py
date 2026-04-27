"""Database initialization and connection management.

Supports both PostgreSQL (production with Supabase) and SQLite (local development).
Set DATABASE_URL environment variable to your PostgreSQL connection string.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Dict, Any

# Determine database type from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool
    
    # Fix for URLs that start with postgres:// instead of postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    _pool: Optional[pool.ThreadedConnectionPool] = None
    
    def _get_pool():
        global _pool
        if _pool is None:
            _pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        return _pool
else:
    import sqlite3
    DATABASE_PATH = Path(__file__).parent.parent / "schedulelink.db"


# SQL Schema - SQLite version
SQLITE_SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    timezone TEXT DEFAULT 'America/New_York',
    meeting_duration INTEGER DEFAULT 30,
    buffer_minutes INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    subscription_status TEXT DEFAULT 'free',
    trial_end DATETIME,
    google_refresh_token TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Working hours per user
CREATE TABLE IF NOT EXISTS working_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,
    enabled INTEGER DEFAULT 0,
    start_time TEXT DEFAULT '09:00',
    end_time TEXT DEFAULT '17:00',
    UNIQUE(user_id, day_of_week)
);

-- Bookings
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    client_name TEXT NOT NULL,
    client_email TEXT NOT NULL,
    client_phone TEXT,
    client_notes TEXT,
    booking_time DATETIME NOT NULL,
    duration INTEGER NOT NULL,
    status TEXT DEFAULT 'confirmed',
    google_event_id TEXT,
    cancellation_token TEXT UNIQUE,
    reminder_24h_sent INTEGER DEFAULT 0,
    reminder_1h_sent INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Google tokens (per user)
CREATE TABLE IF NOT EXISTS google_tokens (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry DATETIME
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    used INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bookings_host_id ON bookings(host_id);
CREATE INDEX IF NOT EXISTS idx_bookings_time ON bookings(booking_time);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_working_hours_user ON working_hours(user_id);
"""


def init_database():
    """Initialize the database with schema."""
    if USE_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres():
    """Initialize PostgreSQL database."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                timezone TEXT DEFAULT 'America/New_York',
                meeting_duration INTEGER DEFAULT 30,
                buffer_minutes INTEGER DEFAULT 0,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                subscription_status TEXT DEFAULT 'free',
                trial_end TIMESTAMP,
                google_refresh_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Working hours table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS working_hours (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                day_of_week INTEGER NOT NULL,
                enabled INTEGER DEFAULT 0,
                start_time TEXT DEFAULT '09:00',
                end_time TEXT DEFAULT '17:00',
                UNIQUE(user_id, day_of_week)
            )
        """)
        
        # Bookings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                host_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                client_name TEXT NOT NULL,
                client_email TEXT NOT NULL,
                client_phone TEXT,
                client_notes TEXT,
                booking_time TIMESTAMP NOT NULL,
                duration INTEGER NOT NULL,
                status TEXT DEFAULT 'confirmed',
                google_event_id TEXT,
                cancellation_token TEXT UNIQUE,
                reminder_24h_sent INTEGER DEFAULT 0,
                reminder_1h_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Google tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS google_tokens (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                access_token TEXT,
                refresh_token TEXT,
                token_expiry TIMESTAMP
            )
        """)
        
        # Password reset tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_host_id ON bookings(host_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_time ON bookings(booking_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_working_hours_user ON working_hours(user_id)")
        
        conn.commit()
        print("[Database] PostgreSQL initialized successfully")
    except Exception as e:
        conn.rollback()
        print(f"[Database] Error initializing PostgreSQL: {e}")
        raise
    finally:
        pool.putconn(conn)


def _init_sqlite():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript(SQLITE_SCHEMA)
    conn.commit()
    
    # Migration: Add reminder columns if they don't exist
    try:
        conn.execute("ALTER TABLE bookings ADD COLUMN reminder_24h_sent INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        conn.execute("ALTER TABLE bookings ADD COLUMN reminder_1h_sent INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.close()
    print("[Database] SQLite initialized successfully")


class PostgresConnection:
    """Wrapper to provide sqlite3-like interface for PostgreSQL."""
    
    def __init__(self, conn, pool_ref):
        self._conn = conn
        self._pool = pool_ref
        self._cursor = None
    
    def execute(self, query: str, params: tuple = ()):
        """Execute a query, converting ? placeholders to %s."""
        # Convert SQLite placeholders to PostgreSQL
        pg_query = query.replace("?", "%s")
        cursor = self._conn.cursor()
        cursor.execute(pg_query, params)
        self._cursor = cursor
        return PostgresCursor(cursor)
    
    def executescript(self, script: str):
        """Execute multiple statements (for compatibility)."""
        cursor = self._conn.cursor()
        cursor.execute(script)
        self._conn.commit()
    
    def commit(self):
        self._conn.commit()
    
    def rollback(self):
        self._conn.rollback()
    
    def close(self):
        if self._pool:
            self._pool.putconn(self._conn)
    
    @property
    def row_factory(self):
        return None  # Not used for PostgreSQL (RealDictCursor handles this)
    
    @row_factory.setter
    def row_factory(self, value):
        pass  # Ignore for PostgreSQL


class PostgresCursor:
    """Wrapper for PostgreSQL cursor results."""
    
    def __init__(self, cursor):
        self._cursor = cursor
    
    def fetchone(self):
        return self._cursor.fetchone()
    
    def fetchall(self):
        return self._cursor.fetchall()
    
    @property
    def lastrowid(self):
        # For PostgreSQL, use RETURNING in the query instead
        return None
    
    @property
    def rowcount(self):
        return self._cursor.rowcount


@contextmanager
def get_db() -> Generator[Any, None, None]:
    """Get database connection context manager."""
    if USE_POSTGRES:
        pool = _get_pool()
        conn = pool.getconn()
        wrapper = PostgresConnection(conn, pool)
        try:
            yield wrapper
        finally:
            wrapper.close()
    else:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()


def _serialize_datetime(value: Any) -> Any:
    """Convert datetime objects to ISO format strings for JSON serialization."""
    from datetime import datetime, date
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def dict_from_row(row: Optional[Any]) -> Optional[Dict[str, Any]]:
    """Convert database row to dict, with datetime serialization."""
    if row is None:
        return None
    if USE_POSTGRES:
        # RealDictCursor already returns dict-like objects
        # Convert datetime fields to strings for Pydantic compatibility
        if row:
            return {k: _serialize_datetime(v) for k, v in dict(row).items()}
        return None
    return dict(row)


def seed_working_hours(user_id: int, conn):
    """Seed default working hours for a new user (Mon-Fri 9-5)."""
    for day in range(7):
        enabled = 1 if day < 5 else 0  # Mon-Fri enabled
        if USE_POSTGRES:
            conn.execute(
                """
                INSERT INTO working_hours (user_id, day_of_week, enabled, start_time, end_time)
                VALUES (%s, %s, %s, '09:00', '17:00')
                ON CONFLICT (user_id, day_of_week) DO NOTHING
                """,
                (user_id, day, enabled)
            )
        else:
            conn.execute(
                """
                INSERT OR IGNORE INTO working_hours (user_id, day_of_week, enabled, start_time, end_time)
                VALUES (?, ?, ?, '09:00', '17:00')
                """,
                (user_id, day, enabled)
            )


def insert_returning_id(conn, table: str, columns: list, values: tuple) -> int:
    """Insert a row and return the new ID. Works for both PostgreSQL and SQLite."""
    placeholders = ", ".join(["%s" if USE_POSTGRES else "?" for _ in values])
    col_names = ", ".join(columns)
    
    if USE_POSTGRES:
        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) RETURNING id"
        cursor = conn.execute(query, values)
        return cursor.fetchone()["id"]
    else:
        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        cursor = conn.execute(query, values)
        return cursor.lastrowid


# FastAPI dependency for database session
def get_db_dependency():
    """FastAPI dependency that provides a database connection.
    
    This is a generator-based dependency that FastAPI handles properly.
    """
    yield from get_db()


# Initialize database on module import
init_database()
