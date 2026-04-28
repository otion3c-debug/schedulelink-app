"""Email sending via SMTP (Gmail) with professional HTML templates.

All emails are sent asynchronously in background threads to not block API responses.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")


def is_configured() -> bool:
    """Check if email is properly configured."""
    return bool(SMTP_USER and SMTP_PASSWORD)


def _send_email_async(to: str, subject: str, body_html: str, body_text: str = None):
    """Internal function to send email - runs in background thread."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[Email] Not configured - skipping send to {to}")
        return
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM or SMTP_USER
    msg["To"] = to
    
    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())
        print(f"[Email] Sent to {to}: {subject}")
    except Exception as e:
        print(f"[Email] Failed to send to {to}: {e}")


def send_email(to: str, subject: str, body_html: str, body_text: str = None) -> bool:
    """Send an email via SMTP (async in background thread)."""
    thread = threading.Thread(
        target=_send_email_async, 
        args=(to, subject, body_html, body_text),
        daemon=True
    )
    thread.start()
    return True


def _base_template(content: str) -> str:
    """Base email template with professional dark theme styling."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #1a1a2e; color: #e4e4e7;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1a1a2e; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #242442; border-radius: 12px; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">📅 ScheduleLink</h1>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            {content}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 30px; border-top: 1px solid #3f3f60; text-align: center;">
                            <p style="margin: 0; font-size: 13px; color: #71717a;">
                                Powered by ScheduleLink • Simple Scheduling for Busy People
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def send_booking_confirmation_to_client(
    client_email: str,
    client_name: str,
    host_name: str,
    start_time: str,
    meeting_duration: int,
    notes: str = "",
    cancellation_link: str = ""
) -> bool:
    """Send booking confirmation email to the client."""
    subject = f"✅ Meeting Confirmed with {host_name}"
    
    cancel_section = ""
    if cancellation_link:
        cancel_section = f"""
        <p style="margin-top: 24px; font-size: 14px; color: #a1a1aa;">
            Need to cancel? <a href="{cancellation_link}" style="color: #818cf8;">Click here to cancel this meeting</a>
        </p>
        """
    
    notes_section = ""
    if notes:
        notes_section = f"""
        <p style="margin: 20px 0 12px; font-size: 14px; color: #71717a;">YOUR NOTES</p>
        <p style="margin: 0; font-size: 16px; color: #a1a1aa;">{notes}</p>
        """
    
    content = f"""
    <h2 style="margin: 0 0 20px; color: #22c55e; font-size: 28px;">Meeting Confirmed! ✓</h2>
    
    <p style="font-size: 16px; color: #e4e4e7; margin-bottom: 8px;">Hi {client_name},</p>
    <p style="font-size: 16px; color: #a1a1aa; margin-bottom: 24px;">Your meeting with <strong style="color: #e4e4e7;">{host_name}</strong> has been scheduled.</p>
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1a1a2e; border-radius: 8px; padding: 24px; margin: 24px 0;">
        <tr>
            <td>
                <p style="margin: 0 0 12px; font-size: 14px; color: #71717a;">DATE & TIME</p>
                <p style="margin: 0 0 20px; font-size: 18px; color: #e4e4e7; font-weight: 600;">{start_time}</p>
                
                <p style="margin: 0 0 12px; font-size: 14px; color: #71717a;">DURATION</p>
                <p style="margin: 0; font-size: 18px; color: #e4e4e7; font-weight: 600;">{meeting_duration} minutes</p>
                
                {notes_section}
            </td>
        </tr>
    </table>
    
    <p style="font-size: 16px; color: #a1a1aa;">A calendar invite will be sent to your email shortly.</p>
    
    {cancel_section}
    """
    
    body_html = _base_template(content)
    
    body_text = f"""Meeting Confirmed!

Hi {client_name},

Your meeting with {host_name} has been scheduled.

Date & Time: {start_time}
Duration: {meeting_duration} minutes
{f'Notes: {notes}' if notes else ''}

A calendar invite will be sent shortly.

— ScheduleLink"""
    
    return send_email(client_email, subject, body_html, body_text)


def send_booking_notification_to_host(
    host_email: str,
    host_name: str,
    client_name: str,
    client_email: str,
    start_time: str,
    meeting_duration: int,
    notes: str = "",
    client_phone: str = ""
) -> bool:
    """Send new booking notification email to the host."""
    subject = f"📅 New Booking: {client_name}"
    
    phone_section = ""
    if client_phone:
        phone_section = f'<p style="margin: 0 0 20px; font-size: 14px; color: #a1a1aa;">📞 {client_phone}</p>'
    
    notes_section = ""
    if notes:
        notes_section = f"""
        <p style="margin: 20px 0 12px; font-size: 14px; color: #71717a;">CLIENT NOTES</p>
        <p style="margin: 0; font-size: 16px; color: #a1a1aa;">{notes}</p>
        """
    
    content = f"""
    <h2 style="margin: 0 0 20px; color: #6366f1; font-size: 28px;">New Meeting Booked! 📅</h2>
    
    <p style="font-size: 16px; color: #e4e4e7; margin-bottom: 8px;">Hi {host_name},</p>
    <p style="font-size: 16px; color: #a1a1aa; margin-bottom: 24px;">Someone just booked a meeting with you.</p>
    
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #1a1a2e; border-radius: 8px; padding: 24px; margin: 24px 0;">
        <tr>
            <td>
                <p style="margin: 0 0 12px; font-size: 14px; color: #71717a;">CLIENT</p>
                <p style="margin: 0 0 4px; font-size: 18px; color: #e4e4e7; font-weight: 600;">{client_name}</p>
                <p style="margin: 0 0 20px; font-size: 14px; color: #818cf8;">{client_email}</p>
                {phone_section}
                
                <p style="margin: 0 0 12px; font-size: 14px; color: #71717a;">DATE & TIME</p>
                <p style="margin: 0 0 20px; font-size: 18px; color: #e4e4e7; font-weight: 600;">{start_time}</p>
                
                <p style="margin: 0 0 12px; font-size: 14px; color: #71717a;">DURATION</p>
                <p style="margin: 0; font-size: 18px; color: #e4e4e7; font-weight: 600;">{meeting_duration} minutes</p>
                
                {notes_section}
            </td>
        </tr>
    </table>
    
    <p style="font-size: 16px; color: #a1a1aa;">The event has been added to your Google Calendar.</p>
    """
    
    body_html = _base_template(content)
    
    body_text = f"""New Meeting Booked!

Hi {host_name},

Someone just booked a meeting with you.

Client: {client_name}
Email: {client_email}
{f'Phone: {client_phone}' if client_phone else ''}
Date & Time: {start_time}
Duration: {meeting_duration} minutes
{f'Notes: {notes}' if notes else ''}

The event has been added to your calendar.

— ScheduleLink"""
    
    return send_email(host_email, subject, body_html, body_text)


def send_booking_cancellation(
    to_email: str,
    to_name: str,
    other_party: str,
    start_time: str
) -> bool:
    """Send booking cancellation notification."""
    subject = "❌ Meeting Cancelled"
    
    content = f"""
    <h2 style="margin: 0 0 20px; color: #ef4444; font-size: 28px;">Meeting Cancelled</h2>
    
    <p style="font-size: 16px; color: #e4e4e7; margin-bottom: 24px;">Hi {to_name},</p>
    
    <p style="font-size: 16px; color: #a1a1aa; margin-bottom: 16px;">
        The meeting with <strong style="color: #e4e4e7;">{other_party}</strong> scheduled for 
        <strong style="color: #e4e4e7;">{start_time}</strong> has been cancelled.
    </p>
    
    <p style="font-size: 14px; color: #71717a; margin-top: 32px;">
        The calendar event has been removed automatically.
    </p>
    """
    
    body_html = _base_template(content)
    
    body_text = f"""Meeting Cancelled

Hi {to_name},

The meeting with {other_party} scheduled for {start_time} has been cancelled.

The calendar event has been removed automatically.

— ScheduleLink"""
    
    return send_email(to_email, subject, body_html, body_text)
