"""Stripe integration for paid tier ($5/month subscription).

Handles:
- Customer creation
- Checkout session creation with 7-day free trial
- Billing portal access
- Webhook processing
"""
import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")

# Only import stripe if key is configured
stripe = None
if STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith("sk_"):
    try:
        import stripe as stripe_module
        stripe_module.api_key = STRIPE_SECRET_KEY
        stripe = stripe_module
        print(f"[Stripe] Configured with key: {STRIPE_SECRET_KEY[:15]}...")
    except ImportError:
        print("[Stripe] Module not installed - billing disabled")


def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return stripe is not None and bool(STRIPE_PRICE_ID)


def create_customer(email: str, name: str = "") -> Optional[str]:
    """Create a Stripe customer and return customer ID."""
    if not stripe:
        return None
    
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name or email,
            metadata={"source": "schedulelink"}
        )
        print(f"[Stripe] Created customer: {customer.id}")
        return customer.id
    except Exception as e:
        print(f"[Stripe] Error creating customer: {e}")
        return None


def create_checkout_session(
    customer_id: str,
    success_url: str,
    cancel_url: str
) -> Optional[str]:
    """Create a Stripe Checkout session and return the URL.
    
    Includes 7-day free trial.
    """
    if not stripe or not STRIPE_PRICE_ID:
        return None
    
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                "trial_period_days": 7  # 7-day free trial
            },
            allow_promotion_codes=True
        )
        print(f"[Stripe] Created checkout session: {session.id}")
        return session.url
    except Exception as e:
        print(f"[Stripe] Error creating checkout session: {e}")
        return None


def create_billing_portal_session(customer_id: str, return_url: str) -> Optional[str]:
    """Create a Stripe Billing Portal session for managing subscription."""
    if not stripe:
        return None
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        return session.url
    except Exception as e:
        print(f"[Stripe] Error creating portal session: {e}")
        return None


def get_subscription_status(subscription_id: str) -> Optional[str]:
    """Get the status of a subscription."""
    if not stripe:
        return None
    
    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        return subscription.status
    except Exception as e:
        print(f"[Stripe] Error retrieving subscription: {e}")
        return None


def cancel_subscription(subscription_id: str) -> bool:
    """Cancel a subscription at period end."""
    if not stripe:
        return False
    
    try:
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=True
        )
        return True
    except Exception as e:
        print(f"[Stripe] Error canceling subscription: {e}")
        return False


def verify_webhook_signature(payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
    """Verify and parse a Stripe webhook event.
    
    If no webhook secret is configured, parses without verification (for testing).
    """
    if not stripe:
        return None
    
    # If no webhook secret configured, parse without verification (for testing)
    if not STRIPE_WEBHOOK_SECRET:
        try:
            return json.loads(payload.decode())
        except json.JSONDecodeError:
            return None
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        print(f"[Stripe] Webhook signature verification failed: {e}")
        return None
    except Exception as e:
        print(f"[Stripe] Webhook verification failed: {e}")
        return None
