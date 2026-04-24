# ScheduleLink

A multi-tenant SaaS scheduling platform — like Calendly, but yours.

## Features

- **Multi-tenant Architecture**: Each user gets their own booking page at `/book/{username}`
- **Smart Availability**: Configure working hours per day, automatic slot calculation
- **Double-booking Prevention**: Database-level conflict detection
- **Email Notifications**: Confirmation emails to both host and client
- **Google Calendar Sync**: OAuth2 integration, automatic event creation
- **Stripe Billing**: Free tier (3 bookings/month) + $5/mo Pro subscription
- **Professional UI**: Dark-themed, mobile-responsive design

## Quick Start

```bash
cd backend
./START.sh
```

Open http://localhost:8080

## Tech Stack

- **Backend**: Python + FastAPI + SQLite
- **Frontend**: Vanilla JavaScript SPA
- **Auth**: JWT-based authentication
- **Payments**: Stripe Checkout + Subscriptions
- **Email**: Gmail SMTP
- **Calendar**: Google Calendar API

## Project Structure

```
schedulelink/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── config.py        # Environment config
│   │   ├── database.py      # SQLite schema & connection
│   │   ├── models.py        # Pydantic models
│   │   ├── auth.py          # JWT + password utilities
│   │   ├── routes/          # API endpoints
│   │   │   ├── auth.py      # Register/login
│   │   │   ├── users.py     # Profile/settings
│   │   │   ├── bookings.py  # Booking management
│   │   │   ├── public.py    # Public booking API
│   │   │   ├── stripe_.py   # Payment handling
│   │   │   └── google.py    # Calendar OAuth
│   │   └── services/        # Business logic
│   │       ├── emailer.py   # Email sending
│   │       ├── calendar.py  # Google Calendar
│   │       └── stripe_.py   # Stripe utilities
│   ├── .env                 # Environment variables
│   ├── requirements.txt     # Python dependencies
│   └── START.sh            # Startup script
├── frontend/
│   ├── index.html          # SPA entry point
│   ├── app.js              # Main application logic
│   ├── styles.css          # Professional dark theme
│   └── book.html           # Public booking page
├── DEPLOY.md               # Deployment guide
└── README.md               # This file
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Get current user

### User Settings
- `GET /api/users/me` - Get profile
- `PUT /api/users/me` - Update profile
- `GET /api/users/working-hours` - Get availability
- `PUT /api/users/working-hours` - Set availability

### Public Booking (No Auth)
- `GET /api/public/{username}` - Get host info
- `GET /api/public/{username}/availability?date=YYYY-MM-DD` - Get time slots
- `POST /api/public/{username}/book` - Create booking

### Bookings
- `GET /api/bookings` - List user's bookings
- `DELETE /api/bookings/{id}` - Cancel booking
- `GET /api/bookings/cancel/{token}` - Cancel via email link

### Stripe
- `POST /api/stripe/checkout` - Start subscription
- `POST /api/stripe/portal` - Billing management
- `POST /api/stripe/webhook` - Handle events
- `GET /api/stripe/status` - Check subscription

### Google
- `GET /api/google/auth` - Start OAuth flow
- `GET /api/google/callback` - OAuth callback
- `POST /api/google/disconnect` - Remove integration

## Environment Variables

| Variable | Description |
|----------|-------------|
| `APP_URL` | Application URL (e.g., https://schedulelink.com) |
| `SECRET_KEY` | App secret for security |
| `JWT_SECRET` | JWT signing key |
| `STRIPE_SECRET_KEY` | Stripe API secret |
| `STRIPE_PUBLISHABLE_KEY` | Stripe frontend key |
| `STRIPE_PRICE_ID` | Subscription price ID |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature secret |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL |
| `SMTP_HOST` | Email server host |
| `SMTP_PORT` | Email server port |
| `SMTP_USER` | Email username |
| `SMTP_PASSWORD` | Email app password |
| `EMAIL_FROM` | From address |

## Free vs Pro

| Feature | Free | Pro ($5/mo) |
|---------|------|-------------|
| Bookings per month | 3 | Unlimited |
| Custom booking page | ✓ | ✓ |
| Email notifications | ✓ | ✓ |
| Google Calendar sync | ✓ | ✓ |
| Working hours config | ✓ | ✓ |

## License

MIT
