import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, html: str) -> bool:
    logger.info(f"[email attempt] to={to_email} subject={subject!r} SMTP_USER={settings.SMTP_USER} SMTP_HOST={settings.SMTP_HOST}")
    if not settings.SMTP_PASSWORD:
        logger.info(f"[email skipped: no SMTP_PASSWORD] to={to_email} subject={subject!r}")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    try:
        if settings.SMTP_USE_SSL:
            import ssl
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15, context=context) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        logger.info(f"[email sent successfully] to={to_email}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e} | SMTP_HOST={settings.SMTP_HOST} SMTP_USER={settings.SMTP_USER}")
        return False


def _fmt_when(dt: datetime, tz: str) -> str:
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")


def send_owner_notification(
    owner_email: str,
    owner_name: str,
    attendee_name: str,
    start_time: datetime,
    timezone: str,
    duration_minutes: int,
    attendee_email: str,
    attendee_phone: Optional[str],
    notes: Optional[str],
) -> bool:
    """Notify the calendar owner that someone booked a slot."""
    when = _fmt_when(start_time, timezone)
    phone_html = f"<p>Phone: {attendee_phone}</p>" if attendee_phone else ""
    notes_html = f"<p>Notes: {notes}</p>" if notes else ""
    html = f"""
    <html><body>
      <h2>New booking confirmed!</h2>
      <p>Hi {owner_name},</p>
      <p><strong>{attendee_name}</strong> booked a time slot:</p>
      <p><strong>{when} ({timezone})</strong></p>
      <p>Duration: {duration_minutes} minutes</p>
      <p>Email: {attendee_email}</p>
      {phone_html}
      {notes_html}
      <p><a href="{settings.FRONTEND_URL}/dashboard/bookings">View in dashboard</a></p>
      <p>Thanks,<br>ScheduleLink</p>
    </body></html>
    """
    return _send(owner_email, f"New booking from {attendee_name} — {start_time.strftime('%B %d at %I:%M %p')}", html)


def send_booking_confirmation(
    attendee_email: str,
    attendee_name: str,
    start_time: datetime,
    timezone: str,
    duration_minutes: int,
    notes: Optional[str],
    booking_id,
) -> bool:
    """Send confirmation to the person who booked the appointment."""
    when = _fmt_when(start_time, timezone)
    notes_html = f"<p>Notes: {notes}</p>" if notes else ""
    html = f"""
    <html><body>
      <h2>Your booking is confirmed!</h2>
      <p>Hi {attendee_name},</p>
      <p>Your appointment has been scheduled for:</p>
      <p><strong>{when} ({timezone})</strong></p>
      <p>Duration: {duration_minutes} minutes</p>
      {notes_html}
      <p><a href="{settings.FRONTEND_URL}/booking/{booking_id}/cancel">Cancel or Reschedule</a></p>
      <p>Thanks,<br>ScheduleLink</p>
    </body></html>
    """
    return _send(attendee_email, f"Booking Confirmed: {start_time.strftime('%B %d at %I:%M %p')}", html)
