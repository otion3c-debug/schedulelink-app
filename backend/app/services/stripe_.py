"""Stripe service utilities."""

import stripe
from ..config import get_settings


def init_stripe():
    """Initialize Stripe with API key."""
    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key


def create_customer(email: str, name: str, user_id: int) -> str:
    """Create a Stripe customer and return customer ID."""
    init_stripe()
    
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata={"user_id": user_id}
    )
    
    return customer.id


def create_checkout_session(customer_id: str, price_id: str, success_url: str, cancel_url: str, user_id: int) -> str:
    """Create a Stripe Checkout session and return session URL."""
    init_stripe()
    
    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price": price_id,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user_id}
    )
    
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe billing portal session and return URL."""
    init_stripe()
    
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url
    )
    
    return session.url


def get_subscription_status(subscription_id: str) -> dict:
    """Get subscription status from Stripe."""
    init_stripe()
    
    subscription = stripe.Subscription.retrieve(subscription_id)
    
    return {
        "id": subscription.id,
        "status": subscription.status,
        "current_period_end": subscription.current_period_end,
        "cancel_at_period_end": subscription.cancel_at_period_end
    }
