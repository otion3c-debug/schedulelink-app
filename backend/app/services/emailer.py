"""Email service using Gmail SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import get_settings


def format_datetime(dt_str: str, timezone: str) -> str:
    """Format datetime string for display."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo(timezone))
    return dt.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def get_html_template(title: str, content: str) -> str:
    """Generate branded HTML email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a;">
    <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-radius: 16px; padding: 40px; border: 1px solid #334155;">
            <!-- Logo -->
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #f8fafc;">
                    <span style="color: #3b82f6;">Schedule</span>Link
                </h1>
            </div>
            
            <!-- Title -->
            <h2 style="color: #f8fafc; font-size: 24px; font-weight: 600; margin: 0 0 24px 0; text-align: center;">
                {title}
            </h2>
            
            <!-- Content -->
            <div style="color: #cbd5e1; font-size: 16px; line-height: 1.6;">
                {content}
            </div>
            
            <!-- Footer -->
            <div style="margin-top: 40px; padding-top: 24px; border-top: 1px solid #334155; text-align: center;">
                <p style="color: #64748b; font-size: 14px; margin: 0;">
                    Powered by <span style="color: #3b82f6;">ScheduleLink</span>
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""


async def send_email(to: str, subject: str, html_content: str, plain_content: str = None):
    """Send email via SMTP."""
    settings = get_settings()
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to
    
    # Plain text fallback
    if plain_content:
        msg.attach(MIMEText(plain_content, "plain"))
    
    # HTML version
    msg.attach(MIMEText(html_content, "html"))
    
    # Send via SMTP
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def send_booking_confirmation_to_client(
    client_email: str,
    client_name: str,
    host_name: str,
    booking_time: str,
    duration: int,
    timezone: str,
    cancellation_url: str
):
    """Send booking confirmation email to the client."""
    formatted_time = format_datetime(booking_time, timezone)
    
    content = f"""
        <p style="margin: 0 0 16px 0;">Hi <strong style="color: #f8fafc;">{client_name}</strong>,</p>
        
        <p style="margin: 0 0 24px 0;">Your meeting has been confirmed!</p>
        
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Host</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{host_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">When</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{formatted_time}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Duration</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{duration} minutes</td>
                </tr>
            </table>
        </div>
        
        <p style="margin: 0 0 16px 0;">Need to cancel? <a href="{cancellation_url}" style="color: #3b82f6;">Click here to cancel this booking</a></p>
        
        <p style="margin: 0; color: #94a3b8; font-size: 14px;">This email was sent by ScheduleLink on behalf of {host_name}.</p>
    """
    
    html = get_html_template("Meeting Confirmed! ✓", content)
    
    plain = f"""
Hi {client_name},

Your meeting has been confirmed!

Host: {host_name}
When: {formatted_time}
Duration: {duration} minutes

Need to cancel? Visit: {cancellation_url}

This email was sent by ScheduleLink on behalf of {host_name}.
"""
    
    await send_email(
        to=client_email,
        subject=f"Meeting Confirmed with {host_name}",
        html_content=html,
        plain_content=plain
    )


async def send_booking_notification_to_host(
    host_email: str,
    host_name: str,
    client_name: str,
    client_email: str,
    client_phone: str,
    client_notes: str,
    booking_time: str,
    duration: int,
    timezone: str
):
    """Send new booking notification to the host."""
    formatted_time = format_datetime(booking_time, timezone)
    
    phone_display = client_phone or "Not provided"
    notes_display = client_notes or "None"
    
    content = f"""
        <p style="margin: 0 0 16px 0;">Hi <strong style="color: #f8fafc;">{host_name}</strong>,</p>
        
        <p style="margin: 0 0 24px 0;">You have a new booking!</p>
        
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Client</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{client_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Email</td>
                    <td style="padding: 8px 0; text-align: right;"><a href="mailto:{client_email}" style="color: #3b82f6;">{client_email}</a></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Phone</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{phone_display}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">When</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{formatted_time}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Duration</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{duration} minutes</td>
                </tr>
            </table>
        </div>
        
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <p style="margin: 0 0 8px 0; color: #94a3b8; font-size: 14px;">Client Notes</p>
            <p style="margin: 0; color: #f8fafc;">{notes_display}</p>
        </div>
    """
    
    html = get_html_template("New Booking! 🎉", content)
    
    plain = f"""
Hi {host_name},

You have a new booking!

Client: {client_name}
Email: {client_email}
Phone: {phone_display}
When: {formatted_time}
Duration: {duration} minutes

Client Notes:
{notes_display}
"""
    
    await send_email(
        to=host_email,
        subject=f"New Booking from {client_name}",
        html_content=html,
        plain_content=plain
    )


async def send_cancellation_email(
    client_email: str,
    client_name: str,
    host_name: str,
    booking_time: str,
    timezone: str
):
    """Send cancellation confirmation to client."""
    formatted_time = format_datetime(booking_time, timezone)
    
    content = f"""
        <p style="margin: 0 0 16px 0;">Hi <strong style="color: #f8fafc;">{client_name}</strong>,</p>
        
        <p style="margin: 0 0 24px 0;">Your meeting has been canceled.</p>
        
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Host</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{host_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Original Time</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{formatted_time}</td>
                </tr>
            </table>
        </div>
        
        <p style="margin: 0; color: #94a3b8;">If you'd like to reschedule, please visit their booking page.</p>
    """
    
    html = get_html_template("Meeting Canceled", content)
    
    plain = f"""
Hi {client_name},

Your meeting with {host_name} scheduled for {formatted_time} has been canceled.

If you'd like to reschedule, please visit their booking page.
"""
    
    await send_email(
        to=client_email,
        subject=f"Meeting with {host_name} Canceled",
        html_content=html,
        plain_content=plain
    )


async def send_cancellation_notification_to_host(
    host_email: str,
    host_name: str,
    client_name: str,
    booking_time: str,
    timezone: str
):
    """Send cancellation notification to host when client cancels."""
    formatted_time = format_datetime(booking_time, timezone)
    
    content = f"""
        <p style="margin: 0 0 16px 0;">Hi <strong style="color: #f8fafc;">{host_name}</strong>,</p>
        
        <p style="margin: 0 0 24px 0;">A booking has been canceled.</p>
        
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Client</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{client_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Original Time</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{formatted_time}</td>
                </tr>
            </table>
        </div>
    """
    
    html = get_html_template("Booking Canceled", content)
    
    plain = f"""
Hi {host_name},

A booking has been canceled.

Client: {client_name}
Original Time: {formatted_time}
"""
    
    await send_email(
        to=host_email,
        subject=f"Booking Canceled: {client_name}",
        html_content=html,
        plain_content=plain
    )


async def send_password_reset_email(
    client_email: str,
    client_name: str,
    reset_link: str
):
    """Send password reset email to user."""
    content = f"""
        <p style="margin: 0 0 16px 0;">Hi <strong style="color: #f8fafc;">{client_name}</strong>,</p>
        
        <p style="margin: 0 0 24px 0;">We received a request to reset your ScheduleLink password.</p>
        
        <p style="margin: 0 0 24px 0;">Click the button below to set a new password. This link expires in <strong style="color: #f8fafc;">1 hour</strong>.</p>
        
        <p style="text-align: center; margin: 0 0 32px 0;">
            <a href="{reset_link}" style="display: inline-block; background: #3b82f6; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;">Reset Password</a>
        </p>
        
        <p style="margin: 0 0 16px 0; color: #94a3b8; font-size: 14px;">
            If you didn't request a password reset, you can safely ignore this email. Your password won't be changed.
        </p>
        
        <p style="margin: 0; color: #64748b; font-size: 13px;">
            This link will expire in 1 hour. If you need help, contact us anytime.
        </p>
    """
    
    html = get_html_template("Reset Your Password", content)
    
    plain = f"""
Hi {client_name},

We received a request to reset your ScheduleLink password.

Click the link below to set a new password. This link expires in 1 hour.

{reset_link}

If you didn't request a password reset, you can safely ignore this email.

This link expires in 1 hour.
"""
    
    await send_email(
        to=client_email,
        subject="Reset Your ScheduleLink Password",
        html_content=html,
        plain_content=plain
    )


async def send_reminder_email(
    client_email: str,
    client_name: str,
    host_name: str,
    booking_time: str,
    duration: int,
    timezone: str,
    reminder_type: str,
    cancellation_token: str = None
):
    """Send appointment reminder email to client.
    
    Args:
        reminder_type: "24h" for 24-hour reminder, "1h" for 1-hour reminder
    """
    settings = get_settings()
    formatted_time = format_datetime(booking_time, timezone)
    
    if reminder_type == "24h":
        title = "Reminder: Your appointment is tomorrow! 📅"
        time_text = "Your appointment is coming up tomorrow"
        subject = f"Reminder: Your appointment with {host_name} is tomorrow"
    else:
        title = "Reminder: Your appointment is in 1 hour! ⏰"
        time_text = "Your appointment is starting soon"
        subject = f"Reminder: Your appointment with {host_name} starts in 1 hour"
    
    # Build reschedule/cancel link if token available
    cancel_link = ""
    if cancellation_token:
        cancel_url = f"{settings.app_url}/api/bookings/cancel/{cancellation_token}"
        cancel_link = f'<p style="margin: 0 0 16px 0;">Need to reschedule or cancel? <a href="{cancel_url}" style="color: #3b82f6;">Click here to cancel</a></p>'
    
    content = f"""
        <p style="margin: 0 0 16px 0;">Hi <strong style="color: #f8fafc;">{client_name}</strong>,</p>
        
        <p style="margin: 0 0 24px 0;">{time_text}!</p>
        
        <div style="background: #1e293b; border-radius: 12px; padding: 24px; margin-bottom: 24px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Host</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{host_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">When</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{formatted_time}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #94a3b8;">Duration</td>
                    <td style="padding: 8px 0; color: #f8fafc; text-align: right; font-weight: 500;">{duration} minutes</td>
                </tr>
            </table>
        </div>
        
        {cancel_link}
        
        <p style="margin: 0; color: #94a3b8; font-size: 14px;">This reminder was sent by ScheduleLink on behalf of {host_name}.</p>
    """
    
    html = get_html_template(title, content)
    
    plain = f"""
Hi {client_name},

{time_text}!

Host: {host_name}
When: {formatted_time}
Duration: {duration} minutes

{"Need to cancel? Visit: " + settings.app_url + "/api/bookings/cancel/" + cancellation_token if cancellation_token else ""}

This reminder was sent by ScheduleLink on behalf of {host_name}.
"""
    
    await send_email(
        to=client_email,
        subject=subject,
        html_content=html,
        plain_content=plain
    )
