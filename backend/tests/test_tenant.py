"""Tests for tenant/patient isolation (task 10.2).

These tests verify tenant isolation functionality:
- Tenant-patient mapping configuration
- Patient access verification
- TenantContext behavior
"""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.tenant import (
    TenantContext,
    get_allowed_patients,
    get_tenant_patient_mapping,
    is_tenant_isolation_enabled,
    verify_document_access,
    verify_patient_access,
)


class TestTenantPatientMapping:
    """Tests for tenant-patient mapping configuration."""

    def test_no_mappings_configured(self) -> None:
        """Test returns empty dict when no mappings configured."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            mapping = get_tenant_patient_mapping()
            assert mapping == {}

    def test_single_tenant_mapping(self) -> None:
        """Test loading single tenant with patients."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001,P002"}, clear=True
        ):
            mapping = get_tenant_patient_mapping()
            assert "KEY1" in mapping
            assert mapping["KEY1"] == {"P001", "P002"}

    def test_multiple_tenant_mappings(self) -> None:
        """Test loading multiple tenants."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ,
            {
                "CON_TENANT_KEY1_PATIENTS": "P001,P002",
                "CON_TENANT_KEY2_PATIENTS": "P003,P004",
            },
            clear=True,
        ):
            mapping = get_tenant_patient_mapping()
            assert mapping["KEY1"] == {"P001", "P002"}
            assert mapping["KEY2"] == {"P003", "P004"}

    def test_strips_whitespace(self) -> None:
        """Test whitespace is stripped from patient IDs."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": " P001 , P002 "}, clear=True
        ):
            mapping = get_tenant_patient_mapping()
            assert mapping["KEY1"] == {"P001", "P002"}

    def test_ignores_empty_values(self) -> None:
        """Test empty patient IDs are ignored."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001,,P002,  ,"}, clear=True
        ):
            mapping = get_tenant_patient_mapping()
            assert mapping["KEY1"] == {"P001", "P002"}


class TestTenantIsolationEnabled:
    """Tests for tenant isolation enabled state."""

    def test_disabled_when_no_mappings(self) -> None:
        """Test isolation is disabled when no mappings configured."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            assert is_tenant_isolation_enabled() is False

    def test_enabled_when_mappings_exist(self) -> None:
        """Test isolation is enabled when mappings configured."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            assert is_tenant_isolation_enabled() is True


class TestGetAllowedPatients:
    """Tests for get_allowed_patients function."""

    def test_returns_none_for_no_api_key(self) -> None:
        """Test returns None when no API key provided."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            assert get_allowed_patients(None) is None

    def test_returns_none_when_no_mappings(self) -> None:
        """Test returns None when no tenant mappings configured."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            assert get_allowed_patients("KEY1") is None

    def test_returns_patients_for_known_key(self) -> None:
        """Test returns patients for configured API key."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001,P002"}, clear=True
        ):
            patients = get_allowed_patients("KEY1")
            assert patients == {"P001", "P002"}

    def test_returns_none_for_unknown_key(self) -> None:
        """Test returns None for unconfigured API key."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            assert get_allowed_patients("UNKNOWN") is None


class TestVerifyPatientAccess:
    """Tests for patient access verification."""

    def test_allows_access_when_no_api_key(self) -> None:
        """Test allows access when no API key (auth disabled)."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            # Should not raise
            verify_patient_access(None, "P002")

    def test_allows_access_when_no_mappings(self) -> None:
        """Test allows access when no tenant mappings configured."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            # Should not raise
            verify_patient_access("KEY1", "P001")

    def test_allows_access_to_allowed_patient(self) -> None:
        """Test allows access to patient in allowed list."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001,P002"}, clear=True
        ):
            # Should not raise
            verify_patient_access("KEY1", "P001")

    def test_denies_access_to_disallowed_patient(self) -> None:
        """Test denies access to patient not in allowed list."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001,P002"}, clear=True
        ):
            with pytest.raises(HTTPException) as exc_info:
                verify_patient_access("KEY1", "P999")
            assert exc_info.value.status_code == 403
            assert "not authorized" in exc_info.value.detail

    def test_allows_access_for_unconfigured_key(self) -> None:
        """Test allows access when API key has no specific mapping."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            # KEY2 is not in mappings, so no restrictions
            verify_patient_access("KEY2", "P999")


class TestVerifyDocumentAccess:
    """Tests for document access verification."""

    def test_verifies_patient_access(self) -> None:
        """Test document access verification checks patient access."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            with pytest.raises(HTTPException) as exc_info:
                verify_document_access("KEY1", "P002", "doc-123")
            assert exc_info.value.status_code == 403


class TestTenantContext:
    """Tests for TenantContext class."""

    def test_context_stores_api_key(self) -> None:
        """Test context stores API key."""
        ctx = TenantContext(api_key="KEY1")
        assert ctx.api_key == "KEY1"

    def test_context_default_tenant_id(self) -> None:
        """Test tenant_id defaults to api_key."""
        ctx = TenantContext(api_key="KEY1")
        assert ctx.tenant_id == "KEY1"

    def test_context_custom_tenant_id(self) -> None:
        """Test custom tenant_id."""
        ctx = TenantContext(api_key="KEY1", tenant_id="TENANT1")
        assert ctx.tenant_id == "TENANT1"

    def test_context_can_access_patient_no_restrictions(self) -> None:
        """Test can_access_patient returns True when no restrictions."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            ctx = TenantContext(api_key="KEY1")
            assert ctx.can_access_patient("P001") is True

    def test_context_can_access_allowed_patient(self) -> None:
        """Test can_access_patient returns True for allowed patient."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001,P002"}, clear=True
        ):
            ctx = TenantContext(api_key="KEY1")
            assert ctx.can_access_patient("P001") is True

    def test_context_cannot_access_disallowed_patient(self) -> None:
        """Test can_access_patient returns False for disallowed patient."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            ctx = TenantContext(api_key="KEY1")
            assert ctx.can_access_patient("P999") is False

    def test_context_verify_raises_on_denied(self) -> None:
        """Test verify_patient_access raises when denied."""
        get_tenant_patient_mapping.cache_clear()
        with patch.dict(
            os.environ, {"CON_TENANT_KEY1_PATIENTS": "P001"}, clear=True
        ):
            ctx = TenantContext(api_key="KEY1")
            with pytest.raises(HTTPException) as exc_info:
                ctx.verify_patient_access("P999")
            assert exc_info.value.status_code == 403
