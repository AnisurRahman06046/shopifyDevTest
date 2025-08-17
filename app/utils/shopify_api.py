import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException
import asyncio
import logging

logger = logging.getLogger(__name__)

# API version to use
API_VERSION = "2023-10"


class ShopifyAPI:
    """Shopify API client for REST and GraphQL requests"""

    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.base_url = f"https://{shop_domain}/admin/api/{API_VERSION}"

    async def graphql_request(
        self, query: str, variables: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make a GraphQL request to Shopify

        Args:
            query: GraphQL query string
            variables: Query variables (optional)

        Returns:
            dict: GraphQL response data

        Raises:
            HTTPException: If request fails
        """
        url = f"{self.base_url}/graphql.json"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                data = response.json()

                # Check for GraphQL errors
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    raise HTTPException(
                        status_code=400, detail=f"GraphQL errors: {data['errors']}"
                    )

                return data

            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise HTTPException(status_code=500, detail=f"Request failed: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error: {e.response.status_code} - {e.response.text}"
                )
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Shopify API error: {e.response.text}",
                )

    async def rest_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make a REST API request to Shopify

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., 'products.json')
            data: Request data for POST/PUT (optional)
            params: Query parameters (optional)

        Returns:
            dict: REST API response data

        Raises:
            HTTPException: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = await client.post(
                        url, headers=headers, json=data, params=params
                    )
                elif method.upper() == "PUT":
                    response = await client.put(
                        url, headers=headers, json=data, params=params
                    )
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                # Handle empty responses
                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                raise HTTPException(status_code=500, detail=f"Request failed: {e}")
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error: {e.response.status_code} - {e.response.text}"
                )
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Shopify API error: {e.response.text}",
                )

    async def get_shop_info(self) -> Dict[str, Any]:
        """Get shop information"""
        return await self.rest_request("GET", "shop.json")

    async def get_products(self, limit: int = 50) -> Dict[str, Any]:
        """Get products via REST API"""
        return await self.rest_request("GET", "products.json", params={"limit": limit})

    async def get_products_graphql(self, limit: int = 50) -> Dict[str, Any]:
        """Get products via GraphQL"""
        query = """
        query getProducts($first: Int!) {
            products(first: $first) {
                edges {
                    node {
                        id
                        title
                        status
                        totalInventory
                        vendor
                        productType
                        createdAt
                        updatedAt
                        images(first: 1) {
                            edges {
                                node {
                                    id
                                    url
                                    altText
                                }
                            }
                        }
                        variants(first: 5) {
                            edges {
                                node {
                                    id
                                    title
                                    price
                                    sku
                                    inventoryQuantity
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """
        return await self.graphql_request(query, {"first": limit})


# Convenience functions for backward compatibility
async def make_graphql_request(
    shop_domain: str, access_token: str, query: str, variables: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make a GraphQL request (convenience function)"""
    api = ShopifyAPI(shop_domain, access_token)
    return await api.graphql_request(query, variables)


async def make_rest_request(
    shop_domain: str,
    access_token: str,
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Make a REST API request (convenience function)"""
    api = ShopifyAPI(shop_domain, access_token)
    return await api.rest_request(method, endpoint, data, params)


async def exchange_code_for_token(shop_domain: str, code: str) -> Dict[str, Any]:
    """
    Exchange OAuth code for access token

    Args:
        shop_domain: Shopify shop domain
        code: OAuth authorization code

    Returns:
        dict: Token response data

    Raises:
        HTTPException: If exchange fails
    """
    from app.config import settings

    url = f"https://{shop_domain}/admin/oauth/access_token"
    payload = {
        "client_id": settings.shopify_api_key,
        "client_secret": settings.shopify_api_secret,
        "code": code,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

        except httpx.RequestError as e:
            logger.error(f"Token exchange request error: {e}")
            raise HTTPException(status_code=500, detail=f"Token exchange failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Token exchange HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Token exchange failed: {e.response.text}",
            )
