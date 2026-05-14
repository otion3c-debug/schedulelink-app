from datetime import datetime
import logging
from fastapi import FastAPI, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import urllib.parse
from .config import settings
from .database import engine
from .routers import auth, users, calendars, availability, bookings, public, widget, subscriptions
from .database import Base, SessionLocal, get_db
from .models import User
from datetime import date
from . import models  # noqa: F401 — ensure all models are imported

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("schedulelink")

app = FastAPI(
    title="ScheduleLink API",
    version="2.0.0",
    description="Multi-calendar scheduling platform — backend API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)")
    return response


@app.get("/")
def root():
    return {"name": "ScheduleLink API", "version": "2.0.0", "status": "ok"}


@app.get("/health")
def health():
    db_ok = True
    db_error = None
    db_url_info = ""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        db_error = str(e)[:200]
        db_url_info = settings.DATABASE_URL[:50] + "..." if settings.DATABASE_URL.startswith("postgresql") else "sqlite"
        logger.error(f"Health check db error: {e}")
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "db_type": db_url_info,
        "error_hint": db_error,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.on_event("startup")
def on_startup():
    # Log which database we're using (without exposing full credentials)
    db_scheme = settings.DATABASE_URL.split("://")[0] if "://" in settings.DATABASE_URL else "unknown"
    db_host = ""
    if db_scheme == "postgresql":
        parsed = urllib.parse.urlparse(settings.DATABASE_URL)
        db_host = parsed.hostname or "unknown"
    logger.info(f"Starting with database: {db_scheme} at {db_host}")
    logger.info("Verifying database connection...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database connection OK, tables verified.")
    except Exception as e:
        logger.warning(f"Could not verify database on startup: {e}")
        logger.warning("App will start and attempt connections at runtime.")


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(calendars.router)
app.include_router(availability.router)
app.include_router(bookings.router)
app.include_router(public.router)
app.include_router(widget.router)
app.include_router(subscriptions.router)


@app.post("/admin/set-tier")
def admin_set_tier(email: str = Header(...), tier: str = Header(...), admin_key: str = Header(...), db=Depends(get_db)):
    if admin_key != "sl-admin-upgrade-2026":
        return {"ok": False, "error": "Unauthorized"}
    valid_tiers = {"free", "pro", "pro_plus"}
    if tier not in valid_tiers:
        return {"ok": False, "error": f"Invalid tier '{tier}'. Must be one of: {', '.join(valid_tiers)}"}
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"ok": False, "error": f"User with email '{email}' not found"}
    user.subscription_tier = tier
    user.subscription_status = "active"
    user.booking_limit = 999999 if tier in ("pro", "pro_plus") else 5
    if not user.billing_cycle_start:
        user.billing_cycle_start = date.today()
    db.commit()
    return {
        "ok": True,
        "email": user.email,
        "tier": user.subscription_tier,
        "status": user.subscription_status,
        "booking_limit": user.booking_limit,
    }
