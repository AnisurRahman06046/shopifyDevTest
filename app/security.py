import re
import hmac
import hashlib
import base64
from typing import Mapping, Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.config import settings

# Shop domain validation regex
SHOP_DOMAIN_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*\.myshopify\.com$")


def is_valid_shop_domain(shop_domain: str) -> bool:
    """
    Validate Shopify shop domain format

    Args:
        shop_domain: Domain to validate (e.g., 'test-shop.myshopify.com')

    Returns:
        bool: True if valid domain format
    """
    if not shop_domain:
        return False
    return bool(SHOP_DOMAIN_REGEX.match(shop_domain))


def verify_oauth_hmac(query_params: Mapping[str, str]) -> bool:
    """
    Verify HMAC signature for OAuth callback

    Args:
        query_params: Query parameters from OAuth callback

    Returns:
        bool: True if HMAC is valid
    """
    params = dict(query_params)
    received_hmac = params.pop("hmac", None)
    params.pop("signature", None)  # Remove signature if present

    if not received_hmac:
        return False

    # Build sorted query string for HMAC calculation
    sorted_params = sorted(params.items())
    query_string = "&".join(f"{key}={value}" for key, value in sorted_params)

    # Calculate HMAC
    calculated_hmac = hmac.new(
        settings.shopify_api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Compare HMACs using constant-time comparison
    return hmac.compare_digest(calculated_hmac, received_hmac)


def verify_webhook_hmac(raw_body: bytes, hmac_header: Optional[str]) -> bool:
    """
    Verify HMAC signature for webhook requests

    Args:
        raw_body: Raw request body bytes
        hmac_header: HMAC header value (base64 encoded)

    Returns:
        bool: True if HMAC is valid
    """
    if not hmac_header:
        return False

    # Calculate HMAC of raw body
    calculated_hmac = hmac.new(
        settings.shopify_api_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).digest()

    # Encode as base64
    calculated_hmac_b64 = base64.b64encode(calculated_hmac).decode("utf-8")

    # Compare with received HMAC
    return hmac.compare_digest(calculated_hmac_b64, hmac_header)


def verify_session_token(token: str, expected_shop: str) -> dict:
    """
    Verify and decode Shopify session token (JWT)

    Args:
        token: JWT session token
        expected_shop: Expected shop domain

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.shopify_api_secret,
            algorithms=[settings.algorithm],
            audience=settings.shopify_api_key,
            options={"verify_aud": True, "verify_exp": True, "verify_signature": True},
        )

        # Verify shop domain matches
        dest = payload.get("dest") or payload.get("iss", "")
        if expected_shop not in dest:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session token shop mismatch",
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session token: {str(e)}",
        )


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in token

    Returns:
        str: Encoded JWT token
    """
    return jwt.encode(data, settings.secret_key, algorithm=settings.algorithm)


def verify_access_token(token: str) -> dict:
    """
    Verify and decode access token

    Args:
        token: JWT access token

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )
