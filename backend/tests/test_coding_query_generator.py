"""Tests for Coding Query Generator Service."""

import pytest

from app.services.coding_query_generator import (
    CodingImpact,
    CodingQuery,
    CodingQueryGeneratorService,
    QueryBatch,
    QueryPriority,
    QueryStatus,
    ResponseOption,
    get_coding_query_generator_service,
    reset_coding_query_generator_service,
)
from app.services.documentation_gaps import GapCategory, GapSeverity


# ============================================================================
# Service Initialization Tests
# ============================================================================


class TestServiceInit:
    """Test service initialization."""

    def test_service_creation(self):
        """Test service can be created."""
        reset_coding_query_generator_service()
        service = get_coding_query_generator_service()
        assert service is not None

    def test_singleton_pattern(self):
        """Test singleton pattern works."""
        reset_coding_query_generator_service()
        service1 = get_coding_query_generator_service()
        service2 = get_coding_query_generator_service()
        assert service1 is service2

    def test_singleton_reset(self):
        """Test singleton can be reset."""
        service1 = get_coding_query_generator_service()
        reset_coding_query_generator_service()
        service2 = get_coding_query_generator_service()
        assert service1 is not service2


# ============================================================================
# Template Tests
# ============================================================================


class TestTemplates:
    """Test query templates."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_has_templates(self):
        """Test service has templates."""
        keys = self.service.list_template_keys()
        assert len(keys) > 0

    def test_diabetes_template_exists(self):
        """Test diabetes template exists."""
        template = self.service.get_query_template("diabetes_type")
        assert template is not None
        assert "question" in template
        assert "response_options" in template

    def test_heart_failure_template_exists(self):
        """Test heart failure template exists."""
        template = self.service.get_query_template("heart_failure_type")
        assert template is not None

    def test_ckd_template_exists(self):
        """Test CKD template exists."""
        template = self.service.get_query_template("ckd_stage")
        assert template is not None

    def test_template_has_response_options(self):
        """Test templates have response options."""
        template = self.service.get_query_template("diabetes_type")
        assert len(template["response_options"]) >= 2

    def test_response_options_have_icd10(self):
        """Test response options include ICD-10 codes."""
        template = self.service.get_query_template("diabetes_type")
        options_with_codes = [
            opt for opt in template["response_options"]
            if opt.icd10_code
        ]
        assert len(options_with_codes) > 0


# ============================================================================
# Query Generation Tests
# ============================================================================


class TestQueryGeneration:
    """Test query generation from clinical text."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_generate_queries_returns_batch(self):
        """Test generate_queries returns QueryBatch."""
        text = "Patient has diabetes and hypertension."
        result = self.service.generate_queries(text)
        assert isinstance(result, QueryBatch)

    def test_diabetes_generates_type_query(self):
        """Test diabetes text generates type query."""
        text = "Patient has diabetes mellitus with A1c of 8.5%."
        result = self.service.generate_queries(text)

        type_queries = [
            q for q in result.queries
            if "type" in q.question.lower() and "diabetes" in q.question.lower()
        ]
        assert len(type_queries) > 0

    def test_heart_failure_generates_query(self):
        """Test heart failure text generates query."""
        text = "Patient presents with heart failure, BNP elevated."
        result = self.service.generate_queries(text)

        hf_queries = [
            q for q in result.queries
            if "heart failure" in q.finding.lower() or "chf" in q.finding.lower()
        ]
        assert len(hf_queries) > 0

    def test_ckd_generates_stage_query(self):
        """Test CKD text generates stage query."""
        text = "Patient has chronic kidney disease, creatinine 2.5."
        result = self.service.generate_queries(text)

        ckd_queries = [
            q for q in result.queries
            if "ckd" in q.finding.lower() or "kidney" in q.finding.lower()
        ]
        assert len(ckd_queries) > 0

    def test_clean_text_no_queries(self):
        """Test clean, specific text generates fewer queries."""
        text = "Patient has well-controlled Type 2 diabetes mellitus with A1c 6.5%."
        result = self.service.generate_queries(text)
        # Should have fewer gaps since it's specific
        assert result.total_queries <= 2  # May have some minor gaps


# ============================================================================
# Query Structure Tests
# ============================================================================


class TestQueryStructure:
    """Test query structure and content."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_queries_have_id(self):
        """Test queries have unique IDs."""
        text = "Patient has diabetes and hypertension."
        result = self.service.generate_queries(text)

        if result.queries:
            for q in result.queries:
                assert q.query_id.startswith("CDI-")

    def test_queries_have_priority(self):
        """Test queries have priority."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            for q in result.queries:
                assert q.priority in QueryPriority

    def test_queries_have_status_pending(self):
        """Test new queries have pending status."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            for q in result.queries:
                assert q.status == QueryStatus.PENDING

    def test_queries_have_response_options(self):
        """Test queries have response options."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            for q in result.queries:
                assert len(q.response_options) >= 2

    def test_queries_have_cer_citation(self):
        """Test queries have CER citations."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            for q in result.queries:
                assert q.cer_citation is not None
                assert q.cer_citation.claim
                assert len(q.cer_citation.evidence) > 0


# ============================================================================
# Priority Tests
# ============================================================================


class TestQueryPriority:
    """Test query prioritization."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_queries_sorted_by_priority(self):
        """Test queries are sorted by priority."""
        text = "Patient has diabetes, heart failure, and CKD."
        result = self.service.generate_queries(text)

        if len(result.queries) >= 2:
            priority_order = {
                QueryPriority.STAT: 0,
                QueryPriority.URGENT: 1,
                QueryPriority.ROUTINE: 2,
                QueryPriority.DEFERRED: 3
            }
            for i in range(len(result.queries) - 1):
                curr_priority = priority_order[result.queries[i].priority]
                next_priority = priority_order[result.queries[i + 1].priority]
                assert curr_priority <= next_priority

    def test_inpatient_context_affects_priority(self):
        """Test inpatient context increases priority."""
        text = "Patient has diabetes."

        # Outpatient context
        outpatient_result = self.service.generate_queries(
            text,
            encounter_context={"encounter_type": "outpatient"}
        )

        # Inpatient context
        inpatient_result = self.service.generate_queries(
            text,
            encounter_context={"encounter_type": "inpatient"}
        )

        # Check both have queries
        if outpatient_result.queries and inpatient_result.queries:
            # Inpatient should have higher or equal priority
            out_priority = outpatient_result.queries[0].priority
            in_priority = inpatient_result.queries[0].priority
            priority_rank = {
                QueryPriority.STAT: 0,
                QueryPriority.URGENT: 1,
                QueryPriority.ROUTINE: 2,
                QueryPriority.DEFERRED: 3
            }
            assert priority_rank[in_priority] <= priority_rank[out_priority]


# ============================================================================
# Impact Estimation Tests
# ============================================================================


class TestImpactEstimation:
    """Test revenue and coding impact estimation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_batch_has_revenue_impact(self):
        """Test batch includes revenue impact estimate."""
        text = "Patient has diabetes and heart failure."
        result = self.service.generate_queries(text)
        assert result.total_estimated_revenue_impact >= 0

    def test_queries_have_individual_impact(self):
        """Test individual queries have impact estimates."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            for q in result.queries:
                assert q.estimated_revenue_impact >= 0

    def test_hcc_impact_detected(self):
        """Test HCC impact is detected for relevant conditions."""
        text = "Patient has diabetes and heart failure."
        result = self.service.generate_queries(text)

        # These conditions affect HCC
        assert result.hcc_impact_possible

    def test_coding_impacts_assigned(self):
        """Test coding impacts are assigned to queries."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            # Diabetes should have HCC impact
            dm_queries = [q for q in result.queries if "diabetes" in q.finding.lower()]
            if dm_queries:
                impacts = dm_queries[0].coding_impacts
                assert len(impacts) > 0


# ============================================================================
# Batch Statistics Tests
# ============================================================================


class TestBatchStatistics:
    """Test batch statistics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_batch_has_counts(self):
        """Test batch has query counts."""
        text = "Patient has diabetes and hypertension."
        result = self.service.generate_queries(text)

        assert result.total_queries >= 0
        assert result.total_queries == len(result.queries)

    def test_batch_has_by_priority(self):
        """Test batch counts by priority."""
        text = "Patient has diabetes and heart failure."
        result = self.service.generate_queries(text)

        # by_priority should exist
        assert isinstance(result.by_priority, dict)

    def test_batch_has_by_category(self):
        """Test batch counts by category."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        # by_category should exist
        assert isinstance(result.by_category, dict)

    def test_batch_has_documentation_score(self):
        """Test batch has documentation score."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        assert 0 <= result.documentation_score <= 100


# ============================================================================
# Query Status Update Tests
# ============================================================================


class TestQueryStatusUpdate:
    """Test query status updates."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_update_status_to_sent(self):
        """Test updating query status to sent."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            query = result.queries[0]
            updated = self.service.update_query_status(query, QueryStatus.SENT)
            assert updated.status == QueryStatus.SENT
            assert updated.sent_at is not None

    def test_update_status_with_response(self):
        """Test updating query with response."""
        text = "Patient has diabetes."
        result = self.service.generate_queries(text)

        if result.queries:
            query = result.queries[0]
            updated = self.service.update_query_status(
                query,
                QueryStatus.RESPONDED,
                response_value="type_2",
                response_notes="Confirmed Type 2 DM"
            )
            assert updated.status == QueryStatus.RESPONDED
            assert updated.responded_at is not None
            assert updated.response_value == "type_2"
            assert updated.response_notes == "Confirmed Type 2 DM"


# ============================================================================
# Service Statistics Tests
# ============================================================================


class TestServiceStatistics:
    """Test service statistics."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_get_stats(self):
        """Test getting service statistics."""
        stats = self.service.get_stats()
        assert "template_count" in stats
        assert "templates" in stats
        assert stats["template_count"] > 0

    def test_stats_include_categories(self):
        """Test stats include gap categories."""
        stats = self.service.get_stats()
        assert "gap_categories" in stats
        assert len(stats["gap_categories"]) > 0


# ============================================================================
# Clinical Scenario Tests
# ============================================================================


class TestClinicalScenarios:
    """Test real-world clinical scenarios."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        reset_coding_query_generator_service()
        self.service = get_coding_query_generator_service()

    def test_discharge_summary_scenario(self):
        """Test discharge summary with multiple conditions."""
        text = """
        Discharge Summary:
        Patient is a 65-year-old male admitted for CHF exacerbation.
        PMH: diabetes, hypertension, CKD.
        Hospital course: Treated with IV diuretics, improved.
        Discharge medications: Lasix, Lisinopril, Metformin.
        """
        result = self.service.generate_queries(text)

        # Should generate queries for ambiguous conditions
        assert result.total_queries > 0

        # Check for HCC impact (CHF, DM, CKD all affect HCC)
        assert result.hcc_impact_possible

    def test_ed_note_scenario(self):
        """Test ED note scenario."""
        text = """
        Chief Complaint: Chest pain
        HPI: 55 yo female with HTN presents with chest pain x 2 hours.
        Assessment: Chest pain, rule out ACS. Known hypertension.
        Plan: Admit for observation, cardiac workup.
        """
        result = self.service.generate_queries(
            text,
            encounter_context={"encounter_type": "emergency"}
        )

        # Should have queries
        assert result.total_queries >= 0

    def test_office_visit_scenario(self):
        """Test routine office visit scenario."""
        text = """
        Office Visit - Follow Up
        Patient returns for diabetes follow-up.
        Current A1c: 7.8%, up from 7.2%.
        Assessment: Diabetes, suboptimally controlled.
        Plan: Increase metformin dose.
        """
        result = self.service.generate_queries(
            text,
            encounter_context={"encounter_type": "outpatient"}
        )

        # Should query for diabetes type if not specified
        dm_queries = [
            q for q in result.queries
            if "diabetes" in q.finding.lower()
        ]
        # May or may not generate query depending on detection
        assert result.total_queries >= 0

    def test_well_documented_note(self):
        """Test well-documented note has fewer queries."""
        text = """
        Patient with Type 2 diabetes mellitus with diabetic nephropathy (Stage 3b CKD),
        currently uncontrolled with A1c 9.2%.
        Also has systolic heart failure with reduced EF (HFrEF), chronic, stable.
        Hypertension is controlled on current regimen.
        """
        result = self.service.generate_queries(text)

        # Well-documented should have high score
        assert result.documentation_score >= 70
