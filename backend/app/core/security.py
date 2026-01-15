"""Security and authentication middleware."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

# API Key header security scheme
api_key_header = APIKeyHeader(
    name=settings.api_key_header,
    auto_error=False,  # Don't auto-error, we handle it manually
)


def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
) -> str | None:
    """Verify API key if authentication is enabled.

    When auth is enabled:
    - Missing API key returns 401
    - Invalid API key returns 403

    When auth is disabled:
    - Returns None (no authentication required)

    Args:
        api_key: The API key from the request header

    Returns:
        The validated API key or None if auth disabled

    Raises:
        HTTPException: 401 if missing key, 403 if invalid key
    """
    if not settings.auth_enabled:
        return None

    if api_key is None:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.api_key:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key


# Dependency for protected endpoints
RequireAuth = Annotated[str | None, Depends(verify_api_key)]


class TenantContext:
    """Context for tenant/patient isolation.

    Tracks the current tenant (patient) context for data access.
    Used to enforce isolation between patient data.
    """

    def __init__(self, tenant_id: str | None = None):
        """Initialize tenant context.

        Args:
            tenant_id: The tenant/patient ID for this request
        """
        self.tenant_id = tenant_id

    def is_authorized_for(self, patient_id: str) -> bool:
        """Check if current context is authorized to access patient data.

        Args:
            patient_id: The patient ID to check access for

        Returns:
            True if authorized, False otherwise
        """
        # If no tenant restriction, allow all (dev mode)
        if self.tenant_id is None:
            return True

        # Only allow access to own data
        return self.tenant_id == patient_id


def get_tenant_context() -> TenantContext:
    """Get tenant context for the current request.

    In a real implementation, this would extract tenant info
    from the authenticated user/token.

    Returns:
        TenantContext for isolation enforcement
    """
    # For now, return unrestricted context (dev mode)
    # In production, this would come from JWT claims or similar
    return TenantContext(tenant_id=None)


RequireTenant = Annotated[TenantContext, Depends(get_tenant_context)]
