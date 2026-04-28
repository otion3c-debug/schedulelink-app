"""ScheduleLink API - Main FastAPI Application."""
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

from .database import init_db, get_db_dependency, seed_working_hours
from .models import (
    UserCreate, UserLogin, UserResponse, Token,
    WorkingHoursUpdate, WorkingHoursResponse,
    BookingCreate, BookingResponse, AvailableSlot, DayAvailability,
    SettingsUpdate, PublicProfile
)
from .auth import (
    hash_password, verify_password, create_access_token, 
    get_current_user, get_optional_user
)
from . import calendar_api, emailer, stripe_api

app = FastAPI(title="ScheduleLink API", version="1.0.0")

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://192.168.1.145:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_URL = os.getenv("APP_URL", "http://localhost:3000")

@app.on_event("startup")
def startup():
    init_db()

# ============== Health Check ==============

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ScheduleLink"}

# ============== Authentication ==============

@app.post("/api/auth/register", response_model=Token)
def register(user: UserCreate, db: sqlite3.Connection = Depends(get_db_dependency)):
    # Check if email or username exists
    existing = db.execute(
        "SELECT id FROM users WHERE email = ? OR username = ?",
        (user.email, user.username)
    ).fetchone()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already registered")
    
    # Create user
    password_hash = hash_password(user.password)
    cursor = db.execute(
        """INSERT INTO users (email, password_hash, username, full_name)
           VALUES (?, ?, ?, ?)""",
        (user.email, password_hash, user.username, user.full_name)
    )
    user_id = cursor.lastrowid
    
    # Create default working hours
    seed_working_hours(user_id, db)
    
    # Generate token
    token = create_access_token({"sub": str(user_id)})
    return {"access_token": token}

@app.post("/api/auth/login", response_model=Token)
def login(credentials: UserLogin, db: sqlite3.Connection = Depends(get_db_dependency)):
    user = db.execute(
        "SELECT * FROM users WHERE email = ?", (credentials.email,)
    ).fetchone()
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user["id"])})
    return {"access_token": token}

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "timezone": current_user["timezone"],
        "meeting_duration": current_user["meeting_duration"],
        "buffer_time": current_user["buffer_time"],
        "is_paid": bool(current_user["is_paid"]),
        "google_connected": bool(current_user["google_access_token"])
    }

# ============== Google Calendar OAuth ==============

@app.get("/api/auth/google")
def google_auth_redirect(current_user: dict = Depends(get_current_user)):
    """Redirect to Google OAuth consent screen."""
    state = str(current_user["id"])
    auth_url = calendar_api.get_google_auth_url(state)
    return {"auth_url": auth_url}

@app.get("/api/auth/google/callback")
def google_auth_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """Handle Google OAuth callback."""
    try:
        tokens = calendar_api.exchange_code_for_tokens(code)
        
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Update user with tokens
        if state:
            db.execute(
                """UPDATE users SET 
                   google_access_token = ?, 
                   google_refresh_token = ?,
                   google_token_expiry = ?
                   WHERE id = ?""",
                (access_token, refresh_token, expiry.isoformat(), state)
            )
        
        # Redirect back to frontend
        return RedirectResponse(url=f"{APP_URL}/#/settings?google=connected")
    
    except Exception as e:
        return RedirectResponse(url=f"{APP_URL}/#/settings?google=error&message={str(e)}")

@app.post("/api/auth/google/disconnect")
def disconnect_google(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """Disconnect Google Calendar."""
    db.execute(
        """UPDATE users SET 
           google_access_token = NULL, 
           google_refresh_token = NULL,
           google_token_expiry = NULL
           WHERE id = ?""",
        (current_user["id"],)
    )
    return {"status": "disconnected"}

@app.get("/api/calendars")
def list_calendars(current_user: dict = Depends(get_current_user)):
    """List user's Google Calendars."""
    if not current_user["google_access_token"]:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    calendars = calendar_api.get_calendar_list(current_user["google_access_token"])
    return {"calendars": calendars}

# ============== Working Hours ==============

@app.get("/api/working-hours", response_model=List[WorkingHoursResponse])
def get_working_hours(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    rows = db.execute(
        "SELECT * FROM working_hours WHERE user_id = ? ORDER BY day_of_week",
        (current_user["id"],)
    ).fetchall()
    
    return [
        {
            "day_of_week": r["day_of_week"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "is_enabled": bool(r["is_enabled"])
        }
        for r in rows
    ]

@app.put("/api/working-hours")
def update_working_hours(
    hours: List[WorkingHoursUpdate],
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    for h in hours:
        db.execute(
            """INSERT OR REPLACE INTO working_hours 
               (user_id, day_of_week, start_time, end_time, is_enabled)
               VALUES (?, ?, ?, ?, ?)""",
            (current_user["id"], h.day_of_week, h.start_time, h.end_time, int(h.is_enabled))
        )
    return {"status": "updated"}

# ============== Settings ==============

@app.patch("/api/settings")
def update_settings(
    settings: SettingsUpdate,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    updates = []
    values = []
    
    if settings.full_name is not None:
        updates.append("full_name = ?")
        values.append(settings.full_name)
    if settings.timezone is not None:
        updates.append("timezone = ?")
        values.append(settings.timezone)
    if settings.meeting_duration is not None:
        updates.append("meeting_duration = ?")
        values.append(settings.meeting_duration)
    if settings.buffer_time is not None:
        updates.append("buffer_time = ?")
        values.append(settings.buffer_time)
    if settings.google_calendar_id is not None:
        updates.append("google_calendar_id = ?")
        values.append(settings.google_calendar_id)
    
    if updates:
        values.append(current_user["id"])
        db.execute(
            f"UPDATE users SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            values
        )
    
    return {"status": "updated"}

# ============== Availability (Public) ==============

def get_user_access_token(user: dict, db: sqlite3.Connection) -> Optional[str]:
    """Get valid access token, refreshing if needed."""
    if not user["google_access_token"]:
        return None
    
    # Check if token expired
    if user["google_token_expiry"]:
        expiry = datetime.fromisoformat(user["google_token_expiry"])
        if datetime.utcnow() > expiry - timedelta(minutes=5):
            # Refresh token
            if user["google_refresh_token"]:
                try:
                    tokens = calendar_api.refresh_access_token(user["google_refresh_token"])
                    new_token = tokens.get("access_token")
                    expires_in = tokens.get("expires_in", 3600)
                    new_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    db.execute(
                        """UPDATE users SET google_access_token = ?, google_token_expiry = ?
                           WHERE id = ?""",
                        (new_token, new_expiry.isoformat(), user["id"])
                    )
                    return new_token
                except:
                    return None
    
    return user["google_access_token"]

@app.get("/api/public/{username}")
def get_public_profile(username: str, db: sqlite3.Connection = Depends(get_db_dependency)):
    """Get public booking profile."""
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user["username"],
        "full_name": user["full_name"],
        "meeting_duration": user["meeting_duration"],
        "timezone": user["timezone"]
    }

@app.get("/api/public/{username}/availability")
def get_availability(
    username: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """Get available time slots for a date range."""
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = dict(user)
    
    # Get working hours
    working_hours = db.execute(
        "SELECT * FROM working_hours WHERE user_id = ?", (user["id"],)
    ).fetchall()
    
    wh_by_day = {r["day_of_week"]: dict(r) for r in working_hours}
    
    # Get existing bookings
    existing_bookings = db.execute(
        """SELECT start_time, end_time FROM bookings 
           WHERE user_id = ? AND status = 'confirmed'
           AND date(start_time) BETWEEN ? AND ?""",
        (user["id"], start_date, end_date)
    ).fetchall()
    
    busy_times = [(b["start_time"], b["end_time"]) for b in existing_bookings]
    
    # Get Google Calendar busy times
    access_token = get_user_access_token(user, db)
    if access_token:
        try:
            time_min = f"{start_date}T00:00:00Z"
            time_max = f"{end_date}T23:59:59Z"
            gcal_busy = calendar_api.get_freebusy(
                access_token, 
                user["google_calendar_id"] or "primary",
                time_min, 
                time_max
            )
            for period in gcal_busy:
                busy_times.append((period["start"], period["end"]))
        except:
            pass
    
    # Generate available slots
    meeting_duration = user["meeting_duration"]
    buffer_time = user["buffer_time"]
    
    availability = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current_date <= end:
        day_of_week = current_date.weekday()  # Monday = 0
        wh = wh_by_day.get(day_of_week)
        
        day_slots = []
        
        if wh and wh["is_enabled"]:
            # Parse working hours
            start_time = datetime.strptime(
                f"{current_date.strftime('%Y-%m-%d')} {wh['start_time']}", 
                "%Y-%m-%d %H:%M"
            )
            end_time = datetime.strptime(
                f"{current_date.strftime('%Y-%m-%d')} {wh['end_time']}", 
                "%Y-%m-%d %H:%M"
            )
            
            # Generate slots
            slot_start = start_time
            while slot_start + timedelta(minutes=meeting_duration) <= end_time:
                slot_end = slot_start + timedelta(minutes=meeting_duration)
                
                # Check if slot conflicts with busy times
                is_available = True
                slot_start_iso = slot_start.isoformat()
                slot_end_iso = slot_end.isoformat()
                
                for busy_start, busy_end in busy_times:
                    # Normalize busy times
                    busy_start_dt = datetime.fromisoformat(busy_start.replace("Z", "+00:00").replace("+00:00", ""))
                    busy_end_dt = datetime.fromisoformat(busy_end.replace("Z", "+00:00").replace("+00:00", ""))
                    
                    # Check overlap
                    if slot_start < busy_end_dt and slot_end > busy_start_dt:
                        is_available = False
                        break
                
                # Don't allow booking in the past
                if slot_start < datetime.now():
                    is_available = False
                
                if is_available:
                    day_slots.append({
                        "start": slot_start_iso,
                        "end": slot_end_iso
                    })
                
                slot_start = slot_end + timedelta(minutes=buffer_time)
        
        availability.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "slots": day_slots
        })
        
        current_date += timedelta(days=1)
    
    return {"availability": availability}

# ============== Bookings ==============

@app.post("/api/public/{username}/book", response_model=BookingResponse)
def create_booking(
    username: str,
    booking: BookingCreate,
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """Create a new booking (public endpoint)."""
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = dict(user)
    
    # Calculate end time
    start_dt = datetime.fromisoformat(booking.start_time)
    end_dt = start_dt + timedelta(minutes=user["meeting_duration"])
    
    # Check for conflicting bookings (prevents double-booking)
    conflict = db.execute(
        """SELECT id FROM bookings
           WHERE user_id = ? AND status = 'confirmed'
           AND start_time < ? AND end_time > ?
           LIMIT 1""",
        (user["id"], end_dt.isoformat(), booking.start_time)
    ).fetchone()
    
    if conflict:
        raise HTTPException(
            status_code=409,
            detail="This time slot is no longer available. Please select another time."
        )
    
    # Insert booking
    cursor = db.execute(
        """INSERT INTO bookings (user_id, client_name, client_email, client_phone, start_time, end_time, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user["id"], booking.client_name, booking.client_email, booking.client_phone,
         booking.start_time, end_dt.isoformat(), booking.notes)
    )
    booking_id = cursor.lastrowid
    
    # Create Google Calendar event
    access_token = get_user_access_token(user, db)
    google_event_id = None
    if access_token:
        try:
            google_event_id = calendar_api.create_calendar_event(
                access_token,
                user["google_calendar_id"] or "primary",
                f"Meeting with {booking.client_name}",
                booking.start_time,
                end_dt.isoformat(),
                f"Booked via ScheduleLink\n\nClient: {booking.client_name}\nEmail: {booking.client_email}\n{f'Notes: {booking.notes}' if booking.notes else ''}",
                booking.client_email
            )
            if google_event_id:
                db.execute(
                    "UPDATE bookings SET google_event_id = ? WHERE id = ?",
                    (google_event_id, booking_id)
                )
        except Exception as e:
            print(f"Failed to create calendar event: {e}")
    
    # Send emails
    host_name = user["full_name"] or user["username"]
    formatted_time = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
    
    emailer.send_booking_confirmation_to_client(
        booking.client_email,
        booking.client_name,
        host_name,
        formatted_time,
        user["meeting_duration"],
        booking.notes or ""
    )
    
    emailer.send_booking_notification_to_host(
        user["email"],
        host_name,
        booking.client_name,
        booking.client_email,
        formatted_time,
        user["meeting_duration"],
        booking.notes or ""
    )
    
    return {
        "id": booking_id,
        "client_name": booking.client_name,
        "client_email": booking.client_email,
        "client_phone": booking.client_phone,
        "start_time": booking.start_time,
        "end_time": end_dt.isoformat(),
        "notes": booking.notes,
        "status": "confirmed",
        "created_at": datetime.now().isoformat()
    }

@app.get("/api/bookings", response_model=List[BookingResponse])
def list_bookings(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """List user's bookings."""
    query = "SELECT * FROM bookings WHERE user_id = ?"
    params = [current_user["id"]]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY start_time DESC"
    
    rows = db.execute(query, params).fetchall()
    
    return [
        {
            "id": r["id"],
            "client_name": r["client_name"],
            "client_email": r["client_email"],
            "client_phone": r["client_phone"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "notes": r["notes"],
            "status": r["status"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]

@app.get("/api/bookings/upcoming", response_model=List[BookingResponse])
def list_upcoming_bookings(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """List upcoming confirmed bookings."""
    now = datetime.now().isoformat()
    rows = db.execute(
        """SELECT * FROM bookings 
           WHERE user_id = ? AND status = 'confirmed' AND start_time > ?
           ORDER BY start_time ASC LIMIT 10""",
        (current_user["id"], now)
    ).fetchall()
    
    return [
        {
            "id": r["id"],
            "client_name": r["client_name"],
            "client_email": r["client_email"],
            "client_phone": r["client_phone"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "notes": r["notes"],
            "status": r["status"],
            "created_at": r["created_at"]
        }
        for r in rows
    ]

@app.delete("/api/bookings/{booking_id}")
def cancel_booking(
    booking_id: int,
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """Cancel a booking."""
    booking = db.execute(
        "SELECT * FROM bookings WHERE id = ? AND user_id = ?",
        (booking_id, current_user["id"])
    ).fetchone()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking = dict(booking)
    
    # Delete Google Calendar event
    if booking["google_event_id"]:
        access_token = get_user_access_token(dict(current_user), db)
        if access_token:
            calendar_api.delete_calendar_event(
                access_token,
                current_user["google_calendar_id"] or "primary",
                booking["google_event_id"]
            )
    
    # Update status
    db.execute(
        "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
        (booking_id,)
    )
    
    # Send cancellation emails
    start_dt = datetime.fromisoformat(booking["start_time"])
    formatted_time = start_dt.strftime("%A, %B %d, %Y at %I:%M %p")
    host_name = current_user["full_name"] or current_user["username"]
    
    emailer.send_booking_cancellation(
        booking["client_email"],
        booking["client_name"],
        host_name,
        formatted_time
    )
    
    return {"status": "cancelled"}

# ============== Stripe Billing ==============

@app.get("/api/billing/checkout")
def create_checkout(
    current_user: dict = Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db_dependency)
):
    """Create Stripe checkout session for paid tier."""
    if not stripe_api.is_stripe_configured():
        raise HTTPException(status_code=503, detail="Billing not configured")
    
    # Create or get customer
    customer_id = current_user["stripe_customer_id"]
    if not customer_id:
        customer_id = stripe_api.create_customer(
            current_user["email"],
            current_user["full_name"] or current_user["username"]
        )
        if customer_id:
            db.execute(
                "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                (customer_id, current_user["id"])
            )
    
    if not customer_id:
        raise HTTPException(status_code=500, detail="Failed to create customer")
    
    checkout_url = stripe_api.create_checkout_session(
        customer_id,
        f"{APP_URL}/#/settings?billing=success",
        f"{APP_URL}/#/settings?billing=cancelled"
    )
    
    if not checkout_url:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")
    
    return {"checkout_url": checkout_url}

@app.get("/api/billing/portal")
def billing_portal(
    current_user: dict = Depends(get_current_user)
):
    """Get Stripe billing portal URL."""
    if not current_user["stripe_customer_id"]:
        raise HTTPException(status_code=400, detail="No billing account")
    
    portal_url = stripe_api.create_billing_portal_session(
        current_user["stripe_customer_id"],
        f"{APP_URL}/#/settings"
    )
    
    if not portal_url:
        raise HTTPException(status_code=500, detail="Failed to create portal session")
    
    return {"portal_url": portal_url}

@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request, db: sqlite3.Connection = Depends(get_db_dependency)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    event = stripe_api.verify_webhook_signature(payload, sig_header)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        
        if customer_id and subscription_id:
            db.execute(
                """UPDATE users SET is_paid = 1, stripe_subscription_id = ?
                   WHERE stripe_customer_id = ?""",
                (subscription_id, customer_id)
            )
    
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        if customer_id:
            db.execute(
                "UPDATE users SET is_paid = 0, stripe_subscription_id = NULL WHERE stripe_customer_id = ?",
                (customer_id,)
            )
    
    return {"received": True}

# ============== Serve Frontend (SPA) ==============
import os
from fastapi.staticfiles import StaticFiles

frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

# ============== Run ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
