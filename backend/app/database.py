"""Database initialization and connection management."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Dict, Any, Union

DATABASE_PATH = Path(__file__).parent.parent / "schedulelink.db"

SCHEMA = """
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bookings_host_id ON bookings(host_id);
CREATE INDEX IF NOT EXISTS idx_bookings_time ON bookings(booking_time);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_working_hours_user ON working_hours(user_id);
"""


def init_database():
    """Initialize the database with schema."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.executescript(SCHEMA)
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


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection context manager."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Convert sqlite3.Row to dict."""
    if row is None:
        return None
    return dict(row)


def seed_working_hours(user_id: int, conn: sqlite3.Connection):
    """Seed default working hours for a new user (Mon-Fri 9-5)."""
    for day in range(7):
        enabled = 1 if day < 5 else 0  # Mon-Fri enabled
        conn.execute(
            """
            INSERT INTO working_hours (user_id, day_of_week, enabled, start_time, end_time)
            VALUES (?, ?, ?, '09:00', '17:00')
            """,
            (user_id, day, enabled)
        )


# Initialize database on module import
init_database()
