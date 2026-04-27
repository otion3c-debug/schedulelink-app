"""ScheduleLink FastAPI Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from .config import get_settings
from .database import init_database
from .routes import auth, users, bookings, public, stripe_, google
from .scheduler import start_scheduler, stop_scheduler

# Initialize database
init_database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifespan - start/stop background services."""
    # Startup: Start the reminder scheduler
    start_scheduler()
    yield
    # Shutdown: Stop the scheduler
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title="ScheduleLink",
    description="Multi-tenant scheduling platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://schedulelink.tech",
        "https://www.schedulelink.tech",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(bookings.router)
app.include_router(public.router)
app.include_router(stripe_.router)
app.include_router(google.router)

# Serve frontend static files
FRONTEND_PATH = Path(__file__).parent.parent.parent / "frontend"


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ScheduleLink"}


@app.get("/api/config")
async def get_public_config():
    """Get public configuration for frontend."""
    settings = get_settings()
    return {
        "stripe_publishable_key": settings.stripe_publishable_key,
        "app_name": settings.app_name
    }


# Serve frontend
@app.get("/")
async def serve_index():
    """Serve main SPA."""
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/book/{username}")
async def serve_booking_page(username: str):
    """Serve public booking page."""
    return FileResponse(FRONTEND_PATH / "book.html")


@app.get("/{path:path}")
async def serve_static(path: str):
    """Serve static files or fallback to SPA.
    
    NOTE: API routes are handled by included routers.
    This catch-all should NOT intercept /api/* paths.
    """
    # Never intercept API routes - let them 404 properly if not found
    if path.startswith("api/") or path.startswith("api"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"detail": f"API endpoint not found: /{path}"}
        )
    
    file_path = FRONTEND_PATH / path
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # Fallback to index.html for SPA routing (for frontend routes only)
    return FileResponse(FRONTEND_PATH / "index.html")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
