from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
import urllib.parse
import logging

logger = logging.getLogger("schedulelink.db")

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    connect_args = {"check_same_thread": False}
    pool_kwargs = {}
    database_url = settings.DATABASE_URL
else:
    # URL-encode the password to handle special characters (!, @, #, etc.)
    parsed = urllib.parse.urlparse(settings.DATABASE_URL)
    if parsed.password:
        # Rebuild the URL with properly encoded password
        encoded_password = urllib.parse.quote(parsed.password, safe="")
        netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        database_url = urllib.parse.ParseResult(
            parsed.scheme, netloc, parsed.path,
            parsed.params, parsed.query, parsed.fragment
        ).geturl()
        logger.info(f"Using PostgreSQL at {parsed.hostname}:{parsed.port}")
    else:
        database_url = settings.DATABASE_URL

    connect_args = {
        "sslmode": "require",
        "connect_timeout": 15,
    }
    pool_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
    }

engine = create_engine(
    database_url,
    connect_args=connect_args,
    future=True,
    **pool_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
