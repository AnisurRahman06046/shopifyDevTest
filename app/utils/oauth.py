import secrets
from urllib.parse import urlencode
from typing import List
from app.config import settings


def generate_state() -> str:
    """
    Generate a cryptographically secure random state for OAuth

    Returns:
        str: Random state string
    """
    return secrets.token_urlsafe(32)


def build_oauth_authorize_url(
    shop_domain: str, state: str, redirect_uri: str, scopes: List[str] = None
) -> str:
    """
    Build Shopify OAuth authorization URL

    Args:
        shop_domain: Shopify shop domain
        state: OAuth state parameter
        redirect_uri: Callback URL
        scopes: List of OAuth scopes (optional)

    Returns:
        str: Complete OAuth authorization URL
    """
    if scopes is None:
        scopes = settings.shopify_scopes_list

    params = {
        "client_id": settings.shopify_api_key,
        "scope": ",".join(scopes),
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
    }

    query_string = urlencode(params)
    return f"https://{shop_domain}/admin/oauth/authorize?{query_string}"


def build_redirect_uri(endpoint: str = "/auth/callback") -> str:
    """
    Build the OAuth redirect URI

    Args:
        endpoint: Callback endpoint path

    Returns:
        str: Complete redirect URI
    """
    return f"{settings.app_url.rstrip('/')}{endpoint}"


def parse_scopes(scope_string: str) -> List[str]:
    """
    Parse comma-separated scope string to list

    Args:
        scope_string: Comma-separated scopes

    Returns:
        List[str]: List of individual scopes
    """
    if not scope_string:
        return []
    return [scope.strip() for scope in scope_string.split(",")]
