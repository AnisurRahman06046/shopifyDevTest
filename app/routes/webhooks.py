from fastapi import APIRouter, Request, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
import json

from app.database import get_db_session
from app.models import Shop, WebhookEvent
from app.security import verify_webhook_hmac
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/shopify")
async def handle_shopify_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Handle incoming Shopify webhooks
    """
    # Get headers
    headers = dict(request.headers)
    topic = headers.get("x-shopify-topic")
    shop_domain = headers.get("x-shopify-shop-domain")
    hmac_header = headers.get("x-shopify-hmac-sha256")
    webhook_id = headers.get("x-shopify-webhook-id")

    # Validate required headers
    if not all([topic, shop_domain, hmac_header]):
        logger.warning(
            f"Missing webhook headers: topic={topic}, shop={shop_domain}, hmac={bool(hmac_header)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required webhook headers",
        )

    # Get raw body for HMAC verification
    raw_body = await request.body()

    # Verify HMAC signature
    if not verify_webhook_hmac(raw_body, hmac_header):
        logger.warning(f"Invalid webhook HMAC for shop: {shop_domain}, topic: {topic}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
        )

    # Parse JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload"
        )

    # Store webhook event
    webhook_event = WebhookEvent(
        shop_domain=shop_domain,
        topic=topic,
        webhook_id=webhook_id,
        payload=payload,
        headers=headers,
        processed=False,
        received_at=datetime.utcnow(),
    )
    session.add(webhook_event)
    await session.commit()

    logger.info(f"Received webhook: {topic} from {shop_domain}")

    # Process webhook in background
    background_tasks.add_task(
        process_webhook_event, webhook_event.id, topic, shop_domain, payload
    )

    return {"status": "received", "topic": topic, "shop": shop_domain}


async def process_webhook_event(
    webhook_event_id: int, topic: str, shop_domain: str, payload: dict
):
    """
    Process webhook event in background

    Args:
        webhook_event_id: Database ID of webhook event
        topic: Webhook topic
        shop_domain: Shop domain
        payload: Webhook payload
    """
    from app.database import async_session_maker

    async with async_session_maker() as session:
        try:
            # Update webhook processing status
            result = await session.execute(
                select(WebhookEvent).where(WebhookEvent.id == webhook_event_id)
            )
            webhook_event = result.scalar_one_or_none()

            if not webhook_event:
                logger.error(f"Webhook event not found: {webhook_event_id}")
                return

            # Process different webhook topics
            if topic == "app/uninstalled":
                await handle_app_uninstalled(session, shop_domain, payload)
            elif topic == "orders/create":
                await handle_order_created(session, shop_domain, payload)
            elif topic == "orders/updated":
                await handle_order_updated(session, shop_domain, payload)
            elif topic == "products/create":
                await handle_product_created(session, shop_domain, payload)
            elif topic == "products/update":
                await handle_product_updated(session, shop_domain, payload)
            elif topic == "customers/create":
                await handle_customer_created(session, shop_domain, payload)
            else:
                logger.info(f"Unhandled webhook topic: {topic}")

            # Mark as processed
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            await session.commit()

            logger.info(f"Successfully processed webhook: {topic} for {shop_domain}")

        except Exception as e:
            logger.error(f"Error processing webhook {webhook_event_id}: {e}")
            # Update error status
            if webhook_event:
                webhook_event.error_message = str(e)
                await session.commit()


async def handle_app_uninstalled(
    session: AsyncSession, shop_domain: str, payload: dict
):
    """
    Handle app uninstallation webhook

    Args:
        session: Database session
        shop_domain: Shop domain
        payload: Webhook payload
    """
    logger.info(f"Processing app uninstallation for: {shop_domain}")

    # Find and update shop record
    result = await session.execute(select(Shop).where(Shop.shop_domain == shop_domain))
    shop = result.scalar_one_or_none()

    if shop:
        shop.uninstalled = True
        shop.uninstalled_at = datetime.utcnow()
        shop.access_token = None  # Clear access token for security
        shop.updated_at = datetime.utcnow()

        logger.info(f"Marked shop as uninstalled: {shop_domain}")
    else:
        logger.warning(f"Shop not found for uninstallation: {shop_domain}")


async def handle_order_created(session: AsyncSession, shop_domain: str, payload: dict):
    """
    Handle new order webhook

    Args:
        session: Database session
        shop_domain: Shop domain
        payload: Order data
    """
    order_id = payload.get("id")
    order_number = payload.get("order_number")
    total_price = payload.get("total_price")

    logger.info(
        f"New order created - Shop: {shop_domain}, Order: #{order_number}, Total: {total_price}"
    )

    # Add your custom order processing logic here
    # For example: sync to external system, send notifications, etc.


async def handle_order_updated(session: AsyncSession, shop_domain: str, payload: dict):
    """
    Handle order update webhook

    Args:
        session: Database session
        shop_domain: Shop domain
        payload: Order data
    """
    order_id = payload.get("id")
    order_number = payload.get("order_number")
    financial_status = payload.get("financial_status")
    fulfillment_status = payload.get("fulfillment_status")

    logger.info(
        f"Order updated - Shop: {shop_domain}, Order: #{order_number}, Financial: {financial_status}, Fulfillment: {fulfillment_status}"
    )


async def handle_product_created(
    session: AsyncSession, shop_domain: str, payload: dict
):
    """
    Handle new product webhook

    Args:
        session: Database session
        shop_domain: Shop domain
        payload: Product data
    """
    product_id = payload.get("id")
    product_title = payload.get("title")
    product_type = payload.get("product_type")
    vendor = payload.get("vendor")

    logger.info(
        f"New product created - Shop: {shop_domain}, Product: {product_title}, Type: {product_type}, Vendor: {vendor}"
    )


async def handle_product_updated(
    session: AsyncSession, shop_domain: str, payload: dict
):
    """
    Handle product update webhook

    Args:
        session: Database session
        shop_domain: Shop domain
        payload: Product data
    """
    product_id = payload.get("id")
    product_title = payload.get("title")

    logger.info(f"Product updated - Shop: {shop_domain}, Product: {product_title}")


async def handle_customer_created(
    session: AsyncSession, shop_domain: str, payload: dict
):
    """
    Handle new customer webhook

    Args:
        session: Database session
        shop_domain: Shop domain
        payload: Customer data
    """
    customer_id = payload.get("id")
    customer_email = payload.get("email")
    first_name = payload.get("first_name")
    last_name = payload.get("last_name")

    logger.info(
        f"New customer created - Shop: {shop_domain}, Email: {customer_email}, Name: {first_name} {last_name}"
    )


@router.get("/events")
async def list_webhook_events(
    shop: str = None,
    topic: str = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
):
    """
    List webhook events for debugging

    Args:
        shop: Filter by shop domain (optional)
        topic: Filter by topic (optional)
        limit: Maximum number of events to return
    """
    query = select(WebhookEvent).order_by(WebhookEvent.received_at.desc())

    if shop:
        query = query.where(WebhookEvent.shop_domain == shop)
    if topic:
        query = query.where(WebhookEvent.topic == topic)

    query = query.limit(limit)

    result = await session.execute(query)
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": event.id,
                "shop_domain": event.shop_domain,
                "topic": event.topic,
                "webhook_id": event.webhook_id,
                "processed": event.processed,
                "processed_at": event.processed_at,
                "received_at": event.received_at,
                "error_message": event.error_message,
                "payload_keys": list(event.payload.keys()) if event.payload else [],
            }
            for event in events
        ],
        "total": len(events),
    }
