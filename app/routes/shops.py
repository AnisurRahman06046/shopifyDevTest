# from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, func, and_, desc
# from typing import List, Optional, Dict, Any
# from datetime import datetime, timedelta
# import logging

# from app.database import get_db_session
# from app.models import Shop, ShopUsage, WebhookEvent
# from app.security import is_valid_shop_domain, verify_session_token
# from app.utils.shopify_api import ShopifyAPI
# from app.config import settings

# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/api", tags=["shops"])


# # Admin endpoints (for managing multiple shops)
# @router.get("/admin/shops")
# async def list_all_shops(
#     country: Optional[str] = Query(None, description="Filter by country code"),
#     plan: Optional[str] = Query(None, description="Filter by plan name"),
#     status: Optional[str] = Query(
#         "active", description="Filter by status (active/uninstalled/all)"
#     ),
#     limit: int = Query(50, le=100, description="Maximum number of shops to return"),
#     offset: int = Query(0, ge=0, description="Number of shops to skip"),
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     List all shops (admin endpoint)
#     """
#     query = select(Shop)

#     # Apply filters
#     if status == "active":
#         query = query.where(Shop.uninstalled == False)
#     elif status == "uninstalled":
#         query = query.where(Shop.uninstalled == True)
#     # For "all", don't filter by uninstalled status

#     if country:
#         query = query.where(Shop.country_code == country.upper())
#     if plan:
#         query = query.where(Shop.plan_name == plan.lower())

#     # Apply pagination
#     query = query.order_by(desc(Shop.installed_at)).offset(offset).limit(limit)

#     result = await session.execute(query)
#     shops = result.scalars().all()

#     # Get total count
#     count_query = select(func.count(Shop.id))
#     if status == "active":
#         count_query = count_query.where(Shop.uninstalled == False)
#     elif status == "uninstalled":
#         count_query = count_query.where(Shop.uninstalled == True)
#     if country:
#         count_query = count_query.where(Shop.country_code == country.upper())
#     if plan:
#         count_query = count_query.where(Shop.plan_name == plan.lower())

#     total = await session.scalar(count_query)

#     return {
#         "shops": [
#             {
#                 "id": shop.id,
#                 "shop_domain": shop.shop_domain,
#                 "shop_name": shop.shop_name,
#                 "country": shop.country_code,
#                 "country_name": shop.country_name,
#                 "currency": shop.currency,
#                 "plan": {
#                     "name": shop.plan_name,
#                     "display_name": shop.plan_display_name,
#                 },
#                 "status": "uninstalled" if shop.uninstalled else "active",
#                 "installed_at": shop.installed_at,
#                 "last_seen_at": shop.last_seen_at,
#                 "uninstalled_at": shop.uninstalled_at,
#                 "subscription_status": shop.subscription_status,
#                 "scopes": shop.scopes.split(",") if shop.scopes else [],
#             }
#             for shop in shops
#         ],
#         "pagination": {
#             "total": total,
#             "limit": limit,
#             "offset": offset,
#             "has_next": offset + limit < total,
#         },
#     }


# @router.get("/admin/stats")
# async def get_platform_stats(
#     days: int = Query(30, le=365, description="Number of days to include in stats"),
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     Get platform-wide statistics
#     """
#     since = datetime.utcnow() - timedelta(days=days)

#     # Total shops
#     active_shops = await session.scalar(
#         select(func.count(Shop.id)).where(Shop.uninstalled == False)
#     )

#     total_shops = await session.scalar(select(func.count(Shop.id)))

#     # Recent installations
#     recent_installs = await session.scalar(
#         select(func.count(Shop.id)).where(
#             and_(Shop.installed_at >= since, Shop.uninstalled == False)
#         )
#     )

#     # Recent uninstalls
#     recent_uninstalls = await session.scalar(
#         select(func.count(Shop.id)).where(Shop.uninstalled_at >= since)
#     )

#     # Shops by country
#     country_result = await session.execute(
#         select(Shop.country_code, func.count(Shop.id))
#         .where(Shop.uninstalled == False)
#         .group_by(Shop.country_code)
#         .order_by(func.count(Shop.id).desc())
#     )

#     # Shops by plan
#     plan_result = await session.execute(
#         select(Shop.plan_name, func.count(Shop.id))
#         .where(Shop.uninstalled == False)
#         .group_by(Shop.plan_name)
#         .order_by(func.count(Shop.id).desc())
#     )

#     # Recent webhook activity
#     webhook_count = await session.scalar(
#         select(func.count(WebhookEvent.id)).where(WebhookEvent.received_at >= since)
#     )

#     return {
#         "overview": {
#             "total_shops": total_shops,
#             "active_shops": active_shops,
#             "uninstalled_shops": total_shops - active_shops,
#         },
#         "recent_activity": {
#             "period_days": days,
#             "new_installs": recent_installs,
#             "uninstalls": recent_uninstalls,
#             "webhook_events": webhook_count,
#         },
#         "distribution": {
#             "by_country": dict(country_result.fetchall()),
#             "by_plan": dict(plan_result.fetchall()),
#         },
#         "generated_at": datetime.utcnow(),
#     }


# @router.get("/shops/{shop_domain}")
# async def get_shop_details(
#     shop_domain: str, session: AsyncSession = Depends(get_db_session)
# ):
#     """
#     Get detailed information about a specific shop
#     """
#     if not is_valid_shop_domain(shop_domain):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain format"
#         )

#     result = await session.execute(select(Shop).where(Shop.shop_domain == shop_domain))
#     shop = result.scalar_one_or_none()

#     if not shop:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
#         )

#     # Get recent usage data
#     week_ago = datetime.utcnow() - timedelta(days=7)
#     usage_result = await session.execute(
#         select(ShopUsage.metric_name, func.sum(ShopUsage.metric_value))
#         .where(and_(ShopUsage.shop_domain == shop_domain, ShopUsage.date >= week_ago))
#         .group_by(ShopUsage.metric_name)
#     )
#     usage_stats = dict(usage_result.fetchall())

#     # Get recent webhook events
#     recent_webhooks = await session.execute(
#         select(WebhookEvent.topic, func.count(WebhookEvent.id))
#         .where(
#             and_(
#                 WebhookEvent.shop_domain == shop_domain,
#                 WebhookEvent.received_at >= week_ago,
#             )
#         )
#         .group_by(WebhookEvent.topic)
#     )
#     webhook_stats = dict(recent_webhooks.fetchall())

#     return {
#         "shop": {
#             "domain": shop.shop_domain,
#             "name": shop.shop_name,
#             "email": shop.shop_email,
#             "owner": shop.shop_owner,
#             "location": {
#                 "country_code": shop.country_code,
#                 "country_name": shop.country_name,
#                 "timezone": shop.timezone,
#                 "primary_locale": shop.primary_locale,
#             },
#             "plan": {"name": shop.plan_name, "display_name": shop.plan_display_name},
#             "domains": {
#                 "myshopify": shop.myshopify_domain,
#                 "primary": shop.primary_domain,
#             },
#             "currency": shop.currency,
#             "status": "uninstalled" if shop.uninstalled else "active",
#             "subscription_status": shop.subscription_status,
#         },
#         "installation": {
#             "installed_at": shop.installed_at,
#             "last_seen_at": shop.last_seen_at,
#             "uninstalled_at": shop.uninstalled_at,
#             "scopes": shop.scopes.split(",") if shop.scopes else [],
#         },
#         "settings": shop.app_settings or {},
#         "usage_stats": usage_stats,
#         "webhook_stats": webhook_stats,
#     }


# @router.put("/shops/{shop_domain}/settings")
# async def update_shop_settings(
#     shop_domain: str,
#     settings_data: Dict[str, Any],
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     Update app settings for a specific shop
#     """
#     if not is_valid_shop_domain(shop_domain):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain format"
#         )

#     result = await session.execute(
#         select(Shop).where(Shop.shop_domain == shop_domain, Shop.uninstalled == False)
#     )
#     shop = result.scalar_one_or_none()

#     if not shop:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Shop not found or uninstalled",
#         )

#     # Update settings
#     current_settings = shop.app_settings or {}
#     current_settings.update(settings_data)
#     shop.app_settings = current_settings
#     shop.last_seen_at = datetime.utcnow()
#     shop.updated_at = datetime.utcnow()

#     await session.commit()

#     logger.info(f"Updated settings for shop: {shop_domain}")

#     return {
#         "status": "success",
#         "shop_domain": shop_domain,
#         "settings": shop.app_settings,
#     }


# # Shop-specific API endpoints (requires session token)
# @router.get("/products")
# async def get_shop_products(
#     shop: str = Query(..., description="Shop domain"),
#     limit: int = Query(50, le=100, description="Number of products to return"),
#     authorization: Optional[str] = Header(None),
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     Get products for a shop (requires session token for embedded apps)
#     """
#     # Verify authorization
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Missing or invalid authorization header",
#         )

#     token = authorization.split(" ", 1)[1]

#     if not is_valid_shop_domain(shop):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
#         )

#     # Verify session token
#     verify_session_token(token, shop)

#     # Get shop record
#     result = await session.execute(
#         select(Shop).where(Shop.shop_domain == shop, Shop.uninstalled == False)
#     )
#     shop_record = result.scalar_one_or_none()

#     if not shop_record or not shop_record.access_token:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Shop not found or access token missing",
#         )

#     # Fetch products from Shopify
#     try:
#         shopify_api = ShopifyAPI(shop, shop_record.access_token)
#         products_data = await shopify_api.get_products_graphql(limit)

#         # Track API usage
#         usage_record = ShopUsage(
#             shop_domain=shop,
#             metric_name="api_calls",
#             metric_value=1,
#             metric_data={"endpoint": "products", "limit": limit},
#         )
#         session.add(usage_record)
#         await session.commit()

#         return products_data

#     except Exception as e:
#         logger.error(f"Error fetching products for {shop}: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to fetch products: {str(e)}",
#         )


# # Bulk operations for multi-shop management
# @router.post("/admin/bulk/products")
# async def bulk_get_products(
#     shop_domains: Optional[List[str]] = None,
#     limit: int = Query(10, le=50, description="Products per shop"),
#     max_shops: int = Query(10, le=50, description="Maximum shops to process"),
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     Get products from multiple shops (admin operation)
#     """
#     query = select(Shop).where(Shop.uninstalled == False)

#     if shop_domains:
#         query = query.where(Shop.shop_domain.in_(shop_domains))

#     query = query.limit(max_shops)
#     result = await session.execute(query)
#     shops = result.scalars().all()

#     results = {}

#     for shop in shops:
#         if not shop.access_token:
#             results[shop.shop_domain] = {
#                 "shop_name": shop.shop_name,
#                 "error": "No access token available",
#             }
#             continue

#         try:
#             shopify_api = ShopifyAPI(shop.shop_domain, shop.access_token)
#             products_data = await shopify_api.get_products_graphql(limit)

#             results[shop.shop_domain] = {
#                 "shop_name": shop.shop_name,
#                 "products": products_data.get("data", {})
#                 .get("products", {})
#                 .get("edges", []),
#                 "status": "success",
#             }

#         except Exception as e:
#             logger.error(f"Error fetching products for {shop.shop_domain}: {e}")
#             results[shop.shop_domain] = {"shop_name": shop.shop_name, "error": str(e)}

#     return {"processed_shops": len(results), "results": results}


# @router.get("/admin/usage")
# async def get_usage_analytics(
#     days: int = Query(7, le=30, description="Number of days to analyze"),
#     metric: Optional[str] = Query(None, description="Filter by metric name"),
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     Get usage analytics across all shops
#     """
#     since = datetime.utcnow() - timedelta(days=days)

#     query = select(
#         ShopUsage.shop_domain,
#         ShopUsage.metric_name,
#         func.sum(ShopUsage.metric_value).label("total_value"),
#         func.count(ShopUsage.id).label("count"),
#     ).where(ShopUsage.date >= since)

#     if metric:
#         query = query.where(ShopUsage.metric_name == metric)

#     query = query.group_by(ShopUsage.shop_domain, ShopUsage.metric_name)

#     result = await session.execute(query)
#     usage_data = {}

#     for shop_domain, metric_name, total_value, count in result:
#         if shop_domain not in usage_data:
#             usage_data[shop_domain] = {}
#         usage_data[shop_domain][metric_name] = {"total": total_value, "count": count}

#     return {
#         "period_days": days,
#         "metric_filter": metric,
#         "usage_by_shop": usage_data,
#         "generated_at": datetime.utcnow(),
#     }


from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.database import get_db_session
from app.models import Shop, ShopUsage, WebhookEvent
from app.security import is_valid_shop_domain, verify_session_token
from app.utils.shopify_api import ShopifyAPI
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["shops"])


# Admin endpoints (for managing multiple shops)
@router.get("/admin/shops")
async def list_all_shops(
    country: Optional[str] = Query(None, description="Filter by country code"),
    plan: Optional[str] = Query(None, description="Filter by plan name"),
    status: Optional[str] = Query(
        "active", description="Filter by status (active/uninstalled/all)"
    ),
    limit: int = Query(50, le=100, description="Maximum number of shops to return"),
    offset: int = Query(0, ge=0, description="Number of shops to skip"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all shops (admin endpoint)
    """
    query = select(Shop)

    # Apply filters
    if status == "active":
        query = query.where(Shop.uninstalled == False)
    elif status == "uninstalled":
        query = query.where(Shop.uninstalled == True)
    # For "all", don't filter by uninstalled status

    if country:
        query = query.where(Shop.country_code == country.upper())
    if plan:
        query = query.where(Shop.plan_name == plan.lower())

    # Apply pagination
    query = query.order_by(desc(Shop.installed_at)).offset(offset).limit(limit)

    result = await session.execute(query)
    shops = result.scalars().all()

    # Get total count
    count_query = select(func.count(Shop.id))
    if status == "active":
        count_query = count_query.where(Shop.uninstalled == False)
    elif status == "uninstalled":
        count_query = count_query.where(Shop.uninstalled == True)
    if country:
        count_query = count_query.where(Shop.country_code == country.upper())
    if plan:
        count_query = count_query.where(Shop.plan_name == plan.lower())

    total = await session.scalar(count_query)

    return {
        "shops": [
            {
                "id": shop.id,
                "shop_domain": shop.shop_domain,
                "shop_name": shop.shop_name,
                "country": shop.country_code,
                "country_name": shop.country_name,
                "currency": shop.currency,
                "plan": {
                    "name": shop.plan_name,
                    "display_name": shop.plan_display_name,
                },
                "status": "uninstalled" if shop.uninstalled else "active",
                "installed_at": shop.installed_at,
                "last_seen_at": shop.last_seen_at,
                "uninstalled_at": shop.uninstalled_at,
                "subscription_status": shop.subscription_status,
                "scopes": shop.scopes.split(",") if shop.scopes else [],
            }
            for shop in shops
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": offset + limit < total,
        },
    }


@router.get("/admin/stats")
async def get_platform_stats(
    days: int = Query(30, le=365, description="Number of days to include in stats"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get platform-wide statistics
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Total shops
    active_shops = await session.scalar(
        select(func.count(Shop.id)).where(Shop.uninstalled == False)
    )

    total_shops = await session.scalar(select(func.count(Shop.id)))

    # Recent installations
    recent_installs = await session.scalar(
        select(func.count(Shop.id)).where(
            and_(Shop.installed_at >= since, Shop.uninstalled == False)
        )
    )

    # Recent uninstalls
    recent_uninstalls = await session.scalar(
        select(func.count(Shop.id)).where(Shop.uninstalled_at >= since)
    )

    # Shops by country
    country_result = await session.execute(
        select(Shop.country_code, func.count(Shop.id))
        .where(Shop.uninstalled == False)
        .group_by(Shop.country_code)
        .order_by(func.count(Shop.id).desc())
    )

    # Shops by plan
    plan_result = await session.execute(
        select(Shop.plan_name, func.count(Shop.id))
        .where(Shop.uninstalled == False)
        .group_by(Shop.plan_name)
        .order_by(func.count(Shop.id).desc())
    )

    # Recent webhook activity
    webhook_count = await session.scalar(
        select(func.count(WebhookEvent.id)).where(WebhookEvent.received_at >= since)
    )

    return {
        "overview": {
            "total_shops": total_shops,
            "active_shops": active_shops,
            "uninstalled_shops": total_shops - active_shops,
        },
        "recent_activity": {
            "period_days": days,
            "new_installs": recent_installs,
            "uninstalls": recent_uninstalls,
            "webhook_events": webhook_count,
        },
        "distribution": {
            "by_country": dict(country_result.fetchall()),
            "by_plan": dict(plan_result.fetchall()),
        },
        "generated_at": datetime.utcnow(),
    }


@router.get("/shops/{shop_domain}")
async def get_shop_details(
    shop_domain: str, session: AsyncSession = Depends(get_db_session)
):
    """
    Get detailed information about a specific shop
    """
    if not is_valid_shop_domain(shop_domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain format"
        )

    result = await session.execute(select(Shop).where(Shop.shop_domain == shop_domain))
    shop = result.scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found"
        )

    # Get recent usage data
    week_ago = datetime.utcnow() - timedelta(days=7)
    usage_result = await session.execute(
        select(ShopUsage.metric_name, func.sum(ShopUsage.metric_value))
        .where(and_(ShopUsage.shop_domain == shop_domain, ShopUsage.date >= week_ago))
        .group_by(ShopUsage.metric_name)
    )
    usage_stats = dict(usage_result.fetchall())

    # Get recent webhook events
    recent_webhooks = await session.execute(
        select(WebhookEvent.topic, func.count(WebhookEvent.id))
        .where(
            and_(
                WebhookEvent.shop_domain == shop_domain,
                WebhookEvent.received_at >= week_ago,
            )
        )
        .group_by(WebhookEvent.topic)
    )
    webhook_stats = dict(recent_webhooks.fetchall())

    return {
        "shop": {
            "domain": shop.shop_domain,
            "name": shop.shop_name,
            "email": shop.shop_email,
            "owner": shop.shop_owner,
            "location": {
                "country_code": shop.country_code,
                "country_name": shop.country_name,
                "timezone": shop.timezone,
                "primary_locale": shop.primary_locale,
            },
            "plan": {"name": shop.plan_name, "display_name": shop.plan_display_name},
            "domains": {
                "myshopify": shop.myshopify_domain,
                "primary": shop.primary_domain,
            },
            "currency": shop.currency,
            "status": "uninstalled" if shop.uninstalled else "active",
            "subscription_status": shop.subscription_status,
        },
        "installation": {
            "installed_at": shop.installed_at,
            "last_seen_at": shop.last_seen_at,
            "uninstalled_at": shop.uninstalled_at,
            "scopes": shop.scopes.split(",") if shop.scopes else [],
        },
        "settings": shop.app_settings or {},
        "usage_stats": usage_stats,
        "webhook_stats": webhook_stats,
    }


@router.put("/shops/{shop_domain}/settings")
async def update_shop_settings(
    shop_domain: str,
    settings_data: Dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Update app settings for a specific shop
    """
    if not is_valid_shop_domain(shop_domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain format"
        )

    result = await session.execute(
        select(Shop).where(Shop.shop_domain == shop_domain, Shop.uninstalled == False)
    )
    shop = result.scalar_one_or_none()

    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found or uninstalled",
        )

    # Update settings
    current_settings = shop.app_settings or {}
    current_settings.update(settings_data)
    shop.app_settings = current_settings
    shop.last_seen_at = datetime.utcnow()
    shop.updated_at = datetime.utcnow()

    await session.commit()

    logger.info(f"Updated settings for shop: {shop_domain}")

    return {
        "status": "success",
        "shop_domain": shop_domain,
        "settings": shop.app_settings,
    }


# Test endpoint (no authentication required)
@router.get("/products/test")
async def test_get_products(
    shop: str = Query(..., description="Shop domain"),
    limit: int = Query(10, le=100, description="Number of products"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Test endpoint to get products without session token (for development)
    """
    if not is_valid_shop_domain(shop):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
        )

    # Get shop record
    result = await session.execute(
        select(Shop).where(Shop.shop_domain == shop, Shop.uninstalled == False)
    )
    shop_record = result.scalar_one_or_none()

    if not shop_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found or not installed",
        )

    if not shop_record.access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access token available for this shop",
        )

    # Fetch products from Shopify
    try:
        shopify_api = ShopifyAPI(shop, shop_record.access_token)
        products_data = await shopify_api.get_products_graphql(limit)

        # Track usage
        usage_record = ShopUsage(
            shop_domain=shop,
            metric_name="api_calls",
            metric_value=1,
            metric_data={"endpoint": "products_test", "limit": limit},
        )
        session.add(usage_record)
        await session.commit()

        logger.info(f"Successfully fetched {limit} products for {shop}")
        return products_data

    except Exception as e:
        logger.error(f"Error fetching products for {shop}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch products: {str(e)}",
        )


# Shop-specific API endpoints (requires session token)
# @router.get("/products")
# async def get_shop_products(
#     shop: str = Query(..., description="Shop domain"),
#     limit: int = Query(50, le=100, description="Number of products to return"),
#     authorization: Optional[str] = Header(None),
#     session: AsyncSession = Depends(get_db_session),
# ):
#     """
#     Get products for a shop (requires session token for embedded apps)
#     """
#     # Verify authorization
#     if not authorization or not authorization.startswith("Bearer "):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Missing or invalid authorization header",
#         )

#     token = authorization.split(" ", 1)[1]

#     if not is_valid_shop_domain(shop):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
#         )

#     # Verify session token
#     verify_session_token(token, shop)

#     # Get shop record
#     result = await session.execute(
#         select(Shop).where(Shop.shop_domain == shop, Shop.uninstalled == False)
#     )
#     shop_record = result.scalar_one_or_none()

#     if not shop_record or not shop_record.access_token:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Shop not found or access token missing",
#         )

#     # Fetch products from Shopify
#     try:
#         shopify_api = ShopifyAPI(shop, shop_record.access_token)
#         products_data = await shopify_api.get_products_graphql(limit)

#         # Track API usage
#         usage_record = ShopUsage(
#             shop_domain=shop,
#             metric_name="api_calls",
#             metric_value=1,
#             metric_data={"endpoint": "products", "limit": limit},
#         )
#         session.add(usage_record)
#         await session.commit()

#         return products_data

#     except Exception as e:
#         logger.error(f"Error fetching products for {shop}: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to fetch products: {str(e)}",
#         )


@router.get("/products")
async def get_shop_products(
    shop: str = Query(..., description="Shop domain"),
    limit: int = Query(50, le=100, description="Number of products to return"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get products for a shop using stored access token
    This is the standard way for server-to-server API calls.
    """
    if not is_valid_shop_domain(shop):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
        )

    # Get shop record with access token
    result = await session.execute(
        select(Shop).where(Shop.shop_domain == shop, Shop.uninstalled == False)
    )
    shop_record = result.scalar_one_or_none()

    if not shop_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found or not installed",
        )

    if not shop_record.access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access token available for this shop",
        )

    # Use the stored access token to fetch products
    try:
        shopify_api = ShopifyAPI(shop, shop_record.access_token)
        products_data = await shopify_api.get_products_graphql(limit)

        # Track API usage
        usage_record = ShopUsage(
            shop_domain=shop,
            metric_name="api_calls",
            metric_value=1,
            metric_data={"endpoint": "products", "limit": limit},
        )
        session.add(usage_record)
        await session.commit()

        # Update last seen
        shop_record.last_seen_at = datetime.utcnow()
        await session.commit()

        logger.info(f"Successfully fetched {limit} products for {shop}")
        return products_data

    except Exception as e:
        logger.error(f"Error fetching products for {shop}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch products: {str(e)}",
        )


# Keep this for embedded apps that DO need session tokens
@router.get("/products/embedded")
async def get_shop_products_embedded(
    shop: str = Query(..., description="Shop domain"),
    limit: int = Query(50, le=100, description="Number of products to return"),
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get products for embedded apps (requires session token)
    Use this only if your app runs inside Shopify admin interface.
    """
    # Verify authorization header
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.split(" ", 1)[1]

    if not is_valid_shop_domain(shop):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
        )

    # Verify session token (this checks the JWT from Shopify)
    verify_session_token(token, shop)

    # Get shop record
    result = await session.execute(
        select(Shop).where(Shop.shop_domain == shop, Shop.uninstalled == False)
    )
    shop_record = result.scalar_one_or_none()

    if not shop_record or not shop_record.access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shop not found or access token missing",
        )

    # Fetch products using stored access token
    try:
        shopify_api = ShopifyAPI(shop, shop_record.access_token)
        products_data = await shopify_api.get_products_graphql(limit)

        # Track usage
        usage_record = ShopUsage(
            shop_domain=shop,
            metric_name="api_calls",
            metric_value=1,
            metric_data={"endpoint": "products_embedded", "limit": limit},
        )
        session.add(usage_record)
        await session.commit()

        return products_data

    except Exception as e:
        logger.error(f"Error fetching products for {shop}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch products: {str(e)}",
        )


# Bulk operations for multi-shop management
@router.post("/admin/bulk/products")
async def bulk_get_products(
    shop_domains: Optional[List[str]] = None,
    limit: int = Query(10, le=50, description="Products per shop"),
    max_shops: int = Query(10, le=50, description="Maximum shops to process"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get products from multiple shops (admin operation)
    """
    query = select(Shop).where(Shop.uninstalled == False)

    if shop_domains:
        query = query.where(Shop.shop_domain.in_(shop_domains))

    query = query.limit(max_shops)
    result = await session.execute(query)
    shops = result.scalars().all()

    results = {}

    for shop in shops:
        if not shop.access_token:
            results[shop.shop_domain] = {
                "shop_name": shop.shop_name,
                "error": "No access token available",
            }
            continue

        try:
            shopify_api = ShopifyAPI(shop.shop_domain, shop.access_token)
            products_data = await shopify_api.get_products_graphql(limit)

            results[shop.shop_domain] = {
                "shop_name": shop.shop_name,
                "products": products_data.get("data", {})
                .get("products", {})
                .get("edges", []),
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Error fetching products for {shop.shop_domain}: {e}")
            results[shop.shop_domain] = {"shop_name": shop.shop_name, "error": str(e)}

    return {"processed_shops": len(results), "results": results}


@router.get("/admin/usage")
async def get_usage_analytics(
    days: int = Query(7, le=30, description="Number of days to analyze"),
    metric: Optional[str] = Query(None, description="Filter by metric name"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get usage analytics across all shops
    """
    since = datetime.utcnow() - timedelta(days=days)

    query = select(
        ShopUsage.shop_domain,
        ShopUsage.metric_name,
        func.sum(ShopUsage.metric_value).label("total_value"),
        func.count(ShopUsage.id).label("count"),
    ).where(ShopUsage.date >= since)

    if metric:
        query = query.where(ShopUsage.metric_name == metric)

    query = query.group_by(ShopUsage.shop_domain, ShopUsage.metric_name)

    result = await session.execute(query)
    usage_data = {}

    for shop_domain, metric_name, total_value, count in result:
        if shop_domain not in usage_data:
            usage_data[shop_domain] = {}
        usage_data[shop_domain][metric_name] = {"total": total_value, "count": count}

    return {
        "period_days": days,
        "metric_filter": metric,
        "usage_by_shop": usage_data,
        "generated_at": datetime.utcnow(),
    }
