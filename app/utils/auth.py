from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from urllib.parse import urlencode
from datetime import datetime
import logging

from app.database import get_db_session
from app.models import Shop, OAuthState
from app.security import is_valid_shop_domain, verify_oauth_hmac
from app.utils.oauth import (
    generate_state,
    build_oauth_authorize_url,
    build_redirect_uri,
)
from app.utils.shopify_api import exchange_code_for_token, ShopifyAPI
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/install")
async def install_app(shop: str, session: AsyncSession = Depends(get_db_session)):
    """
    Start OAuth installation flow

    Args:
        shop: Shopify shop domain (e.g., 'test-shop.myshopify.com')
    """
    # Validate shop domain
    if not is_valid_shop_domain(shop):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain format"
        )

    # Generate secure state for OAuth
    state = generate_state()

    # Store state in database for verification
    oauth_state = OAuthState(state=state, shop_domain=shop)
    session.add(oauth_state)
    await session.commit()

    logger.info(f"Starting OAuth flow for shop: {shop}")

    # Build OAuth authorization URL
    redirect_uri = build_redirect_uri("/auth/callback")
    auth_url = build_oauth_authorize_url(shop, state, redirect_uri)

    # Redirect to Shopify OAuth
    return RedirectResponse(url=auth_url, status_code=307)


@router.get("/callback")
async def oauth_callback(
    request: Request, session: AsyncSession = Depends(get_db_session)
):
    """
    Handle OAuth callback from Shopify
    """
    # Extract query parameters
    query_params = dict(request.query_params)
    shop_domain = query_params.get("shop")
    code = query_params.get("code")
    state = query_params.get("state")

    # Validate required parameters
    if not all([shop_domain, code, state]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required OAuth parameters",
        )

    if not is_valid_shop_domain(shop_domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
        )

    # Verify HMAC signature
    if not verify_oauth_hmac(query_params):
        logger.warning(f"Invalid HMAC for shop: {shop_domain}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC signature"
        )

    # Verify and consume OAuth state
    result = await session.execute(
        select(OAuthState).where(
            OAuthState.state == state, OAuthState.shop_domain == shop_domain
        )
    )
    oauth_state_record = result.scalar_one_or_none()

    if not oauth_state_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OAuth state",
        )

    # Delete used state (one-time use)
    await session.execute(delete(OAuthState).where(OAuthState.state == state))
    await session.commit()

    try:
        # Exchange code for access token
        token_data = await exchange_code_for_token(shop_domain, code)
        access_token = token_data.get("access_token")
        scope = token_data.get("scope", "")

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token",
            )

        # Fetch shop details from Shopify API
        shop_api = ShopifyAPI(shop_domain, access_token)
        shop_info_response = await shop_api.get_shop_info()
        shop_info = shop_info_response.get("shop", {})

        # Create or update shop record
        result = await session.execute(
            select(Shop).where(Shop.shop_domain == shop_domain)
        )
        shop_record = result.scalar_one_or_none()

        now = datetime.utcnow()

        if shop_record:
            # Update existing shop
            shop_record.access_token = access_token
            shop_record.scopes = scope
            shop_record.uninstalled = False
            shop_record.uninstalled_at = None
            shop_record.last_seen_at = now
            shop_record.updated_at = now
            # Update shop info
            update_shop_info(shop_record, shop_info)
            logger.info(f"Updated shop record for: {shop_domain}")
        else:
            # Create new shop record
            shop_record = Shop(
                shop_domain=shop_domain,
                access_token=access_token,
                scopes=scope,
                installed_at=now,
                last_seen_at=now,
                uninstalled=False,
            )
            update_shop_info(shop_record, shop_info)
            session.add(shop_record)
            logger.info(f"Created new shop record for: {shop_domain}")

        await session.commit()

        # Log successful installation
        logger.info(f"Successfully installed app for shop: {shop_domain}")
        logger.info(f"Shop name: {shop_info.get('name', 'Unknown')}")
        logger.info(f"Plan: {shop_info.get('plan_display_name', 'Unknown')}")

        # Redirect to success page
        params = urlencode({"shop": shop_domain})
        return RedirectResponse(
            url=f"{settings.app_url}/auth/success?{params}", status_code=307
        )

    except Exception as e:
        logger.error(f"OAuth callback error for shop {shop_domain}: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Installation failed: {str(e)}",
        )


@router.get("/success", response_class=HTMLResponse)
async def installation_success(
    shop: str, session: AsyncSession = Depends(get_db_session)
):
    """
    Display installation success page
    """
    if not is_valid_shop_domain(shop):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid shop domain"
        )

    # Verify shop is installed
    result = await session.execute(
        select(Shop).where(Shop.shop_domain == shop, Shop.uninstalled == False)
    )
    shop_record = result.scalar_one_or_none()

    if not shop_record:
        return HTMLResponse(
            content="""
            <html>
                <head><title>Installation Failed</title></head>
                <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                    <h1 style="color: #dc3545;">❌ Installation Failed</h1>
                    <p>There was an error installing the app. Please try again.</p>
                    <a href="javascript:history.back()" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Go Back
                    </a>
                </body>
            </html>
            """,
            status_code=400,
        )

    return HTMLResponse(
        content=f"""
        <html>
            <head>
                <title>App Installed Successfully!</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px;">
                <div style="text-align: center; background: #f8f9fa; padding: 30px; border-radius: 10px; border: 1px solid #dee2e6;">
                    <h1 style="color: #28a745; margin-bottom: 20px;">✅ App Installed Successfully!</h1>
                    
                    <div style="text-align: left; background: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Installation Details:</h3>
                        <p><strong>Shop:</strong> {shop}</p>
                        <p><strong>Shop Name:</strong> {shop_record.shop_name or 'Loading...'}</p>
                        <p><strong>Plan:</strong> {shop_record.plan_display_name or 'Loading...'}</p>
                        <p><strong>Country:</strong> {shop_record.country_name or shop_record.country_code or 'Loading...'}</p>
                        <p><strong>Scopes:</strong> {shop_record.scopes or 'None'}</p>
                        <p><strong>Installed:</strong> {shop_record.installed_at.strftime('%Y-%m-%d %H:%M:%S') if shop_record.installed_at else 'Unknown'}</p>
                    </div>
                    
                    <div style="text-align: left; background: #e8f4f8; padding: 20px; border-radius: 5px; margin: 20px 0;">
                        <h3>Next Steps:</h3>
                        <ul>
                            <li>Your app is now installed and ready to use</li>
                            <li>You can access the app from your Shopify admin</li>
                            <li>API endpoints are available for integration</li>
                            <li>Check the developer console for API usage</li>
                        </ul>
                    </div>
                    
                    <div style="margin: 30px 0;">
                        <a href="https://{shop}/admin" 
                           style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px; display: inline-block;">
                            Return to Shopify Admin
                        </a>
                        <a href="{settings.app_url}/docs" 
                           style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px; display: inline-block;">
                            View API Documentation
                        </a>
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 14px; color: #6c757d;">
                        <p>App URL: <code>{settings.app_url}</code></p>
                        <p>Environment: {settings.environment}</p>
                    </div>
                </div>
            </body>
        </html>
        """
    )


def update_shop_info(shop_record: Shop, shop_info: dict):
    """
    Update shop record with information from Shopify API

    Args:
        shop_record: Shop database record
        shop_info: Shop information from Shopify API
    """
    shop_record.shop_name = shop_info.get("name")
    shop_record.shop_email = shop_info.get("email")
    shop_record.shop_owner = shop_info.get("shop_owner")
    shop_record.country_code = shop_info.get("country_code")
    shop_record.country_name = shop_info.get("country_name")
    shop_record.currency = shop_info.get("currency")
    shop_record.timezone = shop_info.get("iana_timezone")
    shop_record.primary_locale = shop_info.get("primary_locale")
    shop_record.plan_name = shop_info.get("plan_name")
    shop_record.plan_display_name = shop_info.get("plan_display_name")
    shop_record.primary_domain = shop_info.get("domain")
    shop_record.myshopify_domain = shop_info.get("myshopify_domain")
