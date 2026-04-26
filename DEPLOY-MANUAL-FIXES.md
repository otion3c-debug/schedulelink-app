# ScheduleLink Deployment Manual Fixes

These steps must be done manually through web dashboards (no API access available).

---

## Part 1: Set Up Supabase Database (REQUIRED)

The SQLite database on Render gets wiped every deploy. You need persistent PostgreSQL.

### Step 1: Create Supabase Account & Project

1. Go to https://supabase.com
2. Click "Start your project" → Sign up (free tier, no credit card needed)
3. Create new project:
   - Name: `schedulelink` (or `schedulelink-prod`)
   - Database password: **Save this somewhere safe!**
   - Region: Choose closest to your users (e.g., `us-east-1`)
4. Wait 1-2 minutes for project to spin up

### Step 2: Get the Connection String

1. In Supabase dashboard → **Settings** (gear icon, left sidebar)
2. Go to **Database** section
3. Scroll to **Connection string** → click **URI** tab
4. You'll see something like:
   ```
   postgresql://postgres.[ref]:[YOUR-PASSWORD]@db.[ref].supabase.co:5432/postgres
   ```
5. **Replace** `[YOUR-PASSWORD]` with the database password you set
6. Copy the full connection string

### Step 3: Add DATABASE_URL to Render

1. Go to https://dashboard.render.com
2. Click on the **schedulelink-app** service
3. Go to **Environment** tab
4. Click **Add Environment Variable**
5. Add:
   - Key: `DATABASE_URL`
   - Value: Your Supabase connection string from Step 2
6. Click **Save Changes**
7. Render will auto-redeploy with the new variable

### Step 4: Verify It Works

After Render redeploys:
1. Go to https://schedulelink-app.onrender.com/api/health
2. Should return `{"status": "ok", ...}`
3. Try registering a new account at https://schedulelink.tech/app.html
4. Refresh the page - your account should still be there!

---

## Part 2: Fix Google OAuth Custom Domain

The Google OAuth redirect is failing because `api.schedulelink.tech` isn't configured as a custom domain in Render.

### Step 1: Add Custom Domain in Render

1. Go to https://dashboard.render.com
2. Click on the **schedulelink-app** service
3. Go to **Settings** tab
4. Scroll to **Custom Domains**
5. Click **Add Custom Domain**
6. Enter: `api.schedulelink.tech`
7. Render will show DNS instructions - these should already be set in Namecheap
8. Wait for Render to verify DNS and provision SSL (usually 2-10 minutes)
9. Status should change from "Pending" to "Verified"

### Step 2: Update Environment Variables in Render

Once the custom domain is verified:

1. Go to **Environment** tab in Render
2. Update these variables:
   - `GOOGLE_REDIRECT_URI` = `https://api.schedulelink.tech/api/google/callback`
   - `BASE_URL` = `https://api.schedulelink.tech`
   - `APP_URL` = `https://schedulelink.tech` (if not already set)
   - `FRONTEND_URL` = `https://schedulelink.tech`
3. Click **Save Changes** (Render will redeploy)

### Step 3: Update Google Cloud Console

1. Go to https://console.cloud.google.com
2. Select your project (the one with ScheduleLink OAuth)
3. Go to **APIs & Services** → **Credentials**
4. Click on your OAuth 2.0 Client ID
5. Under **Authorized redirect URIs**, add:
   ```
   https://api.schedulelink.tech/api/google/callback
   ```
6. You can optionally remove the old Render URL:
   ```
   https://schedulelink-app.onrender.com/api/google/callback
   ```
7. Click **Save**

### Step 4: Test Google Calendar Connection

1. Go to https://schedulelink.tech/app.html
2. Log in to your account
3. Go to Settings → Google Calendar
4. Click "Connect Google Calendar"
5. You should be redirected to Google's consent screen
6. After authorizing, you should return to ScheduleLink settings with "Connected" status

---

## Quick Reference: All Environment Variables for Render

Make sure these are all set correctly:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql://postgres.[ref]:[password]@db.[ref].supabase.co:5432/postgres` |
| `GOOGLE_CLIENT_ID` | Your Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `https://api.schedulelink.tech/api/google/callback` |
| `BASE_URL` | `https://api.schedulelink.tech` |
| `FRONTEND_URL` | `https://schedulelink.tech` |
| `JWT_SECRET` | A long random string (keep existing if set) |
| `STRIPE_SECRET_KEY` | Your Stripe secret key (if using billing) |
| `STRIPE_PUBLISHABLE_KEY` | Your Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Your Stripe webhook secret |
| `SENDGRID_API_KEY` | Your SendGrid key (for emails) |
| `EMAIL_FROM` | Email address for sending confirmations |

---

## Troubleshooting

### Database Still Wiped After Deploy?
- Check Render logs for `[Database] PostgreSQL initialized successfully`
- If you see `SQLite initialized`, the DATABASE_URL wasn't picked up
- Make sure the connection string starts with `postgresql://` not `postgres://`

### Google OAuth Returns 403?
- Verify the custom domain shows "Verified" in Render settings
- Check that the redirect URI matches EXACTLY (including https://)
- The redirect URI in Google Console must match the one in Render's GOOGLE_REDIRECT_URI

### Can't Connect to Supabase?
- Check if Supabase project is "Active" (not paused)
- Free tier pauses after 7 days of inactivity - reactivate in Supabase dashboard
- Verify the password in the connection string is correct

---

## DNS Reference (Already Set in Namecheap)

| Record Type | Host | Value |
|-------------|------|-------|
| A | @ | Vercel IP (for frontend) |
| CNAME | www | cname.vercel-dns.com |
| CNAME | api | schedulelink-app.onrender.com |

---

*Last updated: 2026-04-25*
