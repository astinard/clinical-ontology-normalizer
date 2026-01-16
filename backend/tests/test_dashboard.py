"""Tests for role-based dashboard endpoints."""

import pytest
from datetime import datetime

from app.schemas.dashboard import (
    ActionItem,
    AdminDashboardResponse,
    BillerDashboardResponse,
    CERCitationSummary,
    DashboardMetadata,
    DiagnosisSummary,
    EntityDistribution,
    ErrorSummary,
    HCCOpportunitySummary,
    ProcessingMetricsSummary,
    ProviderDashboardResponse,
    QualityDashboardResponse,
    RiskScoreSummary,
    ServiceHealthSummary,
    SystemStatsSummary,
)


# ============================================================================
# Schema Tests
# ============================================================================


class TestDashboardMetadata:
    """Test DashboardMetadata schema."""

    def test_create_metadata(self):
        """Test creating metadata."""
        meta = DashboardMetadata(
            generated_at=datetime.now(),
            patient_id="PT-001",
            time_window="24h",
        )
        assert meta.patient_id == "PT-001"
        assert meta.time_window == "24h"

    def test_metadata_optional_patient(self):
        """Test metadata with optional patient_id."""
        meta = DashboardMetadata(
            generated_at=datetime.now(),
        )
        assert meta.patient_id is None
        assert meta.time_window == "24h"  # Default


class TestActionItem:
    """Test ActionItem schema."""

    def test_create_action(self):
        """Test creating action item."""
        action = ActionItem(
            priority="high",
            title="Review HCC Opportunity",
            description="Diabetes with complications not coded",
            category="hcc",
            patient_id="PT-001",
            estimated_impact="$4,500/year",
        )
        assert action.priority == "high"
        assert action.category == "hcc"

    def test_action_optional_fields(self):
        """Test action with optional fields."""
        action = ActionItem(
            priority="medium",
            title="Quality Alert",
            description="Error rate above threshold",
            category="quality",
        )
        assert action.patient_id is None
        assert action.estimated_impact is None


class TestCERCitationSummary:
    """Test CER citation summary schema."""

    def test_create_cer(self):
        """Test creating CER citation summary."""
        cer = CERCitationSummary(
            claim="Patient has diabetes with nephropathy",
            strength="HIGH",
            evidence_count=3,
        )
        assert cer.claim == "Patient has diabetes with nephropathy"
        assert cer.strength == "HIGH"
        assert cer.evidence_count == 3


# ============================================================================
# Provider Dashboard Schema Tests
# ============================================================================


class TestProviderDashboardSchema:
    """Test provider dashboard schema."""

    def test_create_diagnosis_summary(self):
        """Test diagnosis summary."""
        dx = DiagnosisSummary(
            name="Type 2 Diabetes Mellitus",
            probability=0.85,
            urgency="routine",
            icd10_code="E11.9",
        )
        assert dx.probability == 0.85
        assert dx.icd10_code == "E11.9"

    def test_create_risk_score(self):
        """Test risk score summary."""
        score = RiskScoreSummary(
            calculator_name="Framingham CVD",
            risk_level="moderate",
            score_value=15.2,
            interpretation="15.2% 10-year cardiovascular risk",
        )
        assert score.risk_level == "moderate"
        assert score.score_value == 15.2

    def test_create_provider_response(self):
        """Test full provider dashboard response."""
        response = ProviderDashboardResponse(
            metadata=DashboardMetadata(generated_at=datetime.now()),
            stats={"total_calculators": 10},
        )
        assert response.clinical_summary is None
        assert response.differential_diagnoses == []
        assert "total_calculators" in response.stats


# ============================================================================
# Biller Dashboard Schema Tests
# ============================================================================


class TestBillerDashboardSchema:
    """Test biller dashboard schema."""

    def test_create_hcc_opportunity(self):
        """Test HCC opportunity summary."""
        opp = HCCOpportunitySummary(
            hcc_code="HCC37",
            description="Diabetes with Chronic Complications",
            gap_type="not_coded",
            confidence="high",
            estimated_revenue=4348.80,
            recommended_icd10="E11.21",
        )
        assert opp.hcc_code == "HCC37"
        assert opp.estimated_revenue == 4348.80
        assert opp.confidence == "high"

    def test_create_biller_response(self):
        """Test full biller dashboard response."""
        response = BillerDashboardResponse(
            metadata=DashboardMetadata(generated_at=datetime.now()),
            hcc_opportunities=[
                HCCOpportunitySummary(
                    hcc_code="HCC37",
                    description="Diabetes",
                    gap_type="not_coded",
                    confidence="high",
                    estimated_revenue=4500.00,
                )
            ],
            revenue_summary={
                "total_potential_revenue": 4500.00,
                "high_confidence_opportunities": 1,
            },
        )
        assert len(response.hcc_opportunities) == 1
        assert response.revenue_summary["total_potential_revenue"] == 4500.00


# ============================================================================
# Quality Dashboard Schema Tests
# ============================================================================


class TestQualityDashboardSchema:
    """Test quality dashboard schema."""

    def test_create_processing_metrics(self):
        """Test processing metrics summary."""
        metrics = ProcessingMetricsSummary(
            documents_processed=100,
            avg_processing_time_ms=250.5,
            total_extractions=500,
            avg_confidence=0.85,
            error_rate=0.02,
        )
        assert metrics.documents_processed == 100
        assert metrics.avg_confidence == 0.85
        assert metrics.error_rate == 0.02

    def test_create_entity_distribution(self):
        """Test entity distribution."""
        dist = EntityDistribution(
            conditions=50,
            drugs=30,
            measurements=20,
            procedures=10,
            observations=5,
        )
        assert dist.conditions == 50
        assert dist.drugs == 30

    def test_create_error_summary(self):
        """Test error summary."""
        err = ErrorSummary(
            error_type="extraction_failed",
            count=5,
            percentage=2.5,
        )
        assert err.error_type == "extraction_failed"
        assert err.percentage == 2.5

    def test_create_quality_response(self):
        """Test full quality dashboard response."""
        response = QualityDashboardResponse(
            metadata=DashboardMetadata(generated_at=datetime.now()),
            processing_metrics=ProcessingMetricsSummary(
                documents_processed=100,
                avg_processing_time_ms=250.0,
                total_extractions=500,
                avg_confidence=0.85,
                error_rate=0.02,
            ),
        )
        assert response.processing_metrics.documents_processed == 100


# ============================================================================
# Admin Dashboard Schema Tests
# ============================================================================


class TestAdminDashboardSchema:
    """Test admin dashboard schema."""

    def test_create_service_health(self):
        """Test service health summary."""
        health = ServiceHealthSummary(
            service_name="hcc_analyzer",
            status="healthy",
            stats={"total_hcc_definitions": 10},
        )
        assert health.service_name == "hcc_analyzer"
        assert health.status == "healthy"

    def test_create_system_stats(self):
        """Test system stats summary."""
        stats = SystemStatsSummary(
            total_patients=1000,
            total_documents=5000,
            total_extractions=25000,
            documents_today=50,
            documents_this_week=350,
        )
        assert stats.total_patients == 1000
        assert stats.total_documents == 5000

    def test_create_admin_response(self):
        """Test full admin dashboard response."""
        response = AdminDashboardResponse(
            metadata=DashboardMetadata(generated_at=datetime.now()),
            system_stats=SystemStatsSummary(
                total_patients=100,
                total_documents=500,
                total_extractions=2500,
                documents_today=10,
                documents_this_week=70,
            ),
            service_health=[
                ServiceHealthSummary(
                    service_name="hcc_analyzer",
                    status="healthy",
                    stats={},
                ),
            ],
        )
        assert response.system_stats.total_patients == 100
        assert len(response.service_health) == 1


# ============================================================================
# Integration-Style Tests (Schema Validation)
# ============================================================================


class TestDashboardIntegration:
    """Integration-style tests for dashboard schemas."""

    def test_full_provider_workflow(self):
        """Test complete provider dashboard workflow."""
        # Simulate what the API would return
        response = ProviderDashboardResponse(
            metadata=DashboardMetadata(
                generated_at=datetime.now(),
                patient_id="PT-001",
            ),
            differential_diagnoses=[
                DiagnosisSummary(
                    name="Type 2 Diabetes",
                    probability=0.9,
                    urgency="routine",
                    icd10_code="E11.9",
                    cer_citation=CERCitationSummary(
                        claim="Patient shows classic DM2 symptoms",
                        strength="HIGH",
                        evidence_count=4,
                    ),
                ),
            ],
            risk_scores=[
                RiskScoreSummary(
                    calculator_name="Framingham CVD",
                    risk_level="moderate",
                    score_value=12.5,
                    interpretation="12.5% 10-year risk",
                ),
            ],
            action_items=[
                ActionItem(
                    priority="high",
                    title="Review cardiovascular risk",
                    description="Patient has moderate CVD risk",
                    category="clinical",
                ),
            ],
            stats={"calculators_available": 10},
        )

        assert response.metadata.patient_id == "PT-001"
        assert len(response.differential_diagnoses) == 1
        assert response.differential_diagnoses[0].cer_citation.strength == "HIGH"
        assert len(response.risk_scores) == 1
        assert len(response.action_items) == 1

    def test_full_biller_workflow(self):
        """Test complete biller dashboard workflow."""
        response = BillerDashboardResponse(
            metadata=DashboardMetadata(
                generated_at=datetime.now(),
                patient_id="PT-002",
            ),
            hcc_opportunities=[
                HCCOpportunitySummary(
                    hcc_code="HCC37",
                    description="Diabetes with Chronic Complications",
                    gap_type="not_coded",
                    confidence="high",
                    estimated_revenue=4348.80,
                    recommended_icd10="E11.21",
                ),
                HCCOpportunitySummary(
                    hcc_code="HCC85",
                    description="Heart Failure",
                    gap_type="needs_specificity",
                    confidence="medium",
                    estimated_revenue=4651.20,
                    recommended_icd10="I50.22",
                ),
            ],
            revenue_summary={
                "total_potential_revenue": 9000.00,
                "high_confidence_opportunities": 1,
                "medium_confidence_opportunities": 1,
            },
            action_items=[
                ActionItem(
                    priority="high",
                    title="Code HCC37",
                    description="Diabetes with nephropathy documented but not coded",
                    category="hcc",
                    estimated_impact="$4,348.80/year",
                ),
            ],
        )

        assert len(response.hcc_opportunities) == 2
        total_revenue = sum(o.estimated_revenue for o in response.hcc_opportunities)
        assert total_revenue == 9000.00
        assert response.revenue_summary["total_potential_revenue"] == 9000.00

    def test_admin_aggregates_all(self):
        """Test admin dashboard aggregates all role data."""
        response = AdminDashboardResponse(
            metadata=DashboardMetadata(generated_at=datetime.now()),
            system_stats=SystemStatsSummary(),
            service_health=[
                ServiceHealthSummary(service_name="hcc_analyzer", status="healthy"),
                ServiceHealthSummary(service_name="icd10_suggester", status="healthy"),
                ServiceHealthSummary(service_name="quality_metrics", status="healthy"),
            ],
            provider_summary={"calculators": 10, "drug_interactions": 500},
            biller_summary={"hcc_definitions": 10, "icd10_codes": 100000},
            quality_summary={"documents_processed": 100, "error_rate": 0.02},
            all_action_items=[
                ActionItem(
                    priority="high",
                    title="Provider Alert",
                    description="High-risk patient",
                    category="clinical",
                ),
                ActionItem(
                    priority="medium",
                    title="Billing Opportunity",
                    description="HCC gap detected",
                    category="hcc",
                ),
            ],
        )

        # Admin should have health for all services
        assert len(response.service_health) == 3
        assert all(s.status == "healthy" for s in response.service_health)

        # Should aggregate actions from all roles
        assert len(response.all_action_items) == 2

        # Should have summaries from all dashboards
        assert "calculators" in response.provider_summary
        assert "hcc_definitions" in response.biller_summary
        assert "documents_processed" in response.quality_summary
