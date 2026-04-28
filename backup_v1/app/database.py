"""SQLite database setup and connection management with proper transaction support."""
import sqlite3
import os
from contextlib import contextmanager
from typing import Generator

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "..", "schedulelink.db")

def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_db_dependency() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            timezone TEXT DEFAULT 'America/New_York',
            meeting_duration INTEGER DEFAULT 30,
            buffer_time INTEGER DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            google_access_token TEXT,
            google_refresh_token TEXT,
            google_token_expiry TEXT,
            google_calendar_id TEXT DEFAULT 'primary',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Working hours table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS working_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, day_of_week)
        )
    """)
    
    # Bookings table with indexes for conflict checking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT NOT NULL,
            client_phone TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'confirmed',
            google_event_id TEXT,
            cancellation_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    # Create index for faster conflict checking
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_user_time 
        ON bookings(user_id, start_time, end_time, status)
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def seed_working_hours(user_id: int, db: sqlite3.Connection = None):
    """Create default working hours for a new user (Mon-Fri 9AM-5PM)."""
    if db is None:
        conn = get_connection()
        own_connection = True
    else:
        conn = db
        own_connection = False
    
    cursor = conn.cursor()
    
    # Days 0-6 = Monday-Sunday
    for day in range(7):
        is_enabled = 1 if day < 5 else 0  # Mon-Fri enabled
        cursor.execute("""
            INSERT OR IGNORE INTO working_hours (user_id, day_of_week, start_time, end_time, is_enabled)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, day, "09:00", "17:00", is_enabled))
    
    if own_connection:
        conn.commit()
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database setup complete!")
