# ScheduleLink Deployment Guide

## Quick Start (Local Development)

```bash
cd schedulelink/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (already done - edit .env if needed)
cp .env.example .env

# Start the server
./START.sh
# OR: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Open http://localhost:8080 in your browser.

---

## Production Deployment: Railway

Railway is the easiest path to production. $5/mo hobby plan includes everything you need.

### Step 1: Prepare Repository

1. Create a new GitHub repository (private recommended)
2. Push the schedulelink folder:
   ```bash
   cd schedulelink
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin git@github.com:YOUR_USERNAME/schedulelink.git
   git push -u origin main
   ```

### Step 2: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your schedulelink repository
4. Railway will auto-detect Python

### Step 3: Configure Build

Create `railway.toml` in your project root:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 100

[build.env]
NIXPACKS_PYTHON_VERSION = "3.12"
```

Or use a `Procfile` in the backend folder:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 4: Set Environment Variables

In Railway dashboard → Variables, add:

```
APP_URL=https://your-app.railway.app
SECRET_KEY=generate-a-secure-random-string
JWT_SECRET=generate-another-secure-random-string
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_PRICE_ID=price_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REDIRECT_URI=https://your-app.railway.app/api/google/callback
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=ScheduleLink <noreply@yourdomain.com>
```

### Step 5: Custom Domain (Optional)

1. In Railway → Settings → Domains
2. Add your custom domain
3. Update DNS with the provided CNAME record
4. Update `APP_URL` and `GOOGLE_REDIRECT_URI` environment variables

### Step 6: Configure Stripe Webhook

1. In Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-app.railway.app/api/stripe/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy webhook signing secret to `STRIPE_WEBHOOK_SECRET`

### Step 7: Update Google OAuth

1. In Google Cloud Console → APIs & Services → Credentials
2. Edit your OAuth client
3. Add authorized redirect URI: `https://your-app.railway.app/api/google/callback`

---

## Alternative: Render

Similar to Railway, slightly cheaper free tier but slower cold starts.

1. Create account at [render.com](https://render.com)
2. New → Web Service → Connect GitHub repo
3. Build Command: `cd backend && pip install -r requirements.txt`
4. Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables in dashboard

---

## Alternative: DigitalOcean App Platform

1. Create account at [digitalocean.com](https://digitalocean.com)
2. Create App → GitHub → Select repo
3. Configure as Python app
4. Set environment variables
5. Deploy

---

## Database Migration (Production)

For production scale, consider switching to PostgreSQL:

1. Add PostgreSQL addon in Railway/Render
2. Update `DATABASE_URL` environment variable
3. Update `database.py` to use PostgreSQL (asyncpg or psycopg2)

The schema is SQLite-compatible, so migration is straightforward.

---

## SSL/HTTPS

Railway, Render, and DigitalOcean all provide automatic SSL certificates. No configuration needed.

---

## Monitoring

- Railway: Built-in logs and metrics
- Render: Built-in logs
- Consider adding Sentry for error tracking:
  ```python
  import sentry_sdk
  sentry_sdk.init(dsn="your-sentry-dsn")
  ```

---

## Scaling

The app is designed to scale horizontally:

- Stateless design (JWT auth, no session storage)
- Database is the only shared state
- For high traffic: add PostgreSQL, Redis for caching

---

## Security Checklist

- [ ] Generate new SECRET_KEY and JWT_SECRET for production
- [ ] Use Stripe live keys (not test keys)
- [ ] Enable Stripe webhook signature verification
- [ ] Set up proper CORS origins (update in main.py)
- [ ] Use Gmail app password (not account password)
- [ ] Consider rate limiting for public endpoints
