"""Tests for privacy safeguards (Phase 10.4)."""

import pytest

from app.core.privacy import (
    PrivacyGuard,
    detect_potential_phi,
    is_synthetic_patient_id,
    sanitize_for_logging,
    validate_no_real_phi,
)


class TestSyntheticPatientIdDetection:
    """Tests for synthetic patient ID pattern matching."""

    def test_p_pattern_is_synthetic(self) -> None:
        """Test P001 pattern is recognized as synthetic."""
        assert is_synthetic_patient_id("P001")
        assert is_synthetic_patient_id("P123")
        assert is_synthetic_patient_id("P999")

    def test_test_pattern_is_synthetic(self) -> None:
        """Test TEST patterns are recognized as synthetic."""
        assert is_synthetic_patient_id("TEST1")
        assert is_synthetic_patient_id("TEST_1")
        assert is_synthetic_patient_id("TEST-1")

    def test_demo_pattern_is_synthetic(self) -> None:
        """Test DEMO patterns are recognized as synthetic."""
        assert is_synthetic_patient_id("DEMO1")
        assert is_synthetic_patient_id("DEMO_42")

    def test_sample_pattern_is_synthetic(self) -> None:
        """Test SAMPLE patterns are recognized as synthetic."""
        assert is_synthetic_patient_id("SAMPLE1")
        assert is_synthetic_patient_id("SAMPLE_123")

    def test_case_insensitive(self) -> None:
        """Test pattern matching is case insensitive."""
        assert is_synthetic_patient_id("p001")
        assert is_synthetic_patient_id("test1")
        assert is_synthetic_patient_id("Demo1")

    def test_non_synthetic_not_matched(self) -> None:
        """Test non-synthetic IDs are not matched."""
        assert not is_synthetic_patient_id("MRN123456")
        assert not is_synthetic_patient_id("12345678")
        assert not is_synthetic_patient_id("john-doe")
        assert not is_synthetic_patient_id("real-patient-id")


class TestPHIPatternDetection:
    """Tests for PHI pattern detection."""

    def test_detect_ssn_pattern(self) -> None:
        """Test SSN-like patterns are detected."""
        text = "Patient SSN: 123-45-6789"
        findings = detect_potential_phi(text)
        assert len(findings) > 0
        assert any("SSN" in desc for _, desc in findings)

    def test_detect_phone_pattern(self) -> None:
        """Test phone number patterns are detected."""
        text = "Contact: 555-123-4567"
        findings = detect_potential_phi(text)
        assert len(findings) > 0
        assert any("Phone" in desc for _, desc in findings)

    def test_detect_email_pattern(self) -> None:
        """Test email patterns are detected."""
        text = "Email: patient@example.com"
        findings = detect_potential_phi(text)
        assert len(findings) > 0
        assert any("Email" in desc for _, desc in findings)

    def test_detect_dob_pattern(self) -> None:
        """Test date of birth patterns are detected."""
        text = "DOB: 01/15/1990"
        findings = detect_potential_phi(text)
        assert len(findings) > 0
        assert any("DOB" in desc for _, desc in findings)

    def test_clean_clinical_text_passes(self) -> None:
        """Test clean clinical text has no findings."""
        text = "Patient presents with chest pain. History of hypertension."
        findings = detect_potential_phi(text)
        assert len(findings) == 0


class TestValidateNoRealPHI:
    """Tests for validate_no_real_phi function."""

    def test_synthetic_id_and_clean_text_passes(self) -> None:
        """Test synthetic ID with clean text passes validation."""
        result = validate_no_real_phi(
            text="Patient has diabetes.",
            patient_id="P001",
            warn_only=True,
        )
        assert result is True

    def test_non_synthetic_id_warns(self) -> None:
        """Test non-synthetic ID triggers warning."""
        result = validate_no_real_phi(
            text="Clean text.",
            patient_id="real-patient-123",
            warn_only=True,
        )
        assert result is False

    def test_phi_in_text_warns(self) -> None:
        """Test PHI in text triggers warning."""
        result = validate_no_real_phi(
            text="Contact: 555-123-4567",
            patient_id="P001",
            warn_only=True,
        )
        assert result is False

    def test_strict_mode_raises_on_phi(self) -> None:
        """Test strict mode raises ValueError on PHI."""
        with pytest.raises(ValueError, match="PHI validation failed"):
            validate_no_real_phi(
                text="SSN: 123-45-6789",
                patient_id="P001",
                warn_only=False,
            )

    def test_strict_mode_raises_on_non_synthetic(self) -> None:
        """Test strict mode raises ValueError on non-synthetic ID."""
        with pytest.raises(ValueError, match="PHI validation failed"):
            validate_no_real_phi(
                text="Clean text.",
                patient_id="real-patient",
                warn_only=False,
            )


class TestSanitizeForLogging:
    """Tests for sanitize_for_logging function."""

    def test_truncates_long_text(self) -> None:
        """Test long text is truncated."""
        long_text = "A" * 200
        result = sanitize_for_logging(long_text, max_length=50)
        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")

    def test_redacts_ssn_patterns(self) -> None:
        """Test SSN patterns are redacted."""
        text = "Patient SSN: 123-45-6789"
        result = sanitize_for_logging(text)
        assert "[REDACTED]" in result
        assert "123-45-6789" not in result

    def test_redacts_phone_patterns(self) -> None:
        """Test phone patterns are redacted."""
        text = "Call 555-123-4567"
        result = sanitize_for_logging(text)
        assert "[REDACTED]" in result
        assert "555-123-4567" not in result

    def test_short_clean_text_unchanged(self) -> None:
        """Test short clean text is returned unchanged."""
        text = "Patient has diabetes"
        result = sanitize_for_logging(text)
        assert result == text


class TestPrivacyGuard:
    """Tests for PrivacyGuard context manager."""

    def test_privacy_guard_synthetic_id_succeeds(self) -> None:
        """Test PrivacyGuard with synthetic ID succeeds."""
        with PrivacyGuard(patient_id="P001") as guard:
            result = guard.validate_text("Patient has diabetes.")
        assert result is True
        assert guard.validated is True

    def test_privacy_guard_non_synthetic_warns(self) -> None:
        """Test PrivacyGuard with non-synthetic ID logs warning."""
        # In non-strict mode, should not raise
        with PrivacyGuard(patient_id="real-patient", strict=False) as guard:
            result = guard.validate_text("Clean text.")
        assert result is False

    def test_privacy_guard_strict_raises(self) -> None:
        """Test PrivacyGuard strict mode raises on non-synthetic."""
        with pytest.raises(ValueError):
            with PrivacyGuard(patient_id="real-patient", strict=True):
                pass
