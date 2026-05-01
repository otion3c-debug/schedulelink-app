import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings

logger = logging.getLogger(__name__)


def _send(to_email: str, subject: str, html: str) -> bool:
    if not settings.SMTP_PASSWORD:
        logger.info(f"[email skipped: no SMTP_PASSWORD] to={to_email} subject={subject!r}")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_booking_confirmation(booking) -> bool:
    when = booking.start_time.strftime("%A, %B %d, %Y at %I:%M %p")
    notes_html = f"<p>Notes: {booking.notes}</p>" if booking.notes else ""
    html = f"""
    <html><body>
      <h2>Your booking is confirmed!</h2>
      <p>Hi {booking.attendee_name},</p>
      <p>Your appointment has been scheduled for:</p>
      <p><strong>{when} ({booking.timezone})</strong></p>
      <p>Duration: {booking.duration_minutes} minutes</p>
      {notes_html}
      <p><a href="{settings.FRONTEND_URL}/booking/{booking.id}/cancel">Cancel or Reschedule</a></p>
      <p>Thanks,<br>ScheduleLink</p>
    </body></html>
    """
    return _send(booking.attendee_email, f"Booking Confirmed: {booking.start_time.strftime('%B %d at %I:%M %p')}", html)
