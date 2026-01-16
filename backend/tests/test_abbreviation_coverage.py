"""Tests for clinical abbreviation coverage in NLP extraction.

These tests validate that the expanded clinical_abbreviations.json
provides adequate coverage for real-world clinical notes.
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.nlp_rule_based import RuleBasedNLPService


# Sample ED note with common clinical abbreviations
SAMPLE_ED_NOTE = """
CHIEF COMPLAINT: Shortness of breath

HISTORY OF PRESENT ILLNESS:
64 y/o male with PMHx of HFrEF (EF 25%), CKD stage 4, HTN, DM2, CAD s/p CABG 2019,
and A-fib on anticoagulation who presents with 3-day history of worsening dyspnea
and bilateral lower extremity edema.

Patient reports orthopnea (sleeps on 3 pillows), PND, and DOE with minimal exertion.
Denies chest pain, palpitations, or syncope. Reports weight gain of 8 lbs over past week.
Compliance with medications has been inconsistent due to cost concerns.

PAST MEDICAL HISTORY:
1. HFrEF (EF 25%) - diagnosed 2018
2. CKD stage 4 (baseline Cr 3.2)
3. HTN
4. DM2 (last A1c 8.2)
5. CAD s/p CABG x3 (2019)
6. Atrial fibrillation (chronic)
7. Hyperlipidemia
8. GERD
9. OSA on CPAP

MEDICATIONS:
- Furosemide 80mg BID
- Carvedilol 25mg BID
- Lisinopril 40mg daily
- Spironolactone 25mg daily
- Apixaban 5mg BID
- Metformin 1000mg BID
- Atorvastatin 80mg daily
- Pantoprazole 40mg daily

ALLERGIES: NKDA

FAMILY HISTORY:
Father died of MI at age 58
Mother with DM2 and HTN

SOCIAL HISTORY:
Former smoker (quit 10 years ago), denies alcohol or illicit drug use

PHYSICAL EXAM:
Vitals: BP 158/92, HR 88 (irregular), RR 22, SpO2 94% on RA, Temp 98.4F
General: Alert, oriented, mild respiratory distress
HEENT: JVD present to angle of jaw
Cardiac: Irregularly irregular rhythm, S3 present, 2/6 systolic murmur
Lungs: Bibasilar crackles, no wheezes
Abdomen: Soft, mild RUQ tenderness, hepatomegaly
Extremities: 2+ bilateral pitting edema to knees

LABS:
BNP: 1850 pg/mL (elevated)
Troponin: 0.04 (normal)
Cr: 3.8 (elevated from baseline)
BUN: 52
Na: 132
K: 5.2
Glucose: 186
WBC: 8.2
Hgb: 10.8
Plt: 198

EKG: AFib with RVR, rate 110, no acute ST changes

CXR: Cardiomegaly, bilateral pleural effusions, pulmonary vascular congestion

ASSESSMENT/PLAN:
1. Acute on chronic systolic heart failure exacerbation
   - IV Lasix 80mg x 2, goal negative 1-2L
   - Daily weights, strict I/O
   - Telemetry monitoring

2. Acute kidney injury (AKI) on CKD
   - Hold ACE inhibitor temporarily
   - Monitor creatinine

3. Atrial fibrillation with RVR
   - Rate control with IV diltiazem
   - Continue anticoagulation

4. DM2 - hold metformin given AKI, sliding scale insulin
"""


class TestClinicalAbbreviationsFile:
    """Tests for the clinical_abbreviations.json file itself."""

    @pytest.fixture
    def abbreviations_path(self) -> Path:
        """Get path to clinical abbreviations file."""
        return Path(__file__).parent.parent / "fixtures" / "clinical_abbreviations.json"

    @pytest.fixture
    def abbreviations_data(self, abbreviations_path: Path) -> dict:
        """Load clinical abbreviations data."""
        with open(abbreviations_path) as f:
            return json.load(f)

    def test_file_exists(self, abbreviations_path: Path) -> None:
        """Test that abbreviations file exists."""
        assert abbreviations_path.exists(), "clinical_abbreviations.json not found"

    def test_file_has_terms(self, abbreviations_data: dict) -> None:
        """Test that file contains terms."""
        assert "terms" in abbreviations_data
        assert len(abbreviations_data["terms"]) > 0

    def test_minimum_term_count(self, abbreviations_data: dict) -> None:
        """Test that we have at least 300 terms (expanded from 64)."""
        term_count = len(abbreviations_data["terms"])
        assert term_count >= 300, f"Expected >= 300 terms, got {term_count}"

    def test_term_structure(self, abbreviations_data: dict) -> None:
        """Test that each term has required fields."""
        required_fields = {"name", "synonyms", "domain", "omop_concept_id"}
        for term in abbreviations_data["terms"]:
            missing = required_fields - set(term.keys())
            assert not missing, f"Term {term.get('name', 'UNKNOWN')} missing: {missing}"

    def test_valid_domains(self, abbreviations_data: dict) -> None:
        """Test that all domains are valid."""
        valid_domains = {"Condition", "Drug", "Procedure", "Measurement", "Observation", "Device"}
        for term in abbreviations_data["terms"]:
            assert term["domain"] in valid_domains, f"Invalid domain: {term['domain']}"


class TestCardiacAbbreviationCoverage:
    """Tests for cardiac abbreviation coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_hfref_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that HFrEF is extracted."""
        text = "Patient has HFrEF with EF 25%."
        mentions = nlp_service.extract_mentions(text, uuid4())

        hfref_found = any("hfref" in m.lexical_variant.lower() or
                         "heart failure" in m.lexical_variant.lower()
                         for m in mentions)
        assert hfref_found, "HFrEF not extracted"

    def test_cad_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that CAD is extracted."""
        text = "History of CAD s/p CABG."
        mentions = nlp_service.extract_mentions(text, uuid4())

        cad_found = any("cad" in m.lexical_variant.lower() or
                       "coronary" in m.lexical_variant.lower()
                       for m in mentions)
        assert cad_found, "CAD not extracted"

    def test_afib_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that A-fib is extracted."""
        text = "Patient with chronic A-fib on anticoagulation."
        mentions = nlp_service.extract_mentions(text, uuid4())

        afib_found = any("fib" in m.lexical_variant.lower() or
                        "fibrillation" in m.lexical_variant.lower()
                        for m in mentions)
        assert afib_found, "A-fib not extracted"

    def test_chf_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that CHF is extracted."""
        text = "Admitted for CHF exacerbation."
        mentions = nlp_service.extract_mentions(text, uuid4())

        chf_found = any("chf" in m.lexical_variant.lower() or
                       "heart failure" in m.lexical_variant.lower()
                       for m in mentions)
        assert chf_found, "CHF not extracted"


class TestRenalAbbreviationCoverage:
    """Tests for renal abbreviation coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_ckd_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that CKD is extracted."""
        text = "Patient with CKD stage 4."
        mentions = nlp_service.extract_mentions(text, uuid4())

        ckd_found = any("ckd" in m.lexical_variant.lower() or
                       "kidney disease" in m.lexical_variant.lower()
                       for m in mentions)
        assert ckd_found, "CKD not extracted"

    def test_aki_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that AKI is extracted."""
        text = "Developed AKI on CKD."
        mentions = nlp_service.extract_mentions(text, uuid4())

        aki_found = any("aki" in m.lexical_variant.lower() or
                       "acute kidney" in m.lexical_variant.lower()
                       for m in mentions)
        assert aki_found, "AKI not extracted"

    def test_esrd_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that ESRD is extracted."""
        text = "Patient with ESRD on hemodialysis."
        mentions = nlp_service.extract_mentions(text, uuid4())

        esrd_found = any("esrd" in m.lexical_variant.lower() or
                        "end stage" in m.lexical_variant.lower() or
                        "hemodialysis" in m.lexical_variant.lower()
                        for m in mentions)
        assert esrd_found, "ESRD not extracted"


class TestEndocrineAbbreviationCoverage:
    """Tests for endocrine abbreviation coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_dm2_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that DM2 is extracted."""
        text = "Patient with DM2 on metformin."
        mentions = nlp_service.extract_mentions(text, uuid4())

        dm2_found = any("dm2" in m.lexical_variant.lower() or
                       "dm 2" in m.lexical_variant.lower() or
                       "diabetes" in m.lexical_variant.lower() or
                       "type 2" in m.lexical_variant.lower()
                       for m in mentions)
        assert dm2_found, "DM2 not extracted"

    def test_htn_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that HTN is extracted."""
        text = "History of HTN controlled on medication."
        mentions = nlp_service.extract_mentions(text, uuid4())

        htn_found = any("htn" in m.lexical_variant.lower() or
                       "hypertension" in m.lexical_variant.lower()
                       for m in mentions)
        assert htn_found, "HTN not extracted"

    def test_a1c_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that A1c is extracted."""
        text = "Last A1c was 8.2%."
        mentions = nlp_service.extract_mentions(text, uuid4())

        a1c_found = any("a1c" in m.lexical_variant.lower() or
                       "hba1c" in m.lexical_variant.lower() or
                       "hemoglobin a1c" in m.lexical_variant.lower()
                       for m in mentions)
        assert a1c_found, "A1c not extracted"


class TestMedicationCoverage:
    """Tests for medication coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_furosemide_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that Furosemide is extracted."""
        text = "Patient on Furosemide 80mg BID."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("furosemide" in m.lexical_variant.lower() or
                   "lasix" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "Furosemide not extracted"

    def test_carvedilol_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that Carvedilol is extracted."""
        text = "Continue Carvedilol 25mg BID."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("carvedilol" in m.lexical_variant.lower() or
                   "coreg" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "Carvedilol not extracted"

    def test_apixaban_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that Apixaban is extracted."""
        text = "On Apixaban 5mg BID for anticoagulation."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("apixaban" in m.lexical_variant.lower() or
                   "eliquis" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "Apixaban not extracted"

    def test_metformin_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that Metformin is extracted."""
        text = "Hold metformin given AKI."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("metformin" in m.lexical_variant.lower() or
                   "glucophage" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "Metformin not extracted"

    def test_atorvastatin_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that Atorvastatin is extracted."""
        text = "Continue atorvastatin 80mg daily."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("atorvastatin" in m.lexical_variant.lower() or
                   "lipitor" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "Atorvastatin not extracted"


class TestLabAbbreviationCoverage:
    """Tests for lab abbreviation coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_bnp_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that BNP is extracted."""
        text = "BNP elevated at 1850."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("bnp" in m.lexical_variant.lower() or
                   "natriuretic" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "BNP not extracted"

    def test_creatinine_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that Creatinine is extracted."""
        text = "Cr elevated at 3.8."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("cr" in m.lexical_variant.lower() or
                   "creatinine" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "Creatinine not extracted"


class TestProcedureAbbreviationCoverage:
    """Tests for procedure abbreviation coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_cabg_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that CABG is extracted."""
        text = "History of CABG x3 in 2019."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("cabg" in m.lexical_variant.lower() or
                   "bypass" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "CABG not extracted"

    def test_ekg_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that EKG is extracted."""
        text = "EKG showed AFib with RVR."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("ekg" in m.lexical_variant.lower() or
                   "ecg" in m.lexical_variant.lower() or
                   "electrocardiogram" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "EKG not extracted"

    def test_cxr_extraction(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that CXR is extracted."""
        text = "CXR shows cardiomegaly and pleural effusions."
        mentions = nlp_service.extract_mentions(text, uuid4())

        found = any("cxr" in m.lexical_variant.lower() or
                   "chest x-ray" in m.lexical_variant.lower() or
                   "chest xray" in m.lexical_variant.lower()
                   for m in mentions)
        assert found, "CXR not extracted"


class TestFullEDNoteCoverage:
    """Integration test for full ED note coverage."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_ed_note_minimum_extractions(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that we extract a minimum number of entities from ED note."""
        mentions = nlp_service.extract_mentions(SAMPLE_ED_NOTE, uuid4())

        # Should extract at least 30 entities from this complex note
        assert len(mentions) >= 30, f"Expected >= 30 extractions, got {len(mentions)}"

    def test_ed_note_condition_coverage(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that key conditions are extracted from ED note."""
        mentions = nlp_service.extract_mentions(SAMPLE_ED_NOTE, uuid4())
        lexical_variants = [m.lexical_variant.lower() for m in mentions]
        all_text = " ".join(lexical_variants)

        # Key conditions that MUST be extracted
        key_conditions = [
            ("hfref", "heart failure"),
            ("ckd", "kidney"),
            ("htn", "hypertension"),
            ("dm", "diabetes"),
            ("cad", "coronary"),
            ("fib", "fibrillation"),
        ]

        found_conditions = []
        missing_conditions = []

        for primary, alternate in key_conditions:
            if primary in all_text or alternate in all_text:
                found_conditions.append(primary)
            else:
                missing_conditions.append(primary)

        # Should find at least 4 of 6 key conditions
        assert len(found_conditions) >= 4, (
            f"Missing key conditions: {missing_conditions}. "
            f"Found: {found_conditions}"
        )

    def test_ed_note_medication_coverage(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that key medications are extracted from ED note."""
        mentions = nlp_service.extract_mentions(SAMPLE_ED_NOTE, uuid4())
        lexical_variants = [m.lexical_variant.lower() for m in mentions]
        all_text = " ".join(lexical_variants)

        # Key medications that should be extracted
        key_meds = [
            "furosemide", "lasix",
            "carvedilol", "coreg",
            "lisinopril",
            "apixaban", "eliquis",
            "metformin",
            "atorvastatin", "lipitor",
        ]

        found_meds = [med for med in key_meds if med in all_text]

        # Should find at least 3 medications
        assert len(found_meds) >= 3, f"Found only {len(found_meds)} meds: {found_meds}"

    def test_ed_note_domain_distribution(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that we extract entities from multiple domains."""
        mentions = nlp_service.extract_mentions(SAMPLE_ED_NOTE, uuid4())

        domains = set(m.domain_hint for m in mentions if m.domain_hint)

        # Should have entities from at least 3 different domains
        assert len(domains) >= 3, f"Only {len(domains)} domains found: {domains}"


class TestNegationInContext:
    """Tests for negation detection in clinical context."""

    @pytest.fixture
    def nlp_service(self) -> RuleBasedNLPService:
        """Create NLP service for tests."""
        return RuleBasedNLPService()

    def test_nkda_detection(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that NKDA is recognized."""
        text = "ALLERGIES: NKDA"
        mentions = nlp_service.extract_mentions(text, uuid4())

        nkda_found = any("nkda" in m.lexical_variant.lower() or
                        "no known" in m.lexical_variant.lower()
                        for m in mentions)
        assert nkda_found, "NKDA not extracted"

    def test_denies_negation(self, nlp_service: RuleBasedNLPService) -> None:
        """Test that 'denies' negation is detected."""
        text = "Denies chest pain, palpitations, or syncope."
        mentions = nlp_service.extract_mentions(text, uuid4())

        # Check that extracted mentions are marked as absent
        for m in mentions:
            if "chest pain" in m.lexical_variant.lower() or \
               "syncope" in m.lexical_variant.lower():
                from app.schemas.base import Assertion
                assert m.assertion == Assertion.ABSENT, \
                    f"{m.lexical_variant} should be marked ABSENT"
