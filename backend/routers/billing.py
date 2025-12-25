"""
Billing router for Stripe webhook handling.
"""
from fastapi import APIRouter, Request, HTTPException, Header
import stripe
import logging
import time
from typing import Optional
from pydantic_settings import BaseSettings
from collections import OrderedDict

logger = logging.getLogger(__name__)
router = APIRouter()


class StripeSettings(BaseSettings):
    """Stripe configuration from environment variables."""
    stripe_webhook_secret: str = ""
    stripe_api_key: str = ""
    
    class Config:
        env_file = ".env"


# Initialize Stripe settings
stripe_settings = StripeSettings()
if stripe_settings.stripe_api_key:
    stripe.api_key = stripe_settings.stripe_api_key


# LRU cache for processed events (idempotency)
MAX_PROCESSED_EVENTS = 1000
processed_events = OrderedDict()


@router.post("/billing/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None)
):
    """
    Stripe webhook endpoint with signature verification and idempotency.
    
    Features:
    - Signature verification
    - Replay attack protection (300s window)
    - Idempotent event processing with LRU cache
    - Handles checkout.session.completed events
    
    Args:
        request: Raw request from Stripe
        stripe_signature: Stripe-Signature header
    
    Returns:
        Success response
    """
    if not stripe_signature:
        logger.warning("Missing Stripe signature")
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    if not stripe_settings.stripe_webhook_secret:
        logger.warning("Stripe webhook secret not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    # Get raw request body
    payload = await request.body()
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=stripe_settings.stripe_webhook_secret
        )
        
        # Check timestamp for replay protection (Stripe uses 300s tolerance)
        event_timestamp = event.get('created', 0)
        current_timestamp = int(time.time())
        time_difference = abs(current_timestamp - event_timestamp)
        
        if time_difference > 300:  # 5 minutes
            logger.warning(f"Event timestamp too old: {time_difference}s difference")
            raise HTTPException(status_code=400, detail="Event timestamp outside tolerance")
        
        # Idempotency check with LRU cache
        event_id = event['id']
        if event_id in processed_events:
            logger.info(f"Event {event_id} already processed (idempotent)")
            return {"status": "success", "message": "Event already processed"}
        
        # Process event
        event_type = event['type']
        logger.info(f"Processing Stripe event: {event_type}, ID: {event_id}")
        
        if event_type == 'checkout.session.completed':
            session = event['data']['object']
            logger.info(f"Checkout session completed: {session.get('id')}")
            
            # Add business logic here (e.g., provision access, send confirmation)
            # For MVP, just log and acknowledge
            customer_email = session.get('customer_email', 'unknown')
            logger.info(f"Processing payment for customer: {customer_email}")
        
        # Mark event as processed with LRU eviction
        processed_events[event_id] = current_timestamp
        
        # Maintain LRU cache size
        if len(processed_events) > MAX_PROCESSED_EVENTS:
            # Remove oldest entry (FIFO in OrderedDict)
            processed_events.popitem(last=False)
        
        return {"status": "success"}
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid Stripe signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook processing error: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")
