from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..security import get_current_user
from ..config import settings
import stripe

router = APIRouter(tags=["subscriptions"])


def _stripe():
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, "Stripe not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


class CheckoutRequest(BaseModel):
    tier: str  # 'pro' or 'pro_plus'


@router.get("/subscription")
def get_subscription(current_user: User = Depends(get_current_user)):
    return {
        "tier": current_user.subscription_tier,
        "status": current_user.subscription_status,
        "billing_cycle_start": current_user.billing_cycle_start.isoformat() if current_user.billing_cycle_start else None,
        "bookings_used_this_month": current_user.bookings_used_this_month,
        "booking_limit": current_user.booking_limit,
        "stripe_customer_id": current_user.stripe_customer_id,
        "stripe_subscription_id": current_user.stripe_subscription_id,
    }


@router.post("/subscription/checkout")
def checkout(
    body: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = _stripe()
    if body.tier == "pro":
        price_id = settings.STRIPE_PRO_PRICE_ID
    elif body.tier == "pro_plus":
        price_id = settings.STRIPE_PRO_PLUS_PRICE_ID
    else:
        raise HTTPException(400, "Invalid tier")
    if not price_id:
        raise HTTPException(503, f"Price ID for {body.tier} not configured")

    if not current_user.stripe_customer_id:
        customer = s.Customer.create(email=current_user.email, name=current_user.full_name)
        current_user.stripe_customer_id = customer["id"]
        db.commit()

    session = s.checkout.Session.create(
        customer=current_user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{settings.FRONTEND_URL}/dashboard/billing?success=1",
        cancel_url=f"{settings.FRONTEND_URL}/dashboard/billing?cancelled=1",
        metadata={"user_id": str(current_user.id), "tier": body.tier},
    )
    return {"checkout_url": session.url}


@router.post("/subscription/portal")
def portal(
    current_user: User = Depends(get_current_user),
):
    s = _stripe()
    if not current_user.stripe_customer_id:
        raise HTTPException(400, "No Stripe customer")
    sess = s.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/dashboard/billing",
    )
    return {"portal_url": sess.url}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    s = _stripe()
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = s.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            raise HTTPException(400, f"Invalid signature: {e}")
    else:
        # Dev mode — accept unsigned payload
        import json
        event = json.loads(payload)

    etype = event.get("type")
    obj = event.get("data", {}).get("object", {})

    if etype in ("customer.subscription.created", "customer.subscription.updated"):
        customer_id = obj.get("customer")
        sub_id = obj.get("id")
        status = obj.get("status")
        items = obj.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        tier = "free"
        if price_id == settings.STRIPE_PRO_PRICE_ID:
            tier = "pro"
        elif price_id == settings.STRIPE_PRO_PLUS_PRICE_ID:
            tier = "pro_plus"
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.stripe_subscription_id = sub_id
            user.subscription_status = "active" if status == "active" else status
            user.subscription_tier = tier
            user.booking_limit = 999999 if tier in ("pro", "pro_plus") else 5
            db.commit()
    elif etype == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_tier = "free"
            user.subscription_status = "cancelled"
            user.booking_limit = 5
            db.commit()
    return {"received": True}
