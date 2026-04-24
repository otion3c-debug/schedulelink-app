# ScheduleLink — Product Descriptions

---

## Short (App Store / Play Store Listing)

**Tagline:** Simple, clean scheduling. No back-and-forth.

**Description:**

Simple, clean scheduling that eliminates the email tag.

Share your booking link, clients pick a time that works for both of you, and everyone gets confirmed — automatically. No calls. No voicemails. No "does Tuesday at 3 work?" emails.

**Perfect for:**
- Consultants and coaches
- Small businesses and agencies
- Freelancers and contractors
- Anyone who books meetings

**Features:**
- Set your availability once
- Share your booking page
- Clients book in 30 seconds — no account needed
- Email confirmations for both sides
- Google Calendar sync
- Cancellation links
- Mobile-friendly booking page

**Pricing:** Free for 3 bookings/month. $5/month for unlimited.

---

## Medium (Website / Landing Page)

### What is ScheduleLink?

ScheduleLink is a scheduling platform that replaces the back-and-forth of booking meetings.

Instead of trading emails to find a time, you share a link. Your clients see when you're available and book in seconds. Everyone gets a confirmation. Done.

### How it works

1. **Set your hours** — Choose when you're available. Monday-Friday 9-5? Weekends only? Whatever works for you.

2. **Share your link** — Send your booking page to clients, put it in your email signature, add it to your website.

3. **Clients book** — They pick a time that works. No account needed on their end.

4. **Everyone's confirmed** — Email confirmations go to both of you instantly. Optional: add to Google Calendar automatically.

### Why ScheduleLink?

**Simple and clean.** No features you don't need. No steep learning curve. Just scheduling, done right.

**Fast to set up.** 5 minutes to create your page and start booking.

**Works everywhere.** Your booking page works on any device — phone, tablet, desktop.

**Professional.** Shows clients you're organized. Shows leads you're responsive.

**Affordable.** Free to start. $5/month for unlimited bookings.

### Who is it for?

- **Consultants & coaches** — Book discovery calls without the email dance
- **Small businesses** — Let clients schedule appointments without calling
- **Freelancers** — Make it easy for clients to book time with you
- **Sales teams** — Replace "can we jump on a call?" emails with a single link

### Features

- Custom booking page with your name and availability
- Timezone-aware scheduling
- Buffer time between meetings
- Email confirmations for host and client
- Google Calendar integration
- Booking cancellations via email link
- Mobile-responsive design
- Free tier (3 bookings/month) + $5/month unlimited

---

## Elevator Pitch (1-2 sentences)

**Version A:** "Simple, clean scheduling. Share your link — clients book in seconds, everyone gets confirmed automatically."

**Version B:** "ScheduleLink eliminates the email tag of scheduling meetings. Share your link, clients pick a time, everyone gets confirmed — automatically."

---

## Competitive Positioning

Other scheduling tools are cluttered and expensive. ScheduleLink is simple, clean, and affordable:

- **$5/month** for unlimited bookings
- Free tier: 3 bookings/month
- Fast setup — 5 minutes to your first booking
- Clean interface — no feature bloat, no learning curve

---

## Use Cases

**Use Case 1: The Sales Call**
*You send a prospect your booking link. They pick a time that works. You get an email confirmation with their details. You add it to your calendar. Done — no voicemails, no email tag.*

**Use Case 2: The Coaching Session**
*Your client clicks your booking link, selects a 45-minute slot, enters their name and what they want to discuss. You get an email with their notes. You show up ready.*

**Use Case 3: The Business Appointment**
*A customer wants to meet with you. They go to your booking page, see you're available Thursday at 2pm, book it. Both of you get confirmations. No phone tag.*

---

## Technical Specs (for developers/partners)

- **Platform:** Web-based SaaS (web app + mobile browser)
- **Host:** Individual accounts, each with custom booking page
- **Booking URL:** `/book/{username}` — public, no login required
- **Auth:** JWT-based, per-user accounts
- **Payments:** Stripe subscriptions ($5/mo)
- **Calendar:** Google Calendar API (OAuth2)
- **Email:** SMTP (Gmail) with HTML templates
- **Database:** SQLite (production-ready PostgreSQL migration available)
- **API:** RESTful FastAPI backend
