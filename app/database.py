from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if _is_sqlite else {}
pool_kwargs = {} if _is_sqlite else {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True, **pool_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
