"""Tests for authentication middleware (task 10.1).

These tests verify the API key authentication functionality:
- API key verification
- Authentication enabled/disabled states
- Public route exemptions
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.auth import (
    PUBLIC_ROUTES,
    get_api_keys,
    is_auth_enabled,
    is_public_route,
    optional_verify_api_key,
    verify_api_key,
)


class TestAPIKeyConfiguration:
    """Tests for API key configuration loading."""

    def test_get_api_keys_no_env_var(self) -> None:
        """Test returns empty set when CON_API_KEYS not set."""
        # Clear cache first
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            keys = get_api_keys()
            assert keys == set()

    def test_get_api_keys_single_key(self) -> None:
        """Test loading single API key."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "test-key-123"}):
            keys = get_api_keys()
            assert keys == {"test-key-123"}

    def test_get_api_keys_multiple_keys(self) -> None:
        """Test loading multiple comma-separated API keys."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "key1,key2,key3"}):
            keys = get_api_keys()
            assert keys == {"key1", "key2", "key3"}

    def test_get_api_keys_strips_whitespace(self) -> None:
        """Test whitespace is stripped from keys."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": " key1 , key2 , key3 "}):
            keys = get_api_keys()
            assert keys == {"key1", "key2", "key3"}

    def test_get_api_keys_ignores_empty_values(self) -> None:
        """Test empty values in comma list are ignored."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "key1,,key2,  ,key3"}):
            keys = get_api_keys()
            assert keys == {"key1", "key2", "key3"}


class TestAuthEnabled:
    """Tests for authentication enabled state."""

    def test_auth_disabled_when_no_keys(self) -> None:
        """Test auth is disabled when no API keys configured."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            assert is_auth_enabled() is False

    def test_auth_enabled_when_keys_configured(self) -> None:
        """Test auth is enabled when API keys are configured."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "test-key"}):
            assert is_auth_enabled() is True


class TestVerifyAPIKey:
    """Tests for API key verification."""

    @pytest.mark.asyncio
    async def test_verify_api_key_valid(self) -> None:
        """Test valid API key is accepted."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "valid-key"}):
            result = await verify_api_key("valid-key")
            assert result == "valid-key"

    @pytest.mark.asyncio
    async def test_verify_api_key_invalid(self) -> None:
        """Test invalid API key is rejected."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "valid-key"}):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key("invalid-key")
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "Invalid API key"

    @pytest.mark.asyncio
    async def test_verify_api_key_missing(self) -> None:
        """Test missing API key raises 401."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "valid-key"}):
            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(None)
            assert exc_info.value.status_code == 401
            assert exc_info.value.detail == "API key required"

    @pytest.mark.asyncio
    async def test_verify_api_key_auth_disabled(self) -> None:
        """Test returns None when auth is disabled."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            result = await verify_api_key(None)
            assert result is None


class TestOptionalVerifyAPIKey:
    """Tests for optional API key verification."""

    @pytest.mark.asyncio
    async def test_optional_verify_returns_none_when_disabled(self) -> None:
        """Test returns None when auth is disabled."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            result = await optional_verify_api_key(None)
            assert result is None

    @pytest.mark.asyncio
    async def test_optional_verify_validates_when_enabled(self) -> None:
        """Test validates key when auth is enabled."""
        get_api_keys.cache_clear()
        with patch.dict(os.environ, {"CON_API_KEYS": "valid-key"}):
            result = await optional_verify_api_key("valid-key")
            assert result == "valid-key"


class TestPublicRoutes:
    """Tests for public route exemptions."""

    def test_health_is_public(self) -> None:
        """Test /health is a public route."""
        assert is_public_route("/health") is True

    def test_root_is_public(self) -> None:
        """Test / is a public route."""
        assert is_public_route("/") is True

    def test_docs_is_public(self) -> None:
        """Test /docs is a public route."""
        assert is_public_route("/docs") is True

    def test_api_routes_not_public(self) -> None:
        """Test API routes are not public."""
        assert is_public_route("/documents") is False
        assert is_public_route("/export/omop/P001") is False
        assert is_public_route("/patients/P001/graph") is False

    def test_public_routes_constant(self) -> None:
        """Test PUBLIC_ROUTES contains expected routes."""
        assert "/" in PUBLIC_ROUTES
        assert "/health" in PUBLIC_ROUTES
        assert "/docs" in PUBLIC_ROUTES
        assert "/redoc" in PUBLIC_ROUTES
        assert "/openapi.json" in PUBLIC_ROUTES
