"""Appointment reminder scheduler using APScheduler."""

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .database import get_db, dict_from_row
from .services.emailer import send_reminder_email
from .config import get_settings

# Global scheduler instance
scheduler = None


def check_and_send_reminders():
    """
    Check for bookings that need reminders and send them.
    This runs every 15 minutes.
    """
    settings = get_settings()
    now = datetime.utcnow()
    
    # Time windows for reminders
    # 24-hour reminder: between 23 and 24 hours before appointment
    reminder_24h_start = now + timedelta(hours=23)
    reminder_24h_end = now + timedelta(hours=24, minutes=15)
    
    # 1-hour reminder: between 45 minutes and 1 hour 15 minutes before appointment
    reminder_1h_start = now + timedelta(minutes=45)
    reminder_1h_end = now + timedelta(hours=1, minutes=15)
    
    with get_db() as conn:
        # Get all bookings needing 24-hour reminder
        # Only for hosts with pro_plus subscription
        bookings_24h = conn.execute(
            """
            SELECT b.*, u.full_name as host_name, u.timezone as host_timezone,
                   u.subscription_status, u.email as host_email
            FROM bookings b
            JOIN users u ON b.host_id = u.id
            WHERE b.status = 'confirmed'
            AND b.reminder_24h_sent = 0
            AND u.subscription_status = 'pro_plus'
            AND b.booking_time >= ?
            AND b.booking_time <= ?
            """,
            (reminder_24h_start.strftime("%Y-%m-%d %H:%M:%S"),
             reminder_24h_end.strftime("%Y-%m-%d %H:%M:%S"))
        ).fetchall()
        
        # Get all bookings needing 1-hour reminder
        bookings_1h = conn.execute(
            """
            SELECT b.*, u.full_name as host_name, u.timezone as host_timezone,
                   u.subscription_status, u.email as host_email
            FROM bookings b
            JOIN users u ON b.host_id = u.id
            WHERE b.status = 'confirmed'
            AND b.reminder_1h_sent = 0
            AND u.subscription_status = 'pro_plus'
            AND b.booking_time >= ?
            AND b.booking_time <= ?
            """,
            (reminder_1h_start.strftime("%Y-%m-%d %H:%M:%S"),
             reminder_1h_end.strftime("%Y-%m-%d %H:%M:%S"))
        ).fetchall()
        
        # Process 24-hour reminders
        for row in bookings_24h:
            booking = dict_from_row(row)
            try:
                # Run async email in sync context
                asyncio.run(send_reminder_email(
                    client_email=booking["client_email"],
                    client_name=booking["client_name"],
                    host_name=booking["host_name"],
                    booking_time=booking["booking_time"],
                    duration=booking["duration"],
                    timezone=booking["host_timezone"],
                    reminder_type="24h",
                    cancellation_token=booking["cancellation_token"]
                ))
                
                # Mark as sent
                conn.execute(
                    "UPDATE bookings SET reminder_24h_sent = 1 WHERE id = ?",
                    (booking["id"],)
                )
                conn.commit()
                print(f"Sent 24h reminder for booking {booking['id']} to {booking['client_email']}")
                
            except Exception as e:
                print(f"Failed to send 24h reminder for booking {booking['id']}: {e}")
        
        # Process 1-hour reminders
        for row in bookings_1h:
            booking = dict_from_row(row)
            try:
                # Run async email in sync context
                asyncio.run(send_reminder_email(
                    client_email=booking["client_email"],
                    client_name=booking["client_name"],
                    host_name=booking["host_name"],
                    booking_time=booking["booking_time"],
                    duration=booking["duration"],
                    timezone=booking["host_timezone"],
                    reminder_type="1h",
                    cancellation_token=booking["cancellation_token"]
                ))
                
                # Mark as sent
                conn.execute(
                    "UPDATE bookings SET reminder_1h_sent = 1 WHERE id = ?",
                    (booking["id"],)
                )
                conn.commit()
                print(f"Sent 1h reminder for booking {booking['id']} to {booking['client_email']}")
                
            except Exception as e:
                print(f"Failed to send 1h reminder for booking {booking['id']}: {e}")


def start_scheduler():
    """Start the background scheduler."""
    global scheduler
    
    if scheduler is not None:
        return  # Already running
    
    scheduler = BackgroundScheduler()
    
    # Run reminder check every 15 minutes
    scheduler.add_job(
        check_and_send_reminders,
        trigger=IntervalTrigger(minutes=15),
        id='reminder_check',
        name='Check and send appointment reminders',
        replace_existing=True
    )
    
    scheduler.start()
    print("Appointment reminder scheduler started (runs every 15 minutes)")


def stop_scheduler():
    """Stop the background scheduler."""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        print("Appointment reminder scheduler stopped")
