"""Basic authentication middleware for Clinical Ontology Normalizer.

Provides API key-based authentication for secure access to endpoints.
In production, this should be replaced with a more robust solution
(OAuth2, JWT tokens, etc.).
"""

import logging
import os
from functools import lru_cache

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# API key header configuration
API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


@lru_cache
def get_api_keys() -> set[str]:
    """Get configured API keys from environment.

    API keys should be set via the CON_API_KEYS environment variable
    as a comma-separated list.

    Returns:
        Set of valid API keys
    """
    api_keys_str = os.environ.get("CON_API_KEYS", "")
    if not api_keys_str:
        logger.warning(
            "No API keys configured (CON_API_KEYS not set). "
            "Authentication is disabled for development."
        )
        return set()

    keys = {k.strip() for k in api_keys_str.split(",") if k.strip()}
    logger.info(f"Loaded {len(keys)} API key(s) for authentication")
    return keys


def is_auth_enabled() -> bool:
    """Check if authentication is enabled.

    Authentication is enabled when API keys are configured.

    Returns:
        True if authentication is enabled
    """
    return len(get_api_keys()) > 0


async def verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str | None:
    """Verify API key from request header.

    This dependency checks the X-API-Key header against configured keys.
    If no keys are configured, authentication is disabled (dev mode).

    Args:
        api_key: API key from request header

    Returns:
        The verified API key if valid

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    api_keys = get_api_keys()

    # If no API keys configured, skip authentication (dev mode)
    if not api_keys:
        return None

    # Check if API key is provided
    if api_key is None:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key
    if api_key not in api_keys:
        logger.warning("Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug("API key verified successfully")
    return api_key


# Optional dependency that doesn't raise error when auth is disabled
async def optional_verify_api_key(
    api_key: str | None = Security(api_key_header),
) -> str | None:
    """Optionally verify API key, returning None if auth is disabled.

    Unlike verify_api_key, this does not raise an error when authentication
    is disabled. Use this for routes that should work both with and without
    authentication.

    Args:
        api_key: API key from request header

    Returns:
        The verified API key, or None if auth is disabled
    """
    if not is_auth_enabled():
        return None
    return await verify_api_key(api_key)


def require_api_key() -> None:
    """Dependency marker indicating route requires authentication.

    Use this in route definitions to clearly mark protected routes:

        @router.get("/protected", dependencies=[Depends(require_api_key)])
        def protected_route():
            ...
    """
    pass


# Public routes that don't require authentication
PUBLIC_ROUTES = frozenset({
    "/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
})


def is_public_route(path: str) -> bool:
    """Check if a route path is public (no auth required).

    Args:
        path: The request path

    Returns:
        True if the route is public
    """
    return path in PUBLIC_ROUTES
