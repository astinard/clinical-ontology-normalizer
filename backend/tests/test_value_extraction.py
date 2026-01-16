"""Tests for the value extraction service."""

import pytest

from app.models.clinical_value import ValueType
from app.services.value_extraction import ExtractedValue, ValueExtractionService


@pytest.fixture
def service() -> ValueExtractionService:
    """Create a value extraction service instance."""
    return ValueExtractionService()


class TestVitalSignExtraction:
    """Tests for vital sign extraction."""

    def test_blood_pressure_standard_format(self, service: ValueExtractionService):
        """Test extraction of standard BP format."""
        text = "BP 145/92 mmHg"
        # Use extract_all which handles deduplication
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        bp = values[0]
        assert bp.name == "Blood Pressure"
        assert bp.value == 145.0
        assert bp.value_secondary == 92.0
        assert bp.unit == "mmHg"
        assert bp.value_type == ValueType.VITAL_SIGN

    def test_blood_pressure_colon_format(self, service: ValueExtractionService):
        """Test extraction of BP with colon."""
        text = "Blood pressure: 120/80"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        bp = values[0]
        assert bp.name == "Blood Pressure"
        assert bp.value == 120.0
        assert bp.value_secondary == 80.0

    def test_heart_rate_bpm(self, service: ValueExtractionService):
        """Test extraction of heart rate with bpm."""
        text = "HR 88 bpm"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        hr = values[0]
        assert hr.name == "Heart Rate"
        assert hr.value == 88.0
        assert hr.unit == "bpm"
        assert hr.value_type == ValueType.VITAL_SIGN

    def test_respiratory_rate(self, service: ValueExtractionService):
        """Test extraction of respiratory rate."""
        text = "RR 18/min"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        rr = values[0]
        assert rr.name == "Respiratory Rate"
        assert rr.value == 18.0

    def test_temperature_fahrenheit(self, service: ValueExtractionService):
        """Test extraction of temperature in Fahrenheit."""
        text = "Temp 101.2 F"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        temp = values[0]
        assert temp.name == "Temperature"
        assert temp.value == 101.2
        assert "F" in (temp.unit or temp.unit_normalized or "")

    def test_temperature_celsius(self, service: ValueExtractionService):
        """Test extraction of temperature in Celsius."""
        text = "Temperature: 38.5C"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        temp = values[0]
        assert temp.name == "Temperature"
        assert temp.value == 38.5

    def test_oxygen_saturation(self, service: ValueExtractionService):
        """Test extraction of oxygen saturation."""
        text = "O2 sat 95% on room air"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        o2 = values[0]
        assert o2.name == "Oxygen Saturation"
        assert o2.value == 95.0
        assert o2.unit == "%"

    def test_spo2_format(self, service: ValueExtractionService):
        """Test extraction of SpO2 format."""
        text = "SpO2: 98%"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        assert values[0].name == "Oxygen Saturation"
        assert values[0].value == 98.0

    def test_weight_kg(self, service: ValueExtractionService):
        """Test extraction of weight in kg."""
        text = "Weight: 85 kg"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        wt = values[0]
        assert wt.name == "Weight"
        assert wt.value == 85.0
        assert wt.unit == "kg"

    def test_weight_lbs(self, service: ValueExtractionService):
        """Test extraction of weight in lbs."""
        text = "Wt 187 lbs"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        wt = values[0]
        assert wt.name == "Weight"
        assert wt.value == 187.0
        assert wt.unit == "lbs"

    def test_height_cm(self, service: ValueExtractionService):
        """Test extraction of height in cm."""
        text = "Height 175 cm"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        ht = values[0]
        assert ht.name == "Height"
        assert ht.value == 175.0
        assert ht.unit == "cm"

    def test_bmi(self, service: ValueExtractionService):
        """Test extraction of BMI."""
        text = "BMI: 32.5"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        bmi = values[0]
        assert bmi.name == "BMI"
        assert bmi.value == 32.5

    def test_multiple_vitals(self, service: ValueExtractionService):
        """Test extraction of multiple vitals in text."""
        text = "VS: BP 130/85, HR 72 bpm, RR 16, Temp 98.6F, SpO2 97%"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        assert len(values) >= 5
        names = [v.name for v in values]
        assert "Blood Pressure" in names
        assert "Heart Rate" in names
        assert "Respiratory Rate" in names
        assert "Temperature" in names
        assert "Oxygen Saturation" in names


class TestLabResultExtraction:
    """Tests for lab result extraction."""

    def test_sodium(self, service: ValueExtractionService):
        """Test extraction of sodium."""
        text = "Na 138 mEq/L"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        na = values[0]
        assert na.name in ["Sodium", "Na"]  # May be abbreviated or full name
        assert na.value == 138.0
        assert na.unit == "mEq/L"
        assert na.value_type == ValueType.LAB_RESULT

    def test_potassium(self, service: ValueExtractionService):
        """Test extraction of potassium."""
        text = "K 4.2 mEq/L"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        k = values[0]
        assert k.name in ["Potassium", "K"]  # May be abbreviated or full name
        assert k.value == 4.2

    def test_creatinine(self, service: ValueExtractionService):
        """Test extraction of creatinine."""
        text = "Creatinine 1.8 mg/dL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        cr = values[0]
        assert cr.name == "Creatinine"
        assert cr.value == 1.8
        assert cr.unit == "mg/dL"

    def test_bun(self, service: ValueExtractionService):
        """Test extraction of BUN."""
        text = "BUN: 28 mg/dL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        bun = values[0]
        assert bun.name == "BUN"
        assert bun.value == 28.0

    def test_glucose(self, service: ValueExtractionService):
        """Test extraction of glucose."""
        text = "Glucose 126 mg/dL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) >= 1
        gluc = next(v for v in values if "Glucose" in v.name or v.name == "Glucose")
        assert gluc.value == 126.0

    def test_hba1c(self, service: ValueExtractionService):
        """Test extraction of HbA1c."""
        text = "HbA1c 7.2%"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        a1c = values[0]
        assert a1c.name == "HbA1c"
        assert a1c.value == 7.2
        assert a1c.unit == "%"

    def test_hemoglobin(self, service: ValueExtractionService):
        """Test extraction of hemoglobin."""
        text = "Hgb 12.5 g/dL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        hgb = values[0]
        assert hgb.name in ["Hemoglobin", "Hgb"]  # May be abbreviated or full name
        assert hgb.value == 12.5

    def test_wbc(self, service: ValueExtractionService):
        """Test extraction of WBC."""
        text = "WBC 8.5 K/uL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        wbc = values[0]
        assert wbc.name == "WBC"
        assert wbc.value == 8.5

    def test_platelets(self, service: ValueExtractionService):
        """Test extraction of platelets."""
        text = "Plt 245 K/uL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        plt = values[0]
        assert plt.name in ["Platelets", "Plt"]  # May be abbreviated or full name
        assert plt.value == 245.0

    def test_inr(self, service: ValueExtractionService):
        """Test extraction of INR."""
        text = "INR 2.3"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        inr = values[0]
        assert inr.name == "INR"
        assert inr.value == 2.3

    def test_troponin(self, service: ValueExtractionService):
        """Test extraction of troponin."""
        text = "Troponin 0.08 ng/mL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        trop = values[0]
        assert trop.name == "Troponin"
        assert trop.value == 0.08

    def test_bnp(self, service: ValueExtractionService):
        """Test extraction of BNP."""
        text = "BNP 850 pg/mL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        bnp = values[0]
        assert bnp.name == "BNP"
        assert bnp.value == 850.0

    def test_tsh(self, service: ValueExtractionService):
        """Test extraction of TSH."""
        text = "TSH 2.1 mIU/L"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        tsh = values[0]
        assert tsh.name == "TSH"
        assert tsh.value == 2.1

    def test_ldl(self, service: ValueExtractionService):
        """Test extraction of LDL."""
        text = "LDL 145 mg/dL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        assert len(values) == 1
        ldl = values[0]
        assert ldl.name == "LDL"
        assert ldl.value == 145.0


class TestMeasurementExtraction:
    """Tests for clinical measurement extraction."""

    def test_ejection_fraction(self, service: ValueExtractionService):
        """Test extraction of ejection fraction."""
        text = "LVEF 35%"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_medications=False)

        assert len(values) == 1
        ef = values[0]
        assert ef.name == "Ejection Fraction"
        assert ef.value == 35.0
        assert ef.unit == "%"
        assert ef.value_type == ValueType.MEASUREMENT

    def test_ef_short_form(self, service: ValueExtractionService):
        """Test extraction of EF short form."""
        text = "EF 45%"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_medications=False)

        assert len(values) == 1
        ef = values[0]
        assert ef.name == "Ejection Fraction"
        assert ef.value == 45.0


class TestMedicationDoseExtraction:
    """Tests for medication dose extraction."""

    def test_metformin_dose(self, service: ValueExtractionService):
        """Test extraction of metformin dose."""
        text = "Metformin 1000mg PO BID"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_measurements=False)

        assert len(values) >= 1
        med = values[0]
        assert med.name == "Metformin"
        assert med.value == 1000.0
        assert med.unit == "mg"
        assert med.value_type == ValueType.MEDICATION_DOSE

    def test_lisinopril_dose(self, service: ValueExtractionService):
        """Test extraction of lisinopril dose."""
        text = "Lisinopril 20 mg daily"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_measurements=False)

        assert len(values) >= 1
        med = values[0]
        assert med.name == "Lisinopril"
        assert med.value == 20.0
        assert med.unit == "mg"

    def test_insulin_units(self, service: ValueExtractionService):
        """Test extraction of insulin dose in units."""
        text = "Lantus 40 units at bedtime"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_measurements=False)

        assert len(values) >= 1
        med = values[0]
        assert med.name == "Lantus"
        assert med.value == 40.0
        assert "unit" in med.unit.lower()

    def test_aspirin_dose(self, service: ValueExtractionService):
        """Test extraction of aspirin dose."""
        text = "Aspirin 81mg daily"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_measurements=False)

        assert len(values) >= 1
        med = values[0]
        assert med.value == 81.0
        assert med.unit == "mg"

    def test_multiple_meds(self, service: ValueExtractionService):
        """Test extraction of multiple medications."""
        text = "Metoprolol 25mg BID, Furosemide 40mg daily, Lisinopril 10mg daily"
        values = service.extract_all(text, include_vitals=False, include_labs=False, include_measurements=False)

        assert len(values) >= 3
        names = [v.name for v in values]
        assert "Metoprolol" in names
        assert "Furosemide" in names
        assert "Lisinopril" in names


class TestExtractAll:
    """Tests for combined extraction."""

    def test_clinical_note_extraction(self, service: ValueExtractionService):
        """Test extraction from a realistic clinical note snippet."""
        text = """
        VITAL SIGNS: BP 145/92 mmHg, HR 88 bpm, RR 18, Temp 98.6F, O2 sat 95% on RA.
        Weight: 187 lbs, Height: 5'10", BMI: 26.8

        LABS:
        Na 138, K 4.2, Cr 1.4 mg/dL, BUN 22
        Glucose 186 mg/dL
        HbA1c 8.2%
        Hgb 11.8 g/dL, WBC 7.2 K/uL, Plt 198

        CARDIAC:
        BNP 650 pg/mL, Troponin 0.02
        Echo shows LVEF 40%

        MEDICATIONS:
        Metformin 1000mg PO BID
        Lisinopril 20mg daily
        Metoprolol 50mg BID
        Aspirin 81mg daily
        """
        values = service.extract_all(text)

        # Should find vitals
        vital_names = [v.name for v in values if v.value_type == ValueType.VITAL_SIGN]
        assert "Blood Pressure" in vital_names
        assert "Heart Rate" in vital_names
        assert "Temperature" in vital_names
        assert "Oxygen Saturation" in vital_names
        assert "Weight" in vital_names
        assert "BMI" in vital_names

        # Should find labs (names may be abbreviated or full)
        lab_names = [v.name for v in values if v.value_type == ValueType.LAB_RESULT]
        assert any(n in lab_names for n in ["Sodium", "Na"])
        assert any(n in lab_names for n in ["Potassium", "K"])
        assert any(n in lab_names for n in ["Creatinine", "Cr"])
        assert "Glucose" in lab_names
        assert "HbA1c" in lab_names
        assert any(n in lab_names for n in ["Hemoglobin", "Hgb"])
        assert "BNP" in lab_names

        # Should find measurements
        meas_names = [v.name for v in values if v.value_type == ValueType.MEASUREMENT]
        assert "Ejection Fraction" in meas_names

        # Should find medications
        med_names = [v.name for v in values if v.value_type == ValueType.MEDICATION_DOSE]
        assert "Metformin" in med_names
        assert "Lisinopril" in med_names
        assert "Metoprolol" in med_names
        assert "Aspirin" in med_names

    def test_offset_calculation(self, service: ValueExtractionService):
        """Test that offsets are correctly calculated."""
        text = "BP 120/80. HR 72."
        values = service.extract_all(text)

        # Find BP
        bp = next(v for v in values if v.name == "Blood Pressure")
        assert text[bp.start_offset:bp.end_offset] == bp.text

        # Find HR
        hr = next(v for v in values if v.name == "Heart Rate")
        assert text[hr.start_offset:hr.end_offset] == hr.text

    def test_offset_with_base_offset(self, service: ValueExtractionService):
        """Test extraction with base offset for section extraction."""
        text = "BP 130/85"
        values = service.extract_all(text, offset=100)

        assert len(values) >= 1
        bp = values[0]
        assert bp.start_offset == 100

    def test_deduplication(self, service: ValueExtractionService):
        """Test that overlapping extractions are deduplicated."""
        text = "BP 145/92 mmHg"
        values = service.extract_all(text)

        # Should have exactly one BP value (not multiple overlapping patterns)
        bp_values = [v for v in values if v.name == "Blood Pressure"]
        assert len(bp_values) == 1


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text(self, service: ValueExtractionService):
        """Test extraction from empty text."""
        values = service.extract_all("")
        assert len(values) == 0

    def test_no_values_text(self, service: ValueExtractionService):
        """Test extraction from text with no extractable values."""
        text = "Patient reports feeling well. No complaints."
        values = service.extract_all(text)
        assert len(values) == 0

    def test_unusual_formatting(self, service: ValueExtractionService):
        """Test extraction with unusual formatting."""
        text = "BP:145/92  HR:88  Temp:98.6"
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        # Should still extract values despite no spaces after colons
        assert len(values) >= 2

    def test_values_in_sentences(self, service: ValueExtractionService):
        """Test extraction of values embedded in sentences."""
        # Use patterns that the service recognizes
        text = "The patient's BP: 150/95, HR: 92 bpm."
        values = service.extract_all(text, include_labs=False, include_measurements=False, include_medications=False)

        bp = next((v for v in values if v.name == "Blood Pressure"), None)
        hr = next((v for v in values if v.name == "Heart Rate"), None)

        assert bp is not None
        assert bp.value == 150.0
        assert hr is not None
        assert hr.value == 92.0

    def test_decimal_values(self, service: ValueExtractionService):
        """Test extraction of decimal values."""
        text = "Creatinine 1.25 mg/dL, Troponin 0.04 ng/mL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        cr = next(v for v in values if v.name == "Creatinine")
        assert cr.value == 1.25

        trop = next(v for v in values if v.name == "Troponin")
        assert trop.value == 0.04

    def test_high_values(self, service: ValueExtractionService):
        """Test extraction of high numeric values."""
        text = "Glucose 456 mg/dL, BNP 2500 pg/mL"
        values = service.extract_all(text, include_vitals=False, include_measurements=False, include_medications=False)

        gluc = next(v for v in values if "Glucose" in v.name or v.name == "Glucose")
        assert gluc.value == 456.0

        bnp = next(v for v in values if v.name == "BNP")
        assert bnp.value == 2500.0
