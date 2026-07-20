from datetime import datetime
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import urllib.parse
from .config import settings
from .database import engine
from .routers import auth, users, calendars, availability, bookings, public, widget, subscriptions, vapi_webhook
from .database import Base
from . import models  # noqa: F401 — ensure all models are imported
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models.user import User
from .models import WidgetCustomization
from .utils import generate_unique_slug
import uuid
from datetime import date

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

    # Create internal Pro+ account for eric@otion.solutions if not exists
    try:
        db = SessionLocal()
        # Upgrade ANY user with email eric@otion.solutions to Pro+
        any_user = db.query(User).filter(User.email == "eric@otion.solutions").first()
        if any_user:
            any_user.subscription_tier = "pro_plus"
            any_user.subscription_status = "active"
            any_user.booking_limit = 9999
            # Delete all other users with same email
            others = db.query(User).filter(
                User.email == "eric@otion.solutions",
                User.id != any_user.id
            ).all()
            for o in others:
                db.delete(o)
            db.commit()
            logger.info(f"Upgraded {any_user.email} (id={any_user.id}, slug={any_user.booking_slug}) to Pro+")
        else:
            # No user exists yet - create one
            slug = "eric"
            new_user = User(
                id=uuid.uuid4(),
                email="eric@otion.solutions",
                full_name="Eric",
                timezone="America/New_York",
                subscription_tier="pro_plus",
                subscription_status="active",
                booking_slug=slug,
                booking_limit=9999,
                bookings_used_this_month=0,
                billing_cycle_start=date.today(),
            )
            db.add(new_user)
            db.flush()
            db.add(WidgetCustomization(user_id=new_user.id))
            db.commit()
            logger.info(f"Created Pro+ account for eric@otion.solutions (slug: {slug})")
        db.close()
    except Exception as e:
        logger.warning(f"Could not create internal account: {e}")


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(calendars.router)
app.include_router(availability.router)
app.include_router(bookings.router)
app.include_router(public.router)
app.include_router(widget.router)
app.include_router(subscriptions.router)
app.include_router(vapi_webhook.router)


@app.get("/demo-video")
async def demo_video():
    """Serve the OAuth demo video for Google verification."""
    video_path = Path(__file__).parent / "static" / "schedulelink-demo.mp4"
    if not video_path.exists():
        return JSONResponse({"error": "Video not found"}, status_code=404)
    from fastapi.responses import FileResponse
    return FileResponse(video_path, media_type="video/mp4")
