"""Stripe payment routes."""

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..auth import get_current_user
from ..config import get_settings
from ..database import get_db
from ..models import CheckoutSessionResponse, PortalSessionResponse, MessageResponse

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


@router.get("/debug-config")
async def debug_stripe_config():
    """Debug endpoint to check Stripe configuration (remove in production)."""
    settings = get_settings()
    full_key = settings.stripe_secret_key_full
    return {
        "stripe_secret_key_set": bool(settings.stripe_secret_key),
        "stripe_secret_key_prefix": settings.stripe_secret_key[:20] + "..." if settings.stripe_secret_key else None,
        "stripe_secret_key_suffix_set": bool(settings.stripe_key_suffix),
        "stripe_secret_key_full_len": len(full_key) if full_key else 0,
        "stripe_publishable_key_set": bool(settings.stripe_publishable_key),
        "stripe_price_id_set": bool(settings.stripe_price_id),
        "stripe_price_id_pro_set": bool(settings.stripe_price_id_pro),
        "stripe_price_id_pro_plus_set": bool(settings.stripe_price_id_pro_plus),
        "app_url": settings.app_url,
    }


def get_stripe():
    """Initialize Stripe with API key."""
    settings = get_settings()
    # Use full key property which handles truncated env vars
    stripe.api_key = settings.stripe_secret_key_full
    return stripe


from typing import Optional
from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Checkout request with optional tier selection."""
    tier: str = "pro"  # "pro" ($5/mo) or "pro_plus" ($7/mo)


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutRequest = None,
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe Checkout session for subscription.
    
    Supports two tiers:
    - pro: $5/month, unlimited bookings
    - pro_plus: $7/month, unlimited bookings + appointment reminders
    """
    settings = get_settings()
    stripe_client = get_stripe()
    
    # Check if Stripe is configured
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing service not configured. Please contact support."
        )
    
    # Determine which tier/price to use
    tier = request.tier if request else "pro"
    if tier == "pro_plus":
        price_id = settings.stripe_price_id_pro_plus or settings.stripe_price_id
    else:
        price_id = settings.stripe_price_id_pro or settings.stripe_price_id
    
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe price not configured for tier '{tier}'. Please contact support."
        )
    
    try:
        # Create or get Stripe customer
        customer_id = current_user.get("stripe_customer_id")
        
        if not customer_id:
            # Create new Stripe customer
            customer = stripe_client.Customer.create(
                email=current_user["email"],
                name=current_user["full_name"],
                metadata={"user_id": current_user["id"]}
            )
            customer_id = customer.id
            
            # Save customer ID
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                    (customer_id, current_user["id"])
                )
                conn.commit()
        
        # Create checkout session
        session = stripe_client.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=f"{settings.app_url}/#/settings?subscription=success&tier={tier}",
            cancel_url=f"{settings.app_url}/#/settings?subscription=canceled",
            metadata={"user_id": current_user["id"], "tier": tier}
        )
        
        return CheckoutSessionResponse(checkout_url=session.url)
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Billing error: {str(e)}"
        )


@router.post("/portal", response_model=PortalSessionResponse)
async def create_portal_session(
    current_user: dict = Depends(get_current_user)
):
    """Create a Stripe billing portal session."""
    settings = get_settings()
    stripe_client = get_stripe()
    
    customer_id = current_user.get("stripe_customer_id")
    
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe first."
        )
    
    try:
        session = stripe_client.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.app_url}/#/settings"
        )
        
        return PortalSessionResponse(portal_url=session.url)
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    settings = get_settings()
    stripe_client = get_stripe()
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    # Verify webhook signature if secret is configured
    if settings.stripe_webhook_secret:
        try:
            event = stripe_client.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe_client.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # For development without webhook secret
        import json
        event = json.loads(payload)
    
    event_type = event.get("type") if isinstance(event, dict) else event.type
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
    
    with get_db() as conn:
        if event_type == "checkout.session.completed":
            # Subscription created
            customer_id = data.get("customer")
            subscription_id = data.get("subscription")
            metadata = data.get("metadata", {})
            tier = metadata.get("tier", "pro")  # Default to pro if not specified
            
            # Set subscription status based on tier
            # pro_plus gets "pro_plus" status (enables reminders)
            # pro gets "active" status
            db_status = "pro_plus" if tier == "pro_plus" else "active"
            
            conn.execute(
                """
                UPDATE users
                SET stripe_subscription_id = ?, subscription_status = ?
                WHERE stripe_customer_id = ?
                """,
                (subscription_id, db_status, customer_id)
            )
            conn.commit()
            
        elif event_type == "customer.subscription.updated":
            subscription_id = data.get("id")
            status_val = data.get("status")
            
            # Get current user's subscription status to preserve tier info
            current_user = conn.execute(
                "SELECT subscription_status FROM users WHERE stripe_subscription_id = ?",
                (subscription_id,)
            ).fetchone()
            
            current_status = current_user["subscription_status"] if current_user else "free"
            
            # Map Stripe status to our status, preserving tier
            if status_val in ("active", "trialing"):
                # Preserve pro_plus status if that's what they had
                if current_status == "pro_plus":
                    db_status = "pro_plus"
                else:
                    db_status = "active"
            elif status_val == "canceled":
                db_status = "canceled"
            else:
                db_status = status_val
            
            conn.execute(
                """
                UPDATE users
                SET subscription_status = ?
                WHERE stripe_subscription_id = ?
                """,
                (db_status, subscription_id)
            )
            conn.commit()
            
        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")
            
            conn.execute(
                """
                UPDATE users
                SET subscription_status = 'free', stripe_subscription_id = NULL
                WHERE stripe_subscription_id = ?
                """,
                (subscription_id,)
            )
            conn.commit()
    
    return {"status": "success"}


@router.get("/status")
async def get_subscription_status(
    current_user: dict = Depends(get_current_user)
):
    """Get current subscription status."""
    settings = get_settings()
    sub_status = current_user["subscription_status"]
    
    # Count bookings this month for free users
    booking_count = 0
    if sub_status == "free":
        from datetime import datetime
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d %H:%M:%S")
        
        with get_db() as conn:
            result = conn.execute(
                """
                SELECT COUNT(*) as count FROM bookings
                WHERE host_id = ? AND created_at >= ? AND status = 'confirmed'
                """,
                (current_user["id"], month_start)
            ).fetchone()
            booking_count = result["count"]
    
    # Determine tier name and features
    is_paid = sub_status in ("active", "pro_plus")
    has_reminders = sub_status == "pro_plus"
    
    # Map internal status to display name
    tier_display = {
        "free": "Free",
        "active": "Pro",
        "pro_plus": "Pro+",
        "canceled": "Canceled"
    }.get(sub_status, sub_status)
    
    return {
        "status": sub_status,
        "tier_display": tier_display,
        "bookings_this_month": booking_count,
        "bookings_limit": settings.free_bookings_per_month if sub_status == "free" else None,
        "can_accept_bookings": is_paid or booking_count < settings.free_bookings_per_month,
        "has_reminders": has_reminders,
        "is_paid": is_paid
    }
