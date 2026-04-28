# 📅 ScheduleLink v2.1.0

A production-ready scheduling SaaS platform — Calendly-style booking with:
- User registration and JWT authentication
- Public booking pages (no login required)
- Google Calendar integration
- Stripe subscription ($5/month)
- Email confirmations
- Double-booking prevention with database locking

## Quick Start

```bash
cd ~/Desktop/Otion/ScheduleLink
./START.sh
```

This will:
1. Create a Python virtual environment (first run only)
2. Initialize the SQLite database
3. Start the backend on port 8080
4. Start ngrok tunnel (if configured)
5. Open the app in your browser

## Public Booking Page

Once running, anyone can book meetings at:
```
http://localhost:8080/#/book/YOUR_USERNAME
```

Or with ngrok:
```
https://your-ngrok-url.ngrok.io/#/book/YOUR_USERNAME
```

**No login required for booking!**

## Features

### ✅ Implemented (MVP Complete)

1. **User Registration & Login** — JWT auth, secure password hashing
2. **Working Hours Configuration** — Set available hours per day
3. **Public Booking Page** — No auth required, shows next 14 days
4. **Slot Booking Flow** — Name, email, phone, notes
5. **Double-Booking Prevention** — Database-level transaction locking
6. **Email Confirmations** — Sent to both client AND host
7. **Admin Dashboard** — View all bookings
8. **Stripe Integration** — $5/month with 7-day free trial
9. **Google Calendar Integration** — OAuth2, auto-create events

### ✅ Polish Features

10. **Booking Cancellation** — Via link in email
11. **Timezone Display** — Shows host's timezone
12. **Booking Buffer** — Configurable gap between meetings
13. **Professional Email Templates** — Dark theme HTML emails

## Tech Stack

- **Backend:** Python 3.9+ / FastAPI / SQLite
- **Frontend:** Vanilla JS SPA
- **Auth:** JWT tokens (30-day expiry)
- **Payments:** Stripe Checkout
- **Calendar:** Google Calendar API (OAuth2)
- **Email:** Gmail SMTP

## Project Structure

```
ScheduleLink/
├── START.sh              # Start everything
├── STOP.sh               # Stop everything
├── README.md             # This file
├── backend/
│   ├── .env              # Environment variables (secrets)
│   ├── requirements.txt  # Python dependencies
│   ├── schedulelink.db   # SQLite database
│   ├── venv/             # Python virtual environment
│   └── app/
│       ├── __init__.py
│       ├── main.py       # FastAPI application
│       ├── database.py   # Database setup & connections
│       ├── models.py     # Pydantic request/response models
│       ├── auth.py       # JWT & password hashing
│       ├── calendar_api.py   # Google Calendar integration
│       ├── emailer.py    # Email sending via SMTP
│       └── stripe_api.py # Stripe payments
└── frontend/
    ├── index.html        # SPA entry point
    ├── styles.css        # Dark theme styling
    └── app.js            # Frontend application
```

## Configuration

All secrets are in `backend/.env`:

```env
# JWT Secret
JWT_SECRET=your-secret-key

# Google Calendar OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8080/api/auth/google/callback

# Email (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-name@domain.com

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_PRICE_ID=price_...

# URLs
BASE_URL=http://localhost:8080
FRONTEND_URL=http://localhost:8080
```

## ngrok Setup (For Public Access)

1. Sign up at [ngrok.com](https://ngrok.com) (free account)
2. Get your authtoken from the dashboard
3. Configure ngrok:
   ```bash
   ngrok config add-authtoken YOUR_TOKEN
   ```
4. Restart ScheduleLink — it will auto-detect ngrok

## API Documentation

When running, visit:
- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

### Key Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/auth/register` | No | Register new user |
| `POST /api/auth/login` | No | Login |
| `GET /api/auth/me` | Yes | Get current user |
| `GET /api/public/{username}` | No | Public profile |
| `GET /api/public/{username}/availability` | No | Available slots |
| `POST /api/public/{username}/book` | No | Book a meeting |
| `GET /api/cancel/{token}` | No | Get booking for cancellation |
| `POST /api/cancel/{token}` | No | Cancel booking |
| `GET /api/bookings` | Yes | List user's bookings |
| `GET /api/working-hours` | Yes | Get working hours |
| `PUT /api/working-hours` | Yes | Update working hours |
| `PATCH /api/settings` | Yes | Update settings |
| `GET /api/billing/checkout` | Yes | Start Stripe checkout |

## Double-Booking Prevention

The booking endpoint uses SQLite's `BEGIN IMMEDIATE` transaction mode to acquire a RESERVED lock before checking for conflicts. This prevents race conditions when two users try to book the same slot simultaneously.

```python
db.execute("BEGIN IMMEDIATE")
# Check for conflicts
# Insert booking
db.execute("COMMIT")
```

## Development

### Manual Start
```bash
cd ~/Desktop/Otion/ScheduleLink/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

### Run Tests (future)
```bash
cd backend
pytest tests/
```

## Troubleshooting

### "Address already in use"
```bash
./STOP.sh
# or manually:
lsof -ti:8080 | xargs kill -9
```

### ngrok not working
1. Ensure ngrok is installed: `brew install ngrok`
2. Configure authtoken: `ngrok config add-authtoken YOUR_TOKEN`
3. Check status: `ngrok config check`

### Email not sending
1. Verify Gmail app password in `.env`
2. Check SMTP_USER and SMTP_PASSWORD
3. App passwords require 2FA enabled on Gmail

### Google Calendar not connecting
1. Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
2. Ensure redirect URI matches exactly
3. Check that Calendar API is enabled in Google Cloud Console

## License

Private — Otion LLC
