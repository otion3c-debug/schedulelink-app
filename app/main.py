from datetime import datetime
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from .config import settings
from .database import engine
from .routers import auth, users, calendars, availability, bookings, public, widget, subscriptions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("schedulelink")

app = FastAPI(
    title="ScheduleLink API",
    version="2.0.0",
    description="Multi-calendar scheduling platform — backend API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "*"],
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
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_ok = False
        logger.error(f"Health check db error: {e}")
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "timestamp": datetime.utcnow().isoformat(),
    }


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(calendars.router)
app.include_router(availability.router)
app.include_router(bookings.router)
app.include_router(public.router)
app.include_router(widget.router)
app.include_router(subscriptions.router)
