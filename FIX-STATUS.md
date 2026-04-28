# ScheduleLink Fix Status Report

**Date:** 2026-04-25  
**Issues:** Database persistence + Google OAuth 403

---

## ✅ Issue 1: Database Wiped on Every Redeploy — CODE PUSHED TO GITHUB

### Problem
SQLite database stored on Render's ephemeral filesystem. Every redeploy wipes all user accounts and bookings.

### Solution Implemented
Updated backend code to support **PostgreSQL (Supabase)** while maintaining SQLite fallback for local dev.

**Code pushed to:** https://github.com/otion3c-debug/schedulelink-app  
**Commit:** `feat: Add PostgreSQL (Supabase) support for persistent database`

**Files Modified:**
- `backend/app/database.py` — Dual PostgreSQL/SQLite support with connection pooling
- `backend/app/routes/auth.py` — Updated to use `insert_returning_id` helper
- `backend/app/routes/public.py` — Updated booking creation for PostgreSQL
- `backend/requirements.txt` — Added `psycopg2-binary>=2.9.9`
- `DEPLOY-MANUAL-FIXES.md` — Step-by-step setup instructions

**How It Works:**
- If `DATABASE_URL` env var starts with `postgresql://`, uses PostgreSQL
- Otherwise falls back to SQLite (local development)
- Connection pooling for PostgreSQL performance
- Helper function handles PostgreSQL's `RETURNING` vs SQLite's `lastrowid`

### ⚠️ Manual Steps Required

**You still need to:**
1. Create a free Supabase account at https://supabase.com
2. Create a new project
3. Get the PostgreSQL connection string
4. Add `DATABASE_URL` environment variable in Render dashboard

**Full instructions:** See `DEPLOY-MANUAL-FIXES.md` in this folder AND in the GitHub repo

---

## ⚠️ Issue 2: Google OAuth 403 — Requires Manual Config

### Problem
- `api.schedulelink.tech` CNAME points to Render
- But Render doesn't accept traffic for custom domains not configured in its dashboard
- Google OAuth redirects fail

### Solution
This requires Render dashboard access — no API key available.

### Manual Steps Required

1. **Add custom domain in Render:**
   - Render Dashboard → schedulelink-app → Settings → Custom Domains
   - Add `api.schedulelink.tech`
   - Wait for DNS verification

2. **Update Render environment variables:**
   - `GOOGLE_REDIRECT_URI` = `https://api.schedulelink.tech/api/google/callback`
   - `BASE_URL` = `https://api.schedulelink.tech`

3. **Update Google Cloud Console:**
   - Add `https://api.schedulelink.tech/api/google/callback` to authorized redirect URIs

**Full instructions:** See `DEPLOY-MANUAL-FIXES.md` Part 2

---

## What Happens Next

1. **Render should auto-deploy** from the GitHub push (check render.com dashboard)
2. **You set up Supabase** (free, 5 min) and add the DATABASE_URL
3. **You configure the custom domain** in Render (5 min)
4. **Test everything** - register, login, book meetings

---

## Test Steps (After Manual Config)

### Test 1: Database Persistence
1. Go to https://schedulelink.tech/app.html
2. Register a new account
3. Note your username
4. In Render dashboard, manually trigger a redeploy
5. After redeploy, go back and log in
6. **Expected:** Your account still exists!

### Test 2: Google Calendar
1. Log into ScheduleLink
2. Go to Settings → Google Calendar
3. Click "Connect Google Calendar"
4. Authorize in Google's popup
5. **Expected:** Redirected back to settings with "Connected" status

### Test 3: End-to-End Booking
1. Share your booking page: `https://schedulelink.tech/app.html#/book/[username]`
2. Book a meeting as a client
3. **Expected:** 
   - Booking appears in dashboard
   - Event appears in Google Calendar
   - Confirmation emails sent

---

## Quick Reference: Environment Variables for Render

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Supabase PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | Your Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Your Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `https://api.schedulelink.tech/api/google/callback` |
| `BASE_URL` or `APP_URL` | `https://api.schedulelink.tech` |
| `FRONTEND_URL` | `https://schedulelink.tech` |

---

## Summary

| Item | Status |
|------|--------|
| Code changes | ✅ Pushed to GitHub |
| Render auto-deploy | 🔄 Should trigger automatically |
| Supabase setup | ❌ Manual action needed |
| DATABASE_URL in Render | ❌ Manual action needed |
| Custom domain in Render | ❌ Manual action needed |
| Google OAuth redirect URI | ❌ Manual action needed |

**Estimated time for manual steps:** 15-20 minutes

All instructions are in `DEPLOY-MANUAL-FIXES.md`.
