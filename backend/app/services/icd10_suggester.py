"""ICD-10 Code Suggester Service.

This module provides ICD-10 code suggestions based on clinical text,
diagnoses, and extracted information. It supports:

- Text-to-code mapping with natural language processing
- Synonym and alias matching
- Code hierarchy navigation
- Specificity guidance

Note: Code suggestions should be verified by qualified medical coders.
ICD-10-CM codes are for US clinical use.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
import threading


class CodeConfidence(Enum):
    """Confidence level for code suggestion."""

    HIGH = "high"  # Direct match or well-established mapping
    MEDIUM = "medium"  # Good match but may need verification
    LOW = "low"  # Possible match, needs review


@dataclass
class CERCitation:
    """Claim-Evidence-Reasoning citation for an ICD-10 code suggestion.

    This framework helps clinicians understand WHY a code is suggested:
    - Claim: What code is being suggested and why
    - Evidence: Clinical documentation/findings supporting this code
    - Reasoning: Explanation connecting evidence to the code selection
    """

    claim: str  # The assertion (e.g., "I10 is appropriate for this patient")
    evidence: list[str]  # Clinical findings supporting the claim
    reasoning: str  # Explanation connecting evidence to claim
    strength: CodeConfidence  # How strong is this CER
    icd10_guidelines: list[str] = field(default_factory=list)  # Relevant ICD-10 coding guidelines


class CodeCategory(Enum):
    """ICD-10 chapter categories."""

    A00_B99 = "Infectious and Parasitic Diseases"
    C00_D49 = "Neoplasms"
    D50_D89 = "Blood and Blood-forming Organs"
    E00_E89 = "Endocrine, Nutritional and Metabolic"
    F01_F99 = "Mental, Behavioral and Neurodevelopmental"
    G00_G99 = "Nervous System"
    H00_H59 = "Eye and Adnexa"
    H60_H95 = "Ear and Mastoid Process"
    I00_I99 = "Circulatory System"
    J00_J99 = "Respiratory System"
    K00_K95 = "Digestive System"
    L00_L99 = "Skin and Subcutaneous Tissue"
    M00_M99 = "Musculoskeletal System"
    N00_N99 = "Genitourinary System"
    O00_O9A = "Pregnancy, Childbirth and Puerperium"
    P00_P96 = "Perinatal Period"
    Q00_Q99 = "Congenital Malformations"
    R00_R99 = "Symptoms, Signs and Abnormal Findings"
    S00_T88 = "Injury, Poisoning and External Causes"
    V00_Y99 = "External Causes of Morbidity"
    Z00_Z99 = "Factors Influencing Health Status"


@dataclass
class ICD10Code:
    """An ICD-10-CM code with description."""

    code: str
    description: str
    category: CodeCategory
    is_billable: bool = True
    parent_code: str | None = None
    includes: list[str] = field(default_factory=list)  # Included conditions
    excludes1: list[str] = field(default_factory=list)  # Not coded here
    excludes2: list[str] = field(default_factory=list)  # Not included but may coexist
    use_additional_code: str | None = None
    code_first: str | None = None
    omop_concept_id: int | None = None
    synonyms: list[str] = field(default_factory=list)


@dataclass
class CodeSuggestion:
    """A suggested ICD-10 code with CER citation."""

    code: str
    description: str
    confidence: CodeConfidence
    match_reason: str
    is_billable: bool
    category: str

    # CER Framework for explaining why this code is suggested
    cer_citation: CERCitation | None = None

    more_specific_codes: list[tuple[str, str]] = field(default_factory=list)  # (code, description)
    related_codes: list[tuple[str, str]] = field(default_factory=list)
    coding_guidance: list[str] = field(default_factory=list)


@dataclass
class SuggestionResult:
    """Result from ICD-10 code suggestion."""

    query: str
    suggestions: list[CodeSuggestion]
    total_matches: int
    coding_tips: list[str]


# ============================================================================
# ICD-10 Code Database
# ============================================================================

# Core ICD-10-CM codes commonly used in clinical practice
ICD10_CODES: list[ICD10Code] = [
    # =========================================================================
    # INFECTIOUS DISEASES (A00-B99)
    # =========================================================================
    ICD10Code(
        code="A41.9",
        description="Sepsis, unspecified organism",
        category=CodeCategory.A00_B99,
        synonyms=["sepsis", "septicemia", "blood poisoning"],
        use_additional_code="code to identify severe sepsis (R65.2-)",
    ),
    ICD10Code(
        code="B34.9",
        description="Viral infection, unspecified",
        category=CodeCategory.A00_B99,
        synonyms=["viral syndrome", "viral illness"],
    ),
    # =========================================================================
    # NEOPLASMS (C00-D49)
    # =========================================================================
    ICD10Code(
        code="C34.90",
        description="Malignant neoplasm of unspecified part of unspecified bronchus or lung",
        category=CodeCategory.C00_D49,
        synonyms=["lung cancer", "bronchogenic carcinoma", "lung malignancy"],
    ),
    ICD10Code(
        code="C50.919",
        description="Malignant neoplasm of unspecified site of unspecified female breast",
        category=CodeCategory.C00_D49,
        synonyms=["breast cancer", "breast malignancy"],
    ),
    # =========================================================================
    # ENDOCRINE (E00-E89)
    # =========================================================================
    ICD10Code(
        code="E11.9",
        description="Type 2 diabetes mellitus without complications",
        category=CodeCategory.E00_E89,
        omop_concept_id=201826,
        synonyms=["diabetes", "dm2", "type 2 dm", "adult onset diabetes", "niddm"],
    ),
    ICD10Code(
        code="E11.65",
        description="Type 2 diabetes mellitus with hyperglycemia",
        category=CodeCategory.E00_E89,
        parent_code="E11",
        synonyms=["uncontrolled diabetes", "high blood sugar"],
    ),
    ICD10Code(
        code="E10.9",
        description="Type 1 diabetes mellitus without complications",
        category=CodeCategory.E00_E89,
        synonyms=["type 1 diabetes", "dm1", "juvenile diabetes", "iddm"],
    ),
    ICD10Code(
        code="E03.9",
        description="Hypothyroidism, unspecified",
        category=CodeCategory.E00_E89,
        synonyms=["hypothyroid", "low thyroid", "underactive thyroid"],
    ),
    ICD10Code(
        code="E05.90",
        description="Thyrotoxicosis, unspecified without thyrotoxic crisis or storm",
        category=CodeCategory.E00_E89,
        synonyms=["hyperthyroidism", "overactive thyroid", "thyrotoxicosis"],
    ),
    ICD10Code(
        code="E78.5",
        description="Hyperlipidemia, unspecified",
        category=CodeCategory.E00_E89,
        omop_concept_id=432867,
        synonyms=["high cholesterol", "hypercholesterolemia", "dyslipidemia", "elevated lipids"],
    ),
    ICD10Code(
        code="E66.9",
        description="Obesity, unspecified",
        category=CodeCategory.E00_E89,
        synonyms=["obese", "morbid obesity"],
    ),
    # =========================================================================
    # MENTAL DISORDERS (F01-F99)
    # =========================================================================
    ICD10Code(
        code="F32.9",
        description="Major depressive disorder, single episode, unspecified",
        category=CodeCategory.F01_F99,
        synonyms=["depression", "mdd", "major depression", "clinical depression"],
    ),
    ICD10Code(
        code="F41.1",
        description="Generalized anxiety disorder",
        category=CodeCategory.F01_F99,
        synonyms=["anxiety", "gad", "generalized anxiety"],
    ),
    ICD10Code(
        code="F17.210",
        description="Nicotine dependence, cigarettes, uncomplicated",
        category=CodeCategory.F01_F99,
        synonyms=["smoking", "tobacco use", "cigarette smoking", "nicotine addiction"],
    ),
    # =========================================================================
    # NEUROLOGICAL (G00-G99)
    # =========================================================================
    ICD10Code(
        code="G43.909",
        description="Migraine, unspecified, not intractable, without status migrainosus",
        category=CodeCategory.G00_G99,
        synonyms=["migraine", "migraine headache"],
    ),
    ICD10Code(
        code="G40.909",
        description="Epilepsy, unspecified, not intractable, without status epilepticus",
        category=CodeCategory.G00_G99,
        synonyms=["epilepsy", "seizure disorder", "seizures"],
    ),
    ICD10Code(
        code="G89.29",
        description="Other chronic pain",
        category=CodeCategory.G00_G99,
        synonyms=["chronic pain", "persistent pain"],
    ),
    # =========================================================================
    # CARDIOVASCULAR (I00-I99)
    # =========================================================================
    ICD10Code(
        code="I10",
        description="Essential (primary) hypertension",
        category=CodeCategory.I00_I99,
        omop_concept_id=320128,
        synonyms=["hypertension", "htn", "high blood pressure", "elevated bp"],
    ),
    ICD10Code(
        code="I25.10",
        description="Atherosclerotic heart disease of native coronary artery without angina pectoris",
        category=CodeCategory.I00_I99,
        synonyms=["coronary artery disease", "cad", "ischemic heart disease", "chd"],
    ),
    ICD10Code(
        code="I21.9",
        description="Acute myocardial infarction, unspecified",
        category=CodeCategory.I00_I99,
        omop_concept_id=4329847,
        synonyms=["heart attack", "mi", "ami", "myocardial infarction", "stemi", "nstemi"],
    ),
    ICD10Code(
        code="I48.91",
        description="Unspecified atrial fibrillation",
        category=CodeCategory.I00_I99,
        omop_concept_id=313217,
        synonyms=["afib", "atrial fibrillation", "a-fib", "af"],
    ),
    ICD10Code(
        code="I50.9",
        description="Heart failure, unspecified",
        category=CodeCategory.I00_I99,
        omop_concept_id=316139,
        synonyms=["chf", "congestive heart failure", "heart failure", "cardiac failure"],
    ),
    ICD10Code(
        code="I50.22",
        description="Chronic systolic (congestive) heart failure",
        category=CodeCategory.I00_I99,
        parent_code="I50",
        synonyms=["systolic heart failure", "hfref", "reduced ef"],
    ),
    ICD10Code(
        code="I50.32",
        description="Chronic diastolic (congestive) heart failure",
        category=CodeCategory.I00_I99,
        parent_code="I50",
        synonyms=["diastolic heart failure", "hfpef", "preserved ef"],
    ),
    ICD10Code(
        code="I63.9",
        description="Cerebral infarction, unspecified",
        category=CodeCategory.I00_I99,
        omop_concept_id=443454,
        synonyms=["stroke", "cva", "ischemic stroke", "cerebrovascular accident"],
    ),
    ICD10Code(
        code="I26.99",
        description="Other pulmonary embolism without acute cor pulmonale",
        category=CodeCategory.I00_I99,
        synonyms=["pulmonary embolism", "pe", "pulmonary embolus"],
    ),
    ICD10Code(
        code="I82.409",
        description="Acute embolism and thrombosis of unspecified deep veins of unspecified lower extremity",
        category=CodeCategory.I00_I99,
        synonyms=["dvt", "deep vein thrombosis", "deep venous thrombosis"],
    ),
    # =========================================================================
    # RESPIRATORY (J00-J99)
    # =========================================================================
    ICD10Code(
        code="J18.9",
        description="Pneumonia, unspecified organism",
        category=CodeCategory.J00_J99,
        omop_concept_id=255848,
        synonyms=["pneumonia", "lung infection"],
    ),
    ICD10Code(
        code="J06.9",
        description="Acute upper respiratory infection, unspecified",
        category=CodeCategory.J00_J99,
        synonyms=["uri", "upper respiratory infection", "cold", "common cold"],
    ),
    ICD10Code(
        code="J44.1",
        description="Chronic obstructive pulmonary disease with (acute) exacerbation",
        category=CodeCategory.J00_J99,
        omop_concept_id=255573,
        synonyms=["copd exacerbation", "copd flare"],
    ),
    ICD10Code(
        code="J44.9",
        description="Chronic obstructive pulmonary disease, unspecified",
        category=CodeCategory.J00_J99,
        synonyms=["copd", "chronic obstructive pulmonary disease", "emphysema"],
    ),
    ICD10Code(
        code="J45.909",
        description="Unspecified asthma, uncomplicated",
        category=CodeCategory.J00_J99,
        omop_concept_id=317009,
        synonyms=["asthma", "bronchial asthma", "reactive airway disease"],
    ),
    ICD10Code(
        code="J45.901",
        description="Unspecified asthma with (acute) exacerbation",
        category=CodeCategory.J00_J99,
        parent_code="J45",
        synonyms=["asthma exacerbation", "asthma attack", "acute asthma"],
    ),
    # =========================================================================
    # GASTROINTESTINAL (K00-K95)
    # =========================================================================
    ICD10Code(
        code="K21.0",
        description="Gastro-esophageal reflux disease with esophagitis",
        category=CodeCategory.K00_K95,
        synonyms=["gerd", "acid reflux", "reflux esophagitis"],
    ),
    ICD10Code(
        code="K35.80",
        description="Unspecified acute appendicitis",
        category=CodeCategory.K00_K95,
        omop_concept_id=440448,
        synonyms=["appendicitis", "acute appendicitis"],
    ),
    ICD10Code(
        code="K80.20",
        description="Calculus of gallbladder without cholecystitis without obstruction",
        category=CodeCategory.K00_K95,
        synonyms=["gallstones", "cholelithiasis"],
    ),
    ICD10Code(
        code="K81.0",
        description="Acute cholecystitis",
        category=CodeCategory.K00_K95,
        omop_concept_id=201606,
        synonyms=["cholecystitis", "gallbladder inflammation"],
    ),
    ICD10Code(
        code="K76.0",
        description="Fatty (change of) liver, not elsewhere classified",
        category=CodeCategory.K00_K95,
        synonyms=["fatty liver", "nafld", "hepatic steatosis", "nash"],
    ),
    # =========================================================================
    # MUSCULOSKELETAL (M00-M99)
    # =========================================================================
    ICD10Code(
        code="M54.5",
        description="Low back pain",
        category=CodeCategory.M00_M99,
        synonyms=["low back pain", "lbp", "lumbar pain", "lumbago"],
    ),
    ICD10Code(
        code="M54.2",
        description="Cervicalgia",
        category=CodeCategory.M00_M99,
        synonyms=["neck pain", "cervical pain"],
    ),
    ICD10Code(
        code="M17.9",
        description="Osteoarthritis of knee, unspecified",
        category=CodeCategory.M00_M99,
        synonyms=["knee osteoarthritis", "knee oa", "degenerative joint disease knee"],
    ),
    ICD10Code(
        code="M10.9",
        description="Gout, unspecified",
        category=CodeCategory.M00_M99,
        omop_concept_id=4070697,
        synonyms=["gout", "gouty arthritis"],
    ),
    ICD10Code(
        code="M79.3",
        description="Panniculitis, unspecified",
        category=CodeCategory.M00_M99,
        synonyms=["fibromyalgia", "chronic widespread pain"],
        # Note: Fibromyalgia has specific code M79.7
    ),
    ICD10Code(
        code="M51.16",
        description="Intervertebral disc disorders with radiculopathy, lumbar region",
        category=CodeCategory.M00_M99,
        omop_concept_id=4063684,
        synonyms=["lumbar disc herniation", "herniated disc", "sciatica", "lumbar radiculopathy"],
    ),
    # =========================================================================
    # GENITOURINARY (N00-N99)
    # =========================================================================
    ICD10Code(
        code="N39.0",
        description="Urinary tract infection, site not specified",
        category=CodeCategory.N00_N99,
        omop_concept_id=81902,
        synonyms=["uti", "urinary tract infection", "bladder infection"],
    ),
    ICD10Code(
        code="N18.9",
        description="Chronic kidney disease, unspecified",
        category=CodeCategory.N00_N99,
        synonyms=["ckd", "chronic kidney disease", "chronic renal failure"],
    ),
    ICD10Code(
        code="N18.3",
        description="Chronic kidney disease, stage 3 (moderate)",
        category=CodeCategory.N00_N99,
        parent_code="N18",
        synonyms=["ckd stage 3", "moderate ckd"],
    ),
    ICD10Code(
        code="N40.0",
        description="Benign prostatic hyperplasia without lower urinary tract symptoms",
        category=CodeCategory.N00_N99,
        synonyms=["bph", "benign prostatic hyperplasia", "enlarged prostate"],
    ),
    # =========================================================================
    # SYMPTOMS AND SIGNS (R00-R99)
    # =========================================================================
    ICD10Code(
        code="R05",
        description="Cough",
        category=CodeCategory.R00_R99,
        synonyms=["cough", "coughing"],
    ),
    ICD10Code(
        code="R06.02",
        description="Shortness of breath",
        category=CodeCategory.R00_R99,
        synonyms=["dyspnea", "sob", "shortness of breath", "breathlessness"],
    ),
    ICD10Code(
        code="R07.9",
        description="Chest pain, unspecified",
        category=CodeCategory.R00_R99,
        synonyms=["chest pain", "chest discomfort"],
    ),
    ICD10Code(
        code="R10.9",
        description="Unspecified abdominal pain",
        category=CodeCategory.R00_R99,
        synonyms=["abdominal pain", "stomach pain", "belly pain"],
    ),
    ICD10Code(
        code="R51",
        description="Headache",
        category=CodeCategory.R00_R99,
        synonyms=["headache", "head pain", "cephalgia"],
    ),
    ICD10Code(
        code="R53.83",
        description="Other fatigue",
        category=CodeCategory.R00_R99,
        synonyms=["fatigue", "tiredness", "malaise"],
    ),
    ICD10Code(
        code="R42",
        description="Dizziness and giddiness",
        category=CodeCategory.R00_R99,
        synonyms=["dizziness", "vertigo", "lightheadedness"],
    ),
    ICD10Code(
        code="R50.9",
        description="Fever, unspecified",
        category=CodeCategory.R00_R99,
        synonyms=["fever", "febrile"],
    ),
    ICD10Code(
        code="R11.2",
        description="Nausea with vomiting, unspecified",
        category=CodeCategory.R00_R99,
        synonyms=["nausea and vomiting", "n/v"],
    ),
    # =========================================================================
    # INJURY AND POISONING (S00-T88)
    # =========================================================================
    ICD10Code(
        code="S72.90XA",
        description="Unspecified fracture of unspecified femur, initial encounter for closed fracture",
        category=CodeCategory.S00_T88,
        synonyms=["hip fracture", "femur fracture", "broken hip"],
    ),
    ICD10Code(
        code="S52.509A",
        description="Unspecified fracture of the lower end of unspecified radius, initial encounter for closed fracture",
        category=CodeCategory.S00_T88,
        synonyms=["wrist fracture", "colles fracture", "distal radius fracture"],
    ),
    # =========================================================================
    # FACTORS INFLUENCING HEALTH (Z00-Z99)
    # =========================================================================
    ICD10Code(
        code="Z87.891",
        description="Personal history of nicotine dependence",
        category=CodeCategory.Z00_Z99,
        synonyms=["former smoker", "history of smoking", "quit smoking"],
    ),
    ICD10Code(
        code="Z79.4",
        description="Long term (current) use of insulin",
        category=CodeCategory.Z00_Z99,
        synonyms=["insulin use", "on insulin"],
    ),
    ICD10Code(
        code="Z79.01",
        description="Long term (current) use of anticoagulants",
        category=CodeCategory.Z00_Z99,
        synonyms=["on anticoagulation", "on blood thinners", "on warfarin"],
    ),
    ICD10Code(
        code="Z96.1",
        description="Presence of intraocular lens",
        category=CodeCategory.Z00_Z99,
        synonyms=["pseudophakia", "iol", "lens implant"],
    ),
]

# Build synonym index for fast lookup
SYNONYM_TO_CODE: dict[str, list[str]] = {}
for _code in ICD10_CODES:
    for syn in _code.synonyms:
        syn_lower = syn.lower()
        if syn_lower not in SYNONYM_TO_CODE:
            SYNONYM_TO_CODE[syn_lower] = []
        SYNONYM_TO_CODE[syn_lower].append(_code.code)


# ============================================================================
# ICD-10 Suggester Service
# ============================================================================

# Singleton instance and lock for thread safety
_icd10_service: "ICD10SuggesterService | None" = None
_icd10_lock = threading.Lock()


def get_icd10_suggester_service() -> "ICD10SuggesterService":
    """Get the singleton ICD-10 suggester service instance."""
    global _icd10_service
    if _icd10_service is None:
        with _icd10_lock:
            if _icd10_service is None:
                _icd10_service = ICD10SuggesterService()
    return _icd10_service


def reset_icd10_suggester_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _icd10_service
    with _icd10_lock:
        _icd10_service = None


class ICD10SuggesterService:
    """Service for suggesting ICD-10 codes from clinical text."""

    def __init__(self) -> None:
        """Initialize the ICD-10 suggester service."""
        self._codes: dict[str, ICD10Code] = {}
        self._synonym_index: dict[str, list[str]] = SYNONYM_TO_CODE.copy()

        # Index codes by code
        for code in ICD10_CODES:
            self._codes[code.code] = code

    def suggest_codes(
        self,
        query: str,
        max_suggestions: int = 10,
    ) -> SuggestionResult:
        """Suggest ICD-10 codes for a clinical query.

        Args:
            query: Clinical text or diagnosis name
            max_suggestions: Maximum number of suggestions to return

        Returns:
            SuggestionResult with matched codes.
        """
        query_lower = query.lower().strip()
        suggestions: list[CodeSuggestion] = []
        seen_codes: set[str] = set()

        # 1. Exact synonym match (highest confidence)
        if query_lower in self._synonym_index:
            for code_str in self._synonym_index[query_lower]:
                if code_str in self._codes and code_str not in seen_codes:
                    code = self._codes[code_str]
                    suggestions.append(self._create_suggestion(
                        code, CodeConfidence.HIGH, f"Exact match for '{query}'", query
                    ))
                    seen_codes.add(code_str)

        # 2. Partial synonym match (medium confidence)
        for synonym, code_list in self._synonym_index.items():
            if query_lower in synonym or synonym in query_lower:
                for code_str in code_list:
                    if code_str in self._codes and code_str not in seen_codes:
                        code = self._codes[code_str]
                        suggestions.append(self._create_suggestion(
                            code, CodeConfidence.MEDIUM, f"Partial match: '{synonym}'", query
                        ))
                        seen_codes.add(code_str)

        # 3. Description search (lower confidence)
        query_words = set(query_lower.split())
        for code in self._codes.values():
            if code.code in seen_codes:
                continue

            desc_lower = code.description.lower()
            desc_words = set(desc_lower.split())

            # Check for word overlap
            common_words = query_words & desc_words
            # Filter out common stopwords
            stopwords = {"of", "the", "and", "or", "a", "an", "with", "without", "unspecified", "other"}
            meaningful_common = common_words - stopwords

            if len(meaningful_common) >= 2 or (len(meaningful_common) == 1 and len(query_words) <= 2):
                suggestions.append(self._create_suggestion(
                    code, CodeConfidence.LOW, f"Description match: {', '.join(meaningful_common)}", query
                ))
                seen_codes.add(code.code)

        # Sort by confidence and limit
        confidence_order = {CodeConfidence.HIGH: 0, CodeConfidence.MEDIUM: 1, CodeConfidence.LOW: 2}
        suggestions.sort(key=lambda s: confidence_order[s.confidence])

        # Generate coding tips
        coding_tips = self._generate_coding_tips(query, suggestions)

        return SuggestionResult(
            query=query,
            suggestions=suggestions[:max_suggestions],
            total_matches=len(suggestions),
            coding_tips=coding_tips,
        )

    def _create_suggestion(
        self,
        code: ICD10Code,
        confidence: CodeConfidence,
        match_reason: str,
        query: str = "",
    ) -> CodeSuggestion:
        """Create a code suggestion from an ICD10Code with CER citation."""
        # Find more specific codes
        more_specific: list[tuple[str, str]] = []
        for other_code in self._codes.values():
            if other_code.parent_code == code.code:
                more_specific.append((other_code.code, other_code.description))

        # Find related codes (same parent)
        related: list[tuple[str, str]] = []
        if code.parent_code:
            for other_code in self._codes.values():
                if other_code.parent_code == code.parent_code and other_code.code != code.code:
                    related.append((other_code.code, other_code.description))

        # Build coding guidance
        guidance: list[str] = []
        if code.use_additional_code:
            guidance.append(f"Use additional code: {code.use_additional_code}")
        if code.code_first:
            guidance.append(f"Code first: {code.code_first}")
        if not code.is_billable:
            guidance.append("Non-billable code - use more specific code")
        if more_specific:
            guidance.append(f"More specific codes available ({len(more_specific)} options)")

        # Build CER citation
        cer_citation = self._build_cer_citation(code, confidence, match_reason, query, guidance)

        return CodeSuggestion(
            code=code.code,
            description=code.description,
            confidence=confidence,
            match_reason=match_reason,
            is_billable=code.is_billable,
            category=code.category.value,
            cer_citation=cer_citation,
            more_specific_codes=more_specific[:5],
            related_codes=related[:5],
            coding_guidance=guidance,
        )

    def _build_cer_citation(
        self,
        code: ICD10Code,
        confidence: CodeConfidence,
        match_reason: str,
        query: str,
        guidance: list[str],
    ) -> CERCitation:
        """Build a CER (Claim-Evidence-Reasoning) citation for an ICD-10 code.

        This provides structured justification for why a code is being suggested.
        """
        # Build the claim
        claim = f"{code.code} ({code.description}) is the appropriate ICD-10-CM code for this diagnosis"

        # Build evidence list from clinical indicators
        evidence: list[str] = []

        # Evidence from the matched synonyms
        if code.synonyms:
            matched_synonyms = [syn for syn in code.synonyms if syn.lower() in query.lower()]
            if matched_synonyms:
                evidence.append(f"Documentation indicates: {', '.join(matched_synonyms[:3])}")
            else:
                evidence.append(f"Common clinical terms: {', '.join(code.synonyms[:3])}")

        # Evidence from the match reason
        evidence.append(f"Match basis: {match_reason}")

        # Evidence from code characteristics
        if code.is_billable:
            evidence.append("Code is billable and specific")
        else:
            evidence.append("Code requires additional specificity for billing")

        # Evidence from category
        evidence.append(f"ICD-10 Chapter: {code.category.value}")

        # Evidence from OMOP mapping
        if code.omop_concept_id:
            evidence.append(f"OMOP standardized concept available (ID: {code.omop_concept_id})")

        # Build reasoning that connects evidence to claim
        reasoning_parts = []

        # Reasoning based on confidence level
        if confidence == CodeConfidence.HIGH:
            reasoning_parts.append(
                f"The documented clinical finding directly maps to {code.code} "
                f"through established terminology."
            )
        elif confidence == CodeConfidence.MEDIUM:
            reasoning_parts.append(
                f"The clinical documentation suggests {code.code} based on "
                f"partial terminology match. Review for specificity."
            )
        else:
            reasoning_parts.append(
                f"The documentation may support {code.code}. "
                f"Additional clinical detail may yield a more specific code."
            )

        # Reasoning about specificity
        if not code.is_billable or code.description.lower().find("unspecified") != -1:
            reasoning_parts.append(
                "Consider if more specific documentation is available to support a more precise code."
            )

        # Reasoning about coding sequence
        if code.code_first:
            reasoning_parts.append(f"Per ICD-10 guidelines, code the underlying condition first.")
        if code.use_additional_code:
            reasoning_parts.append(
                f"ICD-10 guidelines indicate additional codes may be required for completeness."
            )

        reasoning = " ".join(reasoning_parts)

        # Build ICD-10 specific guidelines
        icd10_guidelines: list[str] = []
        if code.code_first:
            icd10_guidelines.append(f"Code first: {code.code_first}")
        if code.use_additional_code:
            icd10_guidelines.append(f"Use additional code: {code.use_additional_code}")
        if code.excludes1:
            icd10_guidelines.append(f"Excludes1: {', '.join(code.excludes1[:2])}")
        if code.excludes2:
            icd10_guidelines.append(f"Excludes2: {', '.join(code.excludes2[:2])}")
        if code.includes:
            icd10_guidelines.append(f"Includes: {', '.join(code.includes[:2])}")

        # Add standard ICD-10 coding guidance
        if "unspecified" in code.description.lower():
            icd10_guidelines.append(
                "Per ICD-10 coding guidelines, unspecified codes should only be used "
                "when documentation does not support a more specific code."
            )

        return CERCitation(
            claim=claim,
            evidence=evidence,
            reasoning=reasoning,
            strength=confidence,
            icd10_guidelines=icd10_guidelines,
        )

    def _generate_coding_tips(
        self,
        query: str,
        suggestions: list[CodeSuggestion],
    ) -> list[str]:
        """Generate coding tips based on query and suggestions."""
        tips: list[str] = []

        # Check for unspecified codes
        unspecified_count = sum(1 for s in suggestions if "unspecified" in s.description.lower())
        if unspecified_count > 0:
            tips.append("Consider documenting more specifics to use a more specific code")

        # Check for multiple high-confidence matches
        high_confidence = [s for s in suggestions if s.confidence == CodeConfidence.HIGH]
        if len(high_confidence) > 1:
            tips.append("Multiple good matches found - review clinical context to select best code")

        # Query-specific tips
        query_lower = query.lower()
        if "diabetes" in query_lower:
            tips.append("For diabetes, code type (1 or 2) and any complications separately")
        if "hypertension" in query_lower:
            tips.append("Code hypertensive heart/kidney disease if applicable (I11, I12, I13)")
        if "pain" in query_lower:
            tips.append("Document underlying cause if known - pain codes are often secondary")
        if "cancer" in query_lower or "malignant" in query_lower:
            tips.append("Code primary site and any metastases separately")

        return tips[:5]

    def get_code(self, code: str) -> ICD10Code | None:
        """Get a specific ICD-10 code."""
        return self._codes.get(code.upper())

    def search_codes(self, query: str, limit: int = 20) -> list[ICD10Code]:
        """Search for codes by description or synonym."""
        query_lower = query.lower()
        matches: list[ICD10Code] = []

        for code in self._codes.values():
            if query_lower in code.description.lower():
                matches.append(code)
                continue
            if any(query_lower in syn.lower() for syn in code.synonyms):
                matches.append(code)

        return matches[:limit]

    def get_codes_by_category(self, category: CodeCategory) -> list[ICD10Code]:
        """Get all codes in a category."""
        return [code for code in self._codes.values() if code.category == category]

    def get_stats(self) -> dict:
        """Get statistics about the code database."""
        by_category: dict[str, int] = {}
        billable_count = 0
        with_omop = 0

        for code in self._codes.values():
            cat = code.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            if code.is_billable:
                billable_count += 1
            if code.omop_concept_id:
                with_omop += 1

        return {
            "total_codes": len(self._codes),
            "total_synonyms": len(self._synonym_index),
            "billable_codes": billable_count,
            "with_omop_mapping": with_omop,
            "by_category": by_category,
        }
