"""Clinical Risk Calculators Service.

Provides validated clinical risk scoring calculators for common
medical conditions and decision support.
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk stratification levels."""

    LOW = "low"
    LOW_MODERATE = "low_moderate"
    MODERATE = "moderate"
    MODERATE_HIGH = "moderate_high"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class CalculatorResult:
    """Result from a clinical calculator."""

    calculator_name: str
    score: float
    score_unit: str
    risk_level: RiskLevel
    interpretation: str
    recommendations: list[str]
    components: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)


# ============================================================================
# BMI Calculator
# ============================================================================

def calculate_bmi(
    weight_kg: float,
    height_cm: float,
) -> CalculatorResult:
    """Calculate Body Mass Index (BMI).

    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.

    Returns:
        CalculatorResult with BMI classification.
    """
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)

    if bmi < 18.5:
        risk = RiskLevel.MODERATE
        interpretation = "Underweight"
        recommendations = [
            "Evaluate for malnutrition or underlying disease",
            "Consider nutritional supplementation",
            "Monitor weight trend",
        ]
    elif bmi < 25:
        risk = RiskLevel.LOW
        interpretation = "Normal weight"
        recommendations = [
            "Maintain current healthy lifestyle",
            "Continue regular physical activity",
        ]
    elif bmi < 30:
        risk = RiskLevel.MODERATE
        interpretation = "Overweight"
        recommendations = [
            "Lifestyle modifications: diet and exercise",
            "Screen for metabolic syndrome",
            "Monitor blood pressure and lipids",
        ]
    elif bmi < 35:
        risk = RiskLevel.HIGH
        interpretation = "Class I Obesity"
        recommendations = [
            "Intensive lifestyle intervention",
            "Screen for obesity-related comorbidities",
            "Consider pharmacotherapy if lifestyle fails",
        ]
    elif bmi < 40:
        risk = RiskLevel.HIGH
        interpretation = "Class II Obesity"
        recommendations = [
            "Intensive lifestyle intervention",
            "Consider pharmacotherapy",
            "Evaluate for bariatric surgery eligibility",
        ]
    else:
        risk = RiskLevel.VERY_HIGH
        interpretation = "Class III Obesity (Morbid)"
        recommendations = [
            "Bariatric surgery evaluation recommended",
            "Intensive medical management",
            "Screen for obesity-related comorbidities",
        ]

    return CalculatorResult(
        calculator_name="Body Mass Index (BMI)",
        score=round(bmi, 1),
        score_unit="kg/m²",
        risk_level=risk,
        interpretation=interpretation,
        recommendations=recommendations,
        components={"weight_kg": weight_kg, "height_cm": height_cm},
        references=["WHO BMI Classification"],
    )


# ============================================================================
# CHADS₂-VASc Score (Atrial Fibrillation Stroke Risk)
# ============================================================================

def calculate_chadsvasc(
    age: int,
    female: bool,
    congestive_heart_failure: bool = False,
    hypertension: bool = False,
    diabetes: bool = False,
    stroke_tia_thromboembolism: bool = False,
    vascular_disease: bool = False,
) -> CalculatorResult:
    """Calculate CHA₂DS₂-VASc score for stroke risk in atrial fibrillation.

    Args:
        age: Patient age in years.
        female: True if female sex.
        congestive_heart_failure: History of CHF.
        hypertension: History of hypertension.
        diabetes: History of diabetes mellitus.
        stroke_tia_thromboembolism: Prior stroke, TIA, or thromboembolism.
        vascular_disease: Prior MI, PAD, or aortic plaque.

    Returns:
        CalculatorResult with stroke risk assessment.
    """
    score = 0
    components = {}

    # C - Congestive heart failure (1 point)
    if congestive_heart_failure:
        score += 1
        components["CHF"] = 1

    # H - Hypertension (1 point)
    if hypertension:
        score += 1
        components["Hypertension"] = 1

    # A₂ - Age ≥75 (2 points) or 65-74 (1 point)
    if age >= 75:
        score += 2
        components["Age ≥75"] = 2
    elif age >= 65:
        score += 1
        components["Age 65-74"] = 1

    # D - Diabetes (1 point)
    if diabetes:
        score += 1
        components["Diabetes"] = 1

    # S₂ - Stroke/TIA/thromboembolism (2 points)
    if stroke_tia_thromboembolism:
        score += 2
        components["Prior Stroke/TIA"] = 2

    # V - Vascular disease (1 point)
    if vascular_disease:
        score += 1
        components["Vascular disease"] = 1

    # Sc - Sex category (1 point for female)
    if female:
        score += 1
        components["Female"] = 1

    # Risk stratification and annual stroke rates
    if score == 0:
        risk = RiskLevel.LOW
        stroke_rate = "0%"
        interpretation = "Low risk - anticoagulation generally not recommended"
        recommendations = [
            "Anticoagulation not recommended",
            "Consider aspirin or no therapy",
            "Reassess risk factors annually",
        ]
    elif score == 1:
        risk = RiskLevel.LOW_MODERATE
        stroke_rate = "1.3%"
        interpretation = "Low-moderate risk - consider anticoagulation"
        recommendations = [
            "Consider oral anticoagulation based on patient preferences",
            "If male with score 1 (no other risk factors), may consider no therapy",
            "Discuss bleeding risk vs stroke prevention",
        ]
    elif score == 2:
        risk = RiskLevel.MODERATE
        stroke_rate = "2.2%"
        interpretation = "Moderate risk - anticoagulation recommended"
        recommendations = [
            "Oral anticoagulation recommended",
            "DOAC preferred over warfarin in most cases",
            "Assess bleeding risk (HAS-BLED score)",
        ]
    else:
        if score <= 4:
            risk = RiskLevel.HIGH
            stroke_rate = f"{1.3 + (score - 1) * 1.5:.1f}%"  # Approximate
        else:
            risk = RiskLevel.VERY_HIGH
            stroke_rate = f"{6 + (score - 5) * 2}%"  # Approximate for high scores
        interpretation = f"High risk - anticoagulation strongly recommended"
        recommendations = [
            "Oral anticoagulation strongly recommended",
            "DOAC preferred unless contraindicated",
            "Consider left atrial appendage closure if anticoagulation contraindicated",
            "Strict risk factor control",
        ]

    return CalculatorResult(
        calculator_name="CHA₂DS₂-VASc Score",
        score=score,
        score_unit="points",
        risk_level=risk,
        interpretation=f"{interpretation}. Annual stroke risk: ~{stroke_rate}",
        recommendations=recommendations,
        components=components,
        references=["2019 AHA/ACC/HRS AF Guidelines"],
    )


# ============================================================================
# HAS-BLED Score (Bleeding Risk)
# ============================================================================

def calculate_hasbled(
    hypertension: bool = False,
    renal_disease: bool = False,
    liver_disease: bool = False,
    stroke_history: bool = False,
    bleeding_history: bool = False,
    labile_inr: bool = False,
    age_over_65: bool = False,
    antiplatelet_nsaid: bool = False,
    alcohol_use: bool = False,
) -> CalculatorResult:
    """Calculate HAS-BLED score for major bleeding risk on anticoagulation.

    Args:
        hypertension: Uncontrolled SBP >160 mmHg.
        renal_disease: Dialysis, transplant, Cr >2.6 mg/dL.
        liver_disease: Cirrhosis or bilirubin >2x normal + ALT/AST >3x normal.
        stroke_history: Prior stroke.
        bleeding_history: Prior major bleeding or predisposition.
        labile_inr: Unstable/high INRs or <60% time in therapeutic range.
        age_over_65: Age over 65 years.
        antiplatelet_nsaid: Concomitant aspirin or NSAIDs.
        alcohol_use: ≥8 drinks/week.

    Returns:
        CalculatorResult with bleeding risk assessment.
    """
    score = 0
    components = {}

    # H - Hypertension
    if hypertension:
        score += 1
        components["Hypertension"] = 1

    # A - Abnormal renal/liver function (1 point each)
    if renal_disease:
        score += 1
        components["Abnormal renal function"] = 1
    if liver_disease:
        score += 1
        components["Abnormal liver function"] = 1

    # S - Stroke
    if stroke_history:
        score += 1
        components["Stroke history"] = 1

    # B - Bleeding
    if bleeding_history:
        score += 1
        components["Bleeding history"] = 1

    # L - Labile INRs
    if labile_inr:
        score += 1
        components["Labile INR"] = 1

    # E - Elderly
    if age_over_65:
        score += 1
        components["Age >65"] = 1

    # D - Drugs/Alcohol (1 point each)
    if antiplatelet_nsaid:
        score += 1
        components["Antiplatelet/NSAID"] = 1
    if alcohol_use:
        score += 1
        components["Alcohol use"] = 1

    # Risk stratification
    if score <= 1:
        risk = RiskLevel.LOW
        interpretation = "Low bleeding risk"
        recommendations = [
            "Anticoagulation generally safe",
            "Standard monitoring",
        ]
    elif score == 2:
        risk = RiskLevel.MODERATE
        interpretation = "Moderate bleeding risk"
        recommendations = [
            "Anticoagulation can be considered",
            "Address modifiable risk factors",
            "Enhanced monitoring recommended",
        ]
    else:
        risk = RiskLevel.HIGH
        interpretation = "High bleeding risk"
        recommendations = [
            "High bleeding risk does not contraindicate anticoagulation",
            "Address all modifiable risk factors",
            "Consider DOAC over warfarin",
            "Close monitoring and follow-up",
            "Consider PPI for GI protection",
        ]

    return CalculatorResult(
        calculator_name="HAS-BLED Score",
        score=score,
        score_unit="points",
        risk_level=risk,
        interpretation=f"{interpretation}. Score ≥3 indicates high risk requiring caution.",
        recommendations=recommendations,
        components=components,
        references=["Pisters R, et al. Chest 2010"],
    )


# ============================================================================
# MELD Score (Liver Disease Severity)
# ============================================================================

def calculate_meld(
    creatinine: float,
    bilirubin: float,
    inr: float,
    sodium: float | None = None,
    on_dialysis: bool = False,
) -> CalculatorResult:
    """Calculate MELD score for liver disease severity.

    Args:
        creatinine: Serum creatinine in mg/dL.
        bilirubin: Total bilirubin in mg/dL.
        inr: International Normalized Ratio.
        sodium: Serum sodium in mEq/L (for MELD-Na).
        on_dialysis: True if on dialysis (creatinine set to 4).

    Returns:
        CalculatorResult with liver disease severity.
    """
    # Apply bounds and dialysis adjustment
    cr = 4.0 if on_dialysis else max(1.0, min(creatinine, 4.0))
    bili = max(1.0, bilirubin)
    inr_val = max(1.0, inr)

    # MELD = 10 * (0.957 * ln(Cr) + 0.378 * ln(Bili) + 1.120 * ln(INR) + 0.643)
    meld = 10 * (
        0.957 * math.log(cr) +
        0.378 * math.log(bili) +
        1.120 * math.log(inr_val) +
        0.643
    )

    # MELD-Na calculation if sodium provided
    meld_na = None
    if sodium is not None:
        na = max(125, min(sodium, 137))
        meld_na = meld + 1.32 * (137 - na) - (0.033 * meld * (137 - na))
        meld_na = max(6, min(meld_na, 40))

    score = round(meld_na if meld_na else meld)
    score = max(6, min(score, 40))  # MELD bounded 6-40

    # Risk stratification
    if score < 10:
        risk = RiskLevel.LOW
        interpretation = "Low risk - 3-month mortality ~2%"
        recommendations = [
            "Continue medical management",
            "Monitor for disease progression",
        ]
    elif score < 20:
        risk = RiskLevel.MODERATE
        interpretation = "Moderate risk - 3-month mortality ~6-20%"
        recommendations = [
            "Consider liver transplant evaluation",
            "Optimize medical management",
            "Monitor closely for complications",
        ]
    elif score < 30:
        risk = RiskLevel.HIGH
        interpretation = "High risk - 3-month mortality ~50%"
        recommendations = [
            "Urgent liver transplant evaluation",
            "ICU monitoring may be needed",
            "Aggressive management of complications",
        ]
    else:
        risk = RiskLevel.VERY_HIGH
        interpretation = "Very high risk - 3-month mortality ~70-80%"
        recommendations = [
            "Emergent liver transplant consideration",
            "ICU care likely required",
            "Discuss goals of care",
        ]

    components = {
        "creatinine": creatinine,
        "bilirubin": bilirubin,
        "inr": inr,
        "on_dialysis": on_dialysis,
    }
    if sodium is not None:
        components["sodium"] = sodium
        components["meld_basic"] = round(meld)

    return CalculatorResult(
        calculator_name="MELD-Na Score" if sodium else "MELD Score",
        score=score,
        score_unit="points",
        risk_level=risk,
        interpretation=interpretation,
        recommendations=recommendations,
        components=components,
        references=["UNOS MELD allocation policy"],
    )


# ============================================================================
# CKD-EPI eGFR Calculator
# ============================================================================

def calculate_egfr_ckdepi(
    creatinine: float,
    age: int,
    female: bool,
    black: bool = False,
) -> CalculatorResult:
    """Calculate eGFR using CKD-EPI equation (2021 race-free version).

    Args:
        creatinine: Serum creatinine in mg/dL.
        age: Patient age in years.
        female: True if female.
        black: Deprecated - included for API compatibility but not used.

    Returns:
        CalculatorResult with CKD staging.
    """
    # 2021 CKD-EPI equation (race-free)
    # eGFR = 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^-1.200 × 0.9938^Age × (1.012 if female)

    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302

    scr_ratio = creatinine / kappa
    min_term = min(scr_ratio, 1) ** alpha
    max_term = max(scr_ratio, 1) ** -1.200
    age_term = 0.9938 ** age
    sex_term = 1.012 if female else 1

    egfr = 142 * min_term * max_term * age_term * sex_term
    egfr = round(egfr, 1)

    # CKD staging
    if egfr >= 90:
        stage = "G1"
        risk = RiskLevel.LOW
        interpretation = "Normal or high kidney function"
        recommendations = [
            "Annual monitoring if risk factors present",
            "Control blood pressure and diabetes",
        ]
    elif egfr >= 60:
        stage = "G2"
        risk = RiskLevel.LOW_MODERATE
        interpretation = "Mildly decreased kidney function"
        recommendations = [
            "Monitor eGFR annually",
            "Optimize blood pressure control",
            "Avoid nephrotoxic medications",
        ]
    elif egfr >= 45:
        stage = "G3a"
        risk = RiskLevel.MODERATE
        interpretation = "Mild-moderately decreased function"
        recommendations = [
            "Monitor eGFR every 6 months",
            "Referral to nephrology if rapid decline",
            "Adjust medications for renal function",
            "Screen for complications (anemia, bone disease)",
        ]
    elif egfr >= 30:
        stage = "G3b"
        risk = RiskLevel.MODERATE_HIGH
        interpretation = "Moderate-severely decreased function"
        recommendations = [
            "Nephrology referral recommended",
            "Monitor every 3-6 months",
            "Prepare for kidney replacement therapy",
            "Avoid contrast and nephrotoxins",
        ]
    elif egfr >= 15:
        stage = "G4"
        risk = RiskLevel.HIGH
        interpretation = "Severely decreased kidney function"
        recommendations = [
            "Nephrology co-management essential",
            "Plan for dialysis or transplant",
            "Avoid nephrotoxins strictly",
            "Monthly monitoring",
        ]
    else:
        stage = "G5"
        risk = RiskLevel.VERY_HIGH
        interpretation = "Kidney failure"
        recommendations = [
            "Initiate dialysis or transplant",
            "Intensive nephrology management",
            "Discuss goals of care",
        ]

    return CalculatorResult(
        calculator_name="CKD-EPI eGFR (2021)",
        score=egfr,
        score_unit="mL/min/1.73m²",
        risk_level=risk,
        interpretation=f"CKD Stage {stage}: {interpretation}",
        recommendations=recommendations,
        components={
            "creatinine": creatinine,
            "age": age,
            "female": female,
            "ckd_stage": stage,
        },
        references=["CKD-EPI 2021 (Inker et al., NEJM 2021)"],
    )


# ============================================================================
# Wells Score for DVT
# ============================================================================

def calculate_wells_dvt(
    active_cancer: bool = False,
    paralysis_immobilization: bool = False,
    bedridden_surgery: bool = False,
    localized_tenderness: bool = False,
    entire_leg_swollen: bool = False,
    calf_swelling_3cm: bool = False,
    pitting_edema: bool = False,
    collateral_veins: bool = False,
    previous_dvt: bool = False,
    alternative_diagnosis_likely: bool = False,
) -> CalculatorResult:
    """Calculate Wells Score for DVT probability.

    Args:
        active_cancer: Active cancer (treatment within 6 months).
        paralysis_immobilization: Paralysis or recent immobilization.
        bedridden_surgery: Bedridden >3 days or major surgery within 12 weeks.
        localized_tenderness: Localized tenderness along deep venous system.
        entire_leg_swollen: Entire leg swollen.
        calf_swelling_3cm: Calf swelling >3 cm compared to asymptomatic leg.
        pitting_edema: Pitting edema in symptomatic leg.
        collateral_veins: Collateral superficial veins (non-varicose).
        previous_dvt: Previous documented DVT.
        alternative_diagnosis_likely: Alternative diagnosis at least as likely.

    Returns:
        CalculatorResult with DVT probability assessment.
    """
    score = 0
    components = {}

    if active_cancer:
        score += 1
        components["Active cancer"] = 1
    if paralysis_immobilization:
        score += 1
        components["Paralysis/immobilization"] = 1
    if bedridden_surgery:
        score += 1
        components["Bedridden/surgery"] = 1
    if localized_tenderness:
        score += 1
        components["Localized tenderness"] = 1
    if entire_leg_swollen:
        score += 1
        components["Entire leg swollen"] = 1
    if calf_swelling_3cm:
        score += 1
        components["Calf swelling >3cm"] = 1
    if pitting_edema:
        score += 1
        components["Pitting edema"] = 1
    if collateral_veins:
        score += 1
        components["Collateral veins"] = 1
    if previous_dvt:
        score += 1
        components["Previous DVT"] = 1
    if alternative_diagnosis_likely:
        score -= 2
        components["Alternative diagnosis likely"] = -2

    # Risk stratification
    if score <= 0:
        risk = RiskLevel.LOW
        interpretation = "Low probability (~5% DVT risk)"
        recommendations = [
            "Check D-dimer",
            "If D-dimer negative, DVT excluded",
            "If D-dimer positive, perform ultrasound",
        ]
    elif score <= 2:
        risk = RiskLevel.MODERATE
        interpretation = "Moderate probability (~17% DVT risk)"
        recommendations = [
            "Check D-dimer",
            "If D-dimer negative, DVT unlikely",
            "If D-dimer positive, perform ultrasound",
        ]
    else:
        risk = RiskLevel.HIGH
        interpretation = "High probability (~53% DVT risk)"
        recommendations = [
            "Perform venous ultrasound",
            "Consider empiric anticoagulation while awaiting imaging",
            "D-dimer not recommended (high false negative rate)",
        ]

    return CalculatorResult(
        calculator_name="Wells Score for DVT",
        score=score,
        score_unit="points",
        risk_level=risk,
        interpretation=interpretation,
        recommendations=recommendations,
        components=components,
        references=["Wells PS, et al. NEJM 2003"],
    )


# ============================================================================
# CURB-65 (Pneumonia Severity)
# ============================================================================

def calculate_curb65(
    confusion: bool = False,
    bun_over_19: bool = False,
    respiratory_rate_over_30: bool = False,
    sbp_under_90_or_dbp_under_60: bool = False,
    age_65_or_older: bool = False,
) -> CalculatorResult:
    """Calculate CURB-65 score for community-acquired pneumonia severity.

    Args:
        confusion: New mental confusion (AMT ≤8 or disorientation).
        bun_over_19: BUN >19 mg/dL (or urea >7 mmol/L).
        respiratory_rate_over_30: Respiratory rate ≥30/min.
        sbp_under_90_or_dbp_under_60: SBP <90 or DBP ≤60 mmHg.
        age_65_or_older: Age ≥65 years.

    Returns:
        CalculatorResult with pneumonia severity and disposition.
    """
    score = 0
    components = {}

    if confusion:
        score += 1
        components["Confusion"] = 1
    if bun_over_19:
        score += 1
        components["BUN >19"] = 1
    if respiratory_rate_over_30:
        score += 1
        components["RR ≥30"] = 1
    if sbp_under_90_or_dbp_under_60:
        score += 1
        components["Low BP"] = 1
    if age_65_or_older:
        score += 1
        components["Age ≥65"] = 1

    # Risk stratification
    if score == 0:
        risk = RiskLevel.LOW
        mortality = "0.7%"
        interpretation = "Low risk - consider outpatient treatment"
        recommendations = [
            "Outpatient treatment appropriate",
            "Oral antibiotics",
            "Return precautions for worsening symptoms",
        ]
    elif score == 1:
        risk = RiskLevel.LOW
        mortality = "3.2%"
        interpretation = "Low risk - outpatient treatment likely appropriate"
        recommendations = [
            "Outpatient treatment likely appropriate",
            "Consider short observation in some cases",
            "Close follow-up in 24-48 hours",
        ]
    elif score == 2:
        risk = RiskLevel.MODERATE
        mortality = "13%"
        interpretation = "Moderate risk - consider hospital admission"
        recommendations = [
            "Hospital admission recommended",
            "IV antibiotics initially",
            "Oxygen supplementation as needed",
        ]
    elif score == 3:
        risk = RiskLevel.HIGH
        mortality = "17%"
        interpretation = "High risk - hospital admission required"
        recommendations = [
            "Inpatient treatment required",
            "Consider ICU admission",
            "IV antibiotics",
            "Close monitoring for deterioration",
        ]
    else:
        risk = RiskLevel.VERY_HIGH
        mortality = "41-57%"
        interpretation = "Very high risk - ICU admission recommended"
        recommendations = [
            "ICU admission strongly recommended",
            "Broad-spectrum IV antibiotics",
            "Monitor for sepsis and respiratory failure",
            "Consider mechanical ventilation readiness",
        ]

    return CalculatorResult(
        calculator_name="CURB-65 Score",
        score=score,
        score_unit="points",
        risk_level=risk,
        interpretation=f"{interpretation}. 30-day mortality: ~{mortality}",
        recommendations=recommendations,
        components=components,
        references=["Lim WS, et al. Thorax 2003"],
    )


# ============================================================================
# Framingham Risk Score (10-year CVD Risk)
# ============================================================================

def calculate_framingham_10yr(
    age: int,
    female: bool,
    total_cholesterol: float,
    hdl_cholesterol: float,
    systolic_bp: float,
    bp_treated: bool = False,
    smoker: bool = False,
    diabetic: bool = False,
) -> CalculatorResult:
    """Calculate Framingham 10-year cardiovascular disease risk.

    Args:
        age: Patient age in years (30-79).
        female: True if female.
        total_cholesterol: Total cholesterol in mg/dL.
        hdl_cholesterol: HDL cholesterol in mg/dL.
        systolic_bp: Systolic blood pressure in mmHg.
        bp_treated: True if on BP medication.
        smoker: Current smoker.
        diabetic: Has diabetes.

    Returns:
        CalculatorResult with 10-year CVD risk.
    """
    # Simplified Framingham calculation (based on 2008 general CVD risk)
    # Using point system for easier calculation

    points = 0
    components = {}

    # Age points
    if female:
        if age < 35:
            age_pts = -7
        elif age < 40:
            age_pts = -3
        elif age < 45:
            age_pts = 0
        elif age < 50:
            age_pts = 3
        elif age < 55:
            age_pts = 6
        elif age < 60:
            age_pts = 8
        elif age < 65:
            age_pts = 10
        elif age < 70:
            age_pts = 12
        elif age < 75:
            age_pts = 14
        else:
            age_pts = 16
    else:
        if age < 35:
            age_pts = -9
        elif age < 40:
            age_pts = -4
        elif age < 45:
            age_pts = 0
        elif age < 50:
            age_pts = 3
        elif age < 55:
            age_pts = 6
        elif age < 60:
            age_pts = 8
        elif age < 65:
            age_pts = 10
        elif age < 70:
            age_pts = 11
        elif age < 75:
            age_pts = 12
        else:
            age_pts = 13

    points += age_pts
    components["Age points"] = age_pts

    # Total cholesterol points
    if total_cholesterol < 160:
        tc_pts = 0
    elif total_cholesterol < 200:
        tc_pts = 1 if female else 1
    elif total_cholesterol < 240:
        tc_pts = 2 if female else 2
    elif total_cholesterol < 280:
        tc_pts = 3 if female else 3
    else:
        tc_pts = 4 if female else 4

    points += tc_pts
    components["Cholesterol points"] = tc_pts

    # HDL points
    if hdl_cholesterol >= 60:
        hdl_pts = -1
    elif hdl_cholesterol >= 50:
        hdl_pts = 0
    elif hdl_cholesterol >= 40:
        hdl_pts = 1
    else:
        hdl_pts = 2

    points += hdl_pts
    components["HDL points"] = hdl_pts

    # BP points
    if systolic_bp < 120:
        bp_pts = 0
    elif systolic_bp < 130:
        bp_pts = 1 if bp_treated else 0
    elif systolic_bp < 140:
        bp_pts = 2 if bp_treated else 1
    elif systolic_bp < 160:
        bp_pts = 3 if bp_treated else 2
    else:
        bp_pts = 4 if bp_treated else 3

    points += bp_pts
    components["BP points"] = bp_pts

    # Smoking
    if smoker:
        smoke_pts = 3 if female else 3
        points += smoke_pts
        components["Smoking"] = smoke_pts

    # Diabetes
    if diabetic:
        dm_pts = 4 if female else 3
        points += dm_pts
        components["Diabetes"] = dm_pts

    # Convert points to 10-year risk (simplified)
    if female:
        if points <= 0:
            risk_pct = 1
        elif points <= 5:
            risk_pct = 2
        elif points <= 8:
            risk_pct = 4
        elif points <= 11:
            risk_pct = 8
        elif points <= 14:
            risk_pct = 15
        elif points <= 17:
            risk_pct = 22
        else:
            risk_pct = 30
    else:
        if points <= 0:
            risk_pct = 1
        elif points <= 5:
            risk_pct = 3
        elif points <= 8:
            risk_pct = 6
        elif points <= 11:
            risk_pct = 11
        elif points <= 14:
            risk_pct = 18
        elif points <= 17:
            risk_pct = 27
        else:
            risk_pct = 35

    # Risk stratification
    if risk_pct < 5:
        risk = RiskLevel.LOW
        interpretation = f"Low 10-year CVD risk ({risk_pct}%)"
        recommendations = [
            "Lifestyle modifications recommended",
            "Healthy diet and regular exercise",
            "Reassess in 4-6 years",
        ]
    elif risk_pct < 10:
        risk = RiskLevel.LOW_MODERATE
        interpretation = f"Borderline 10-year CVD risk ({risk_pct}%)"
        recommendations = [
            "Aggressive lifestyle modifications",
            "Consider statin therapy if risk-enhancing factors",
            "Target LDL <100 mg/dL",
        ]
    elif risk_pct < 20:
        risk = RiskLevel.MODERATE
        interpretation = f"Intermediate 10-year CVD risk ({risk_pct}%)"
        recommendations = [
            "Moderate-intensity statin therapy recommended",
            "Target LDL <100 mg/dL (some recommend <70)",
            "Aspirin if benefit outweighs bleeding risk",
            "Strict BP control",
        ]
    else:
        risk = RiskLevel.HIGH
        interpretation = f"High 10-year CVD risk ({risk_pct}%)"
        recommendations = [
            "High-intensity statin therapy",
            "Target LDL <70 mg/dL",
            "Aspirin therapy",
            "Aggressive BP control (<130/80)",
            "Consider additional therapies (ezetimibe, PCSK9i)",
        ]

    return CalculatorResult(
        calculator_name="Framingham 10-Year CVD Risk",
        score=risk_pct,
        score_unit="%",
        risk_level=risk,
        interpretation=interpretation,
        recommendations=recommendations,
        components=components,
        references=["D'Agostino RB, et al. Circulation 2008"],
    )


# ============================================================================
# Calculator Service
# ============================================================================

class ClinicalCalculatorService:
    """Service for clinical risk calculations.

    Provides access to validated clinical calculators including:
    - BMI
    - CHA₂DS₂-VASc (stroke risk in AF)
    - HAS-BLED (bleeding risk)
    - MELD/MELD-Na (liver disease severity)
    - CKD-EPI eGFR (kidney function)
    - Wells DVT score
    - CURB-65 (pneumonia severity)
    - Framingham 10-year CVD risk

    Usage:
        service = ClinicalCalculatorService()

        # Calculate BMI
        result = service.calculate("bmi", weight_kg=70, height_cm=175)

        # Calculate stroke risk
        result = service.calculate("chadsvasc",
            age=72, female=True, hypertension=True, diabetes=True)
    """

    CALCULATORS = {
        "bmi": calculate_bmi,
        "chadsvasc": calculate_chadsvasc,
        "hasbled": calculate_hasbled,
        "meld": calculate_meld,
        "egfr": calculate_egfr_ckdepi,
        "wells_dvt": calculate_wells_dvt,
        "curb65": calculate_curb65,
        "framingham": calculate_framingham_10yr,
    }

    def __init__(self) -> None:
        """Initialize the calculator service."""
        pass

    def get_available_calculators(self) -> dict[str, str]:
        """Get list of available calculators with descriptions.

        Returns:
            Dict of calculator name to description.
        """
        return {
            "bmi": "Body Mass Index",
            "chadsvasc": "CHA₂DS₂-VASc Score (AF stroke risk)",
            "hasbled": "HAS-BLED Score (bleeding risk)",
            "meld": "MELD/MELD-Na Score (liver disease)",
            "egfr": "CKD-EPI eGFR (kidney function)",
            "wells_dvt": "Wells Score for DVT",
            "curb65": "CURB-65 (pneumonia severity)",
            "framingham": "Framingham 10-Year CVD Risk",
        }

    def calculate(
        self,
        calculator: str,
        **kwargs: Any,
    ) -> CalculatorResult:
        """Run a clinical calculator.

        Args:
            calculator: Name of calculator to run.
            **kwargs: Parameters for the calculator.

        Returns:
            CalculatorResult with score and interpretation.

        Raises:
            ValueError: If calculator not found or parameters invalid.
        """
        calc_name = calculator.lower().replace("-", "_")

        if calc_name not in self.CALCULATORS:
            available = ", ".join(self.CALCULATORS.keys())
            raise ValueError(f"Unknown calculator: {calculator}. Available: {available}")

        calc_func = self.CALCULATORS[calc_name]

        try:
            return calc_func(**kwargs)
        except TypeError as e:
            raise ValueError(f"Invalid parameters for {calculator}: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about available calculators.

        Returns:
            Dictionary with calculator statistics.
        """
        return {
            "total_calculators": len(self.CALCULATORS),
            "calculator_list": list(self.CALCULATORS.keys()),
        }


# Singleton instance and lock
_clinical_calculator_service: ClinicalCalculatorService | None = None
_clinical_calculator_lock = Lock()


def get_clinical_calculator_service() -> ClinicalCalculatorService:
    """Get the singleton ClinicalCalculatorService instance.

    Returns:
        The singleton ClinicalCalculatorService instance.
    """
    global _clinical_calculator_service

    if _clinical_calculator_service is None:
        with _clinical_calculator_lock:
            if _clinical_calculator_service is None:
                logger.info("Creating singleton ClinicalCalculatorService instance")
                _clinical_calculator_service = ClinicalCalculatorService()

    return _clinical_calculator_service


def reset_clinical_calculator_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _clinical_calculator_service
    with _clinical_calculator_lock:
        _clinical_calculator_service = None
