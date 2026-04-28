"""Email sending via SMTP (Gmail)."""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")

def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None
) -> bool:
    """Send an email via SMTP."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("Email not configured - skipping send")
        return False
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM or SMTP_USER
    msg["To"] = to
    
    # Plain text version
    if body_text:
        msg.attach(MIMEText(body_text, "plain"))
    
    # HTML version
    msg.attach(MIMEText(body_html, "html"))
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())
        print(f"Email sent to {to}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_booking_confirmation_to_client(
    client_email: str,
    client_name: str,
    host_name: str,
    start_time: str,
    meeting_duration: int,
    notes: str = ""
) -> bool:
    """Send booking confirmation email to the client."""
    subject = f"Meeting Confirmed with {host_name}"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">Meeting Confirmed! ✓</h2>
        <p>Hi {client_name},</p>
        <p>Your meeting with <strong>{host_name}</strong> has been scheduled.</p>
        
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Date & Time:</strong> {start_time}</p>
            <p style="margin: 10px 0 0;"><strong>Duration:</strong> {meeting_duration} minutes</p>
            {f'<p style="margin: 10px 0 0;"><strong>Notes:</strong> {notes}</p>' if notes else ''}
        </div>
        
        <p>You'll receive a calendar invite shortly.</p>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            — Sent via ScheduleLink
        </p>
    </body>
    </html>
    """
    
    body_text = f"""
Meeting Confirmed!

Hi {client_name},

Your meeting with {host_name} has been scheduled.

Date & Time: {start_time}
Duration: {meeting_duration} minutes
{f'Notes: {notes}' if notes else ''}

You'll receive a calendar invite shortly.

— Sent via ScheduleLink
    """
    
    return send_email(client_email, subject, body_html, body_text)

def send_booking_notification_to_host(
    host_email: str,
    host_name: str,
    client_name: str,
    client_email: str,
    start_time: str,
    meeting_duration: int,
    notes: str = ""
) -> bool:
    """Send new booking notification email to the host."""
    subject = f"New Booking: {client_name}"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2563eb;">New Meeting Booked! 📅</h2>
        <p>Hi {host_name},</p>
        <p>Someone just booked a meeting with you.</p>
        
        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Client:</strong> {client_name}</p>
            <p style="margin: 10px 0 0;"><strong>Email:</strong> {client_email}</p>
            <p style="margin: 10px 0 0;"><strong>Date & Time:</strong> {start_time}</p>
            <p style="margin: 10px 0 0;"><strong>Duration:</strong> {meeting_duration} minutes</p>
            {f'<p style="margin: 10px 0 0;"><strong>Notes:</strong> {notes}</p>' if notes else ''}
        </div>
        
        <p>The event has been added to your calendar.</p>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            — Sent via ScheduleLink
        </p>
    </body>
    </html>
    """
    
    body_text = f"""
New Meeting Booked!

Hi {host_name},

Someone just booked a meeting with you.

Client: {client_name}
Email: {client_email}
Date & Time: {start_time}
Duration: {meeting_duration} minutes
{f'Notes: {notes}' if notes else ''}

The event has been added to your calendar.

— Sent via ScheduleLink
    """
    
    return send_email(host_email, subject, body_html, body_text)

def send_booking_cancellation(
    to_email: str,
    to_name: str,
    other_party: str,
    start_time: str
) -> bool:
    """Send booking cancellation notification."""
    subject = "Meeting Cancelled"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #dc2626;">Meeting Cancelled</h2>
        <p>Hi {to_name},</p>
        <p>The meeting with <strong>{other_party}</strong> scheduled for <strong>{start_time}</strong> has been cancelled.</p>
        
        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            — Sent via ScheduleLink
        </p>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, body_html)
