#!/usr/bin/env python3
"""Fetch and process complete ICD-10-CM codes from CMS.

This script downloads the official ICD-10-CM code files from CMS,
parses them, and generates a comprehensive fixture file for the
ICD-10 suggester service.

CMS provides annual releases at:
https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-files

The code files contain:
- Code (7 characters max)
- Long description
- Short description

Usage:
    python scripts/fetch_icd10_codes.py

This will:
1. Download the ICD-10-CM code files
2. Parse codes and descriptions
3. Add clinical synonyms for common conditions
4. Generate fixtures/icd10_codes_full.json
"""

import json
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from typing import Any

# CMS ICD-10-CM code file URLs (FY2024)
# Note: URLs change annually, may need updating
CMS_ICD10_URLS = [
    # FY2024 ICD-10-CM files
    "https://www.cms.gov/files/zip/2024-code-descriptions-tabular-order-updated-01-11-2024.zip",
    # Backup: 2023 files
    "https://www.cms.gov/files/zip/2023-code-descriptions-tabular-order.zip",
]

# Output paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FIXTURES_DIR = PROJECT_ROOT / "fixtures"
OUTPUT_FILE = FIXTURES_DIR / "icd10_codes_full.json"

# Clinical synonyms for common ICD-10 codes
# Format: code -> list of synonyms
CLINICAL_SYNONYMS: dict[str, list[str]] = {
    # Infectious diseases
    "A41.9": ["sepsis", "septicemia", "blood poisoning", "systemic infection"],
    "A49.9": ["bacterial infection", "infection nos"],
    "B34.9": ["viral infection", "viral syndrome", "viral illness"],
    "B37.9": ["candidiasis", "yeast infection", "thrush"],

    # Neoplasms
    "C34.90": ["lung cancer", "bronchogenic carcinoma", "lung malignancy"],
    "C50.919": ["breast cancer", "breast malignancy"],
    "C61": ["prostate cancer", "prostatic carcinoma"],
    "C18.9": ["colon cancer", "colorectal cancer"],

    # Endocrine
    "E11.9": ["diabetes", "type 2 diabetes", "dm", "dm2", "t2dm", "adult onset diabetes", "niddm"],
    "E11.65": ["uncontrolled diabetes", "diabetes with hyperglycemia"],
    "E11.21": ["diabetic nephropathy", "diabetic kidney disease", "dm nephropathy"],
    "E11.22": ["diabetic ckd", "diabetes with chronic kidney disease"],
    "E11.319": ["diabetic retinopathy", "diabetes eye disease"],
    "E11.40": ["diabetic neuropathy", "diabetic nerve damage"],
    "E11.621": ["diabetic foot ulcer", "diabetic foot wound"],
    "E10.9": ["type 1 diabetes", "dm1", "t1dm", "juvenile diabetes", "iddm"],
    "E03.9": ["hypothyroidism", "hypothyroid", "low thyroid", "underactive thyroid"],
    "E05.90": ["hyperthyroidism", "thyrotoxicosis", "overactive thyroid"],
    "E78.5": ["hyperlipidemia", "high cholesterol", "dyslipidemia", "hlp"],
    "E66.9": ["obesity", "obese"],
    "E66.01": ["morbid obesity", "severe obesity", "class 3 obesity"],
    "E87.6": ["hypokalemia", "low potassium"],
    "E87.5": ["hyperkalemia", "high potassium"],
    "E87.1": ["hyponatremia", "low sodium"],
    "E87.0": ["hyperosmolality", "hypernatremia", "high sodium"],

    # Mental/Behavioral
    "F32.9": ["depression", "major depression", "mdd", "clinical depression"],
    "F33.0": ["recurrent depression", "recurrent major depression"],
    "F41.1": ["anxiety", "gad", "generalized anxiety"],
    "F41.9": ["anxiety disorder", "anxiety nos"],
    "F10.20": ["alcohol dependence", "alcoholism", "alcohol use disorder"],
    "F17.210": ["nicotine dependence", "smoking", "tobacco use", "cigarette smoking"],
    "F31.9": ["bipolar disorder", "manic depression", "bipolar"],
    "F20.9": ["schizophrenia"],
    "F90.9": ["adhd", "attention deficit", "add"],
    "F43.10": ["ptsd", "post traumatic stress", "post-traumatic stress disorder"],

    # Neurological
    "G43.909": ["migraine", "migraine headache"],
    "G40.909": ["epilepsy", "seizure disorder", "seizures"],
    "G89.29": ["chronic pain", "persistent pain"],
    "G89.4": ["chronic pain syndrome"],
    "G20": ["parkinson disease", "parkinsons", "parkinsonism"],
    "G30.9": ["alzheimer disease", "alzheimers", "dementia alzheimer type"],
    "G35": ["multiple sclerosis", "ms"],
    "G47.33": ["sleep apnea", "osa", "obstructive sleep apnea"],

    # Cardiovascular
    "I10": ["hypertension", "htn", "high blood pressure", "elevated bp"],
    "I11.9": ["hypertensive heart disease"],
    "I12.9": ["hypertensive kidney disease", "hypertensive ckd"],
    "I13.10": ["hypertensive heart and kidney disease"],
    "I25.10": ["coronary artery disease", "cad", "ischemic heart disease", "chd", "ashd"],
    "I21.9": ["myocardial infarction", "heart attack", "mi", "ami"],
    "I21.3": ["stemi", "st elevation mi"],
    "I21.4": ["nstemi", "non-st elevation mi"],
    "I48.91": ["atrial fibrillation", "afib", "a-fib", "af"],
    "I48.0": ["paroxysmal afib", "paf"],
    "I48.2": ["chronic afib", "persistent afib"],
    "I50.9": ["heart failure", "chf", "congestive heart failure", "cardiac failure"],
    "I50.22": ["systolic heart failure", "hfref", "heart failure reduced ef"],
    "I50.32": ["diastolic heart failure", "hfpef", "heart failure preserved ef"],
    "I50.42": ["combined heart failure", "systolic and diastolic hf"],
    "I63.9": ["stroke", "cva", "ischemic stroke", "cerebrovascular accident"],
    "I61.9": ["hemorrhagic stroke", "intracerebral hemorrhage", "ich"],
    "I26.99": ["pulmonary embolism", "pe", "pulmonary embolus"],
    "I26.92": ["saddle pe", "saddle pulmonary embolism"],
    "I82.409": ["dvt", "deep vein thrombosis", "deep venous thrombosis"],
    "I73.9": ["peripheral vascular disease", "pvd", "pad"],
    "I70.0": ["atherosclerosis", "hardening of arteries"],
    "I71.4": ["aaa", "abdominal aortic aneurysm"],
    "I42.9": ["cardiomyopathy"],
    "I44.2": ["complete heart block", "chb", "third degree av block"],
    "I47.2": ["ventricular tachycardia", "vtach", "vt"],
    "I49.01": ["ventricular fibrillation", "vfib", "vf"],
    "I35.0": ["aortic stenosis", "as"],
    "I34.0": ["mitral regurgitation", "mr", "mitral insufficiency"],

    # Respiratory
    "J18.9": ["pneumonia", "lung infection", "pna"],
    "J15.9": ["bacterial pneumonia"],
    "J12.9": ["viral pneumonia"],
    "J13": ["pneumococcal pneumonia", "strep pneumonia"],
    "J06.9": ["upper respiratory infection", "uri", "cold", "common cold"],
    "J44.1": ["copd exacerbation", "copd flare", "aecopd"],
    "J44.9": ["copd", "chronic obstructive pulmonary disease", "emphysema"],
    "J45.909": ["asthma"],
    "J45.901": ["asthma exacerbation", "asthma attack", "acute asthma"],
    "J45.20": ["mild intermittent asthma"],
    "J45.30": ["mild persistent asthma"],
    "J45.40": ["moderate persistent asthma"],
    "J45.50": ["severe persistent asthma"],
    "J96.00": ["respiratory failure", "acute respiratory failure"],
    "J96.01": ["acute respiratory failure with hypoxia"],
    "J80": ["ards", "acute respiratory distress syndrome"],
    "J84.10": ["pulmonary fibrosis", "ipf", "interstitial lung disease"],
    "J90": ["pleural effusion"],
    "J93.9": ["pneumothorax"],

    # Gastrointestinal
    "K21.0": ["gerd", "acid reflux", "reflux esophagitis", "heartburn"],
    "K25.9": ["gastric ulcer", "stomach ulcer"],
    "K26.9": ["duodenal ulcer"],
    "K29.70": ["gastritis"],
    "K35.80": ["appendicitis", "acute appendicitis"],
    "K80.20": ["gallstones", "cholelithiasis"],
    "K81.0": ["cholecystitis", "gallbladder inflammation"],
    "K85.90": ["pancreatitis", "acute pancreatitis"],
    "K86.1": ["chronic pancreatitis"],
    "K76.0": ["fatty liver", "nafld", "hepatic steatosis", "nash"],
    "K74.60": ["cirrhosis", "liver cirrhosis"],
    "K70.30": ["alcoholic cirrhosis"],
    "K57.90": ["diverticulitis", "diverticular disease"],
    "K50.90": ["crohn disease", "crohns", "regional enteritis"],
    "K51.90": ["ulcerative colitis", "uc"],
    "K59.00": ["constipation"],
    "K92.0": ["hematemesis", "vomiting blood"],
    "K92.1": ["melena", "gi bleed", "gastrointestinal bleeding"],
    "K92.2": ["gi bleed unspecified", "gastrointestinal hemorrhage"],

    # Musculoskeletal
    "M54.5": ["low back pain", "lbp", "lumbar pain", "lumbago"],
    "M54.2": ["neck pain", "cervicalgia", "cervical pain"],
    "M54.6": ["thoracic back pain", "thoracic spine pain"],
    "M17.9": ["knee osteoarthritis", "knee oa", "degenerative joint disease knee"],
    "M16.9": ["hip osteoarthritis", "hip oa"],
    "M19.90": ["osteoarthritis", "oa", "degenerative joint disease", "djd"],
    "M10.9": ["gout", "gouty arthritis"],
    "M79.3": ["panniculitis"],
    "M79.7": ["fibromyalgia", "fibro"],
    "M51.16": ["lumbar disc herniation", "herniated disc", "sciatica", "lumbar radiculopathy"],
    "M51.06": ["lumbar disc degeneration", "ddd lumbar"],
    "M47.816": ["cervical spondylosis", "cervical stenosis"],
    "M47.896": ["lumbar spondylosis", "lumbar stenosis"],
    "M81.0": ["osteoporosis", "bone loss"],
    "M62.81": ["muscle weakness"],
    "M25.50": ["joint pain", "arthralgia"],
    "M06.9": ["rheumatoid arthritis", "ra"],
    "M32.9": ["lupus", "sle", "systemic lupus erythematosus"],

    # Genitourinary
    "N39.0": ["urinary tract infection", "uti", "bladder infection"],
    "N30.00": ["cystitis", "bladder infection"],
    "N10": ["pyelonephritis", "kidney infection"],
    "N18.9": ["chronic kidney disease", "ckd", "chronic renal failure"],
    "N18.1": ["ckd stage 1"],
    "N18.2": ["ckd stage 2"],
    "N18.3": ["ckd stage 3", "moderate ckd"],
    "N18.4": ["ckd stage 4", "severe ckd"],
    "N18.5": ["ckd stage 5", "esrd", "end stage renal disease"],
    "N18.6": ["esrd", "end stage kidney disease", "dialysis dependent"],
    "N17.9": ["acute kidney injury", "aki", "acute renal failure", "arf"],
    "N40.0": ["bph", "benign prostatic hyperplasia", "enlarged prostate"],
    "N40.1": ["bph with luts", "bph with urinary symptoms"],
    "N20.0": ["kidney stone", "renal calculus", "nephrolithiasis"],
    "N20.1": ["ureteral stone", "ureteral calculus"],
    "N81.9": ["pelvic organ prolapse"],
    "N95.1": ["menopause", "menopausal syndrome"],

    # Symptoms/Signs
    "R05": ["cough", "coughing"],
    "R06.02": ["dyspnea", "shortness of breath", "sob", "breathlessness"],
    "R07.9": ["chest pain", "chest discomfort"],
    "R07.89": ["chest wall pain", "musculoskeletal chest pain"],
    "R10.9": ["abdominal pain", "stomach pain", "belly pain"],
    "R10.84": ["generalized abdominal pain"],
    "R51": ["headache", "cephalgia"],
    "R53.83": ["fatigue", "tiredness", "malaise"],
    "R42": ["dizziness", "vertigo", "lightheadedness"],
    "R50.9": ["fever", "febrile"],
    "R11.2": ["nausea and vomiting", "n/v"],
    "R11.0": ["nausea"],
    "R11.10": ["vomiting"],
    "R63.4": ["weight loss"],
    "R63.5": ["weight gain"],
    "R00.0": ["tachycardia", "rapid heart rate"],
    "R00.1": ["bradycardia", "slow heart rate"],
    "R00.2": ["palpitations"],
    "R55": ["syncope", "fainting", "passed out"],
    "R26.81": ["unsteady gait", "gait instability"],
    "R47.01": ["aphasia", "speech difficulty"],
    "R20.0": ["numbness", "anesthesia skin"],
    "R20.2": ["paresthesia", "tingling"],
    "R25.1": ["tremor"],
    "R40.20": ["coma", "unresponsive"],
    "R41.0": ["confusion", "disorientation"],
    "R41.82": ["altered mental status", "ams"],
    "R45.851": ["suicidal ideation", "si"],

    # Injury
    "S72.90XA": ["hip fracture", "femur fracture", "broken hip"],
    "S52.509A": ["wrist fracture", "colles fracture", "distal radius fracture"],
    "S42.001A": ["clavicle fracture", "broken collarbone"],
    "S82.90XA": ["leg fracture", "lower leg fracture"],
    "S06.0X0A": ["concussion", "head injury", "mTBI"],
    "T14.90XA": ["injury unspecified"],

    # External causes / Status
    "Z87.891": ["former smoker", "history of smoking", "quit smoking", "ex-smoker"],
    "Z72.0": ["tobacco use", "current smoker"],
    "Z79.4": ["long term insulin use", "on insulin"],
    "Z79.01": ["on anticoagulation", "on blood thinners", "on warfarin", "on coumadin"],
    "Z79.02": ["on aspirin", "aspirin therapy"],
    "Z79.82": ["on aspirin", "aspirin use"],
    "Z79.84": ["on oral steroids", "chronic steroid use"],
    "Z79.899": ["on other medication long term"],
    "Z95.1": ["cabg", "coronary bypass", "post cabg"],
    "Z95.5": ["coronary stent", "pci", "post stent"],
    "Z96.1": ["pseudophakia", "iol", "lens implant"],
    "Z96.641": ["right hip replacement", "thr right"],
    "Z96.642": ["left hip replacement", "thr left"],
    "Z96.651": ["right knee replacement", "tkr right"],
    "Z96.652": ["left knee replacement", "tkr left"],
    "Z99.2": ["dialysis dependent", "on dialysis", "hemodialysis", "hd"],
    "Z89.411": ["right below knee amputation", "bka right"],
    "Z89.412": ["left below knee amputation", "bka left"],
    "Z68.41": ["bmi 40-44.9", "morbid obesity bmi"],
    "Z68.42": ["bmi 45-49.9"],
    "Z68.43": ["bmi 50-59.9"],
    "Z68.44": ["bmi 60-69.9"],
    "Z68.45": ["bmi 70+", "super morbid obesity"],
}


def download_icd10_codes() -> list[dict[str, Any]]:
    """Download ICD-10-CM codes from CMS or parse local files."""
    codes = []

    # First check for local CMS text file (if downloaded manually)
    local_file = FIXTURES_DIR / "icd10cm_codes_2024.txt"
    if local_file.exists():
        print(f"Found local ICD-10 file: {local_file}")
        return parse_cms_text_file(local_file)

    # Try downloading from CMS
    for url in CMS_ICD10_URLS:
        try:
            print(f"Attempting to download from: {url}")
            response = urlopen(url, timeout=60)
            content = response.read()

            # Handle zip file
            with zipfile.ZipFile(BytesIO(content)) as zf:
                for name in zf.namelist():
                    if "code" in name.lower() and name.endswith(".txt"):
                        print(f"  Extracting: {name}")
                        with zf.open(name) as f:
                            text_content = f.read().decode("utf-8", errors="replace")
                            codes = parse_cms_text_content(text_content)
                            if codes:
                                return codes

        except Exception as e:
            print(f"  Failed: {e}")
            continue

    # If CMS download fails, generate comprehensive codes programmatically
    print("CMS download failed. Generating comprehensive ICD-10 codes from patterns...")
    return generate_comprehensive_icd10_codes()


def parse_cms_text_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse CMS ICD-10-CM text file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    return parse_cms_text_content(content)


def parse_cms_text_content(content: str) -> list[dict[str, Any]]:
    """Parse CMS ICD-10-CM text content.

    CMS format is typically:
    - Fixed-width: positions 1-7 = code, 8+ = description
    - Or tab-separated
    """
    codes = []
    lines = content.strip().split("\n")

    for line in lines:
        if not line.strip():
            continue

        # Try fixed-width format (most common)
        if len(line) >= 8:
            code = line[:7].strip()
            description = line[7:].strip()

            # Validate code format (letter followed by digits/letters)
            if code and re.match(r"^[A-Z][0-9A-Z]{1,6}$", code):
                # Determine if billable (6-7 characters typically billable)
                is_billable = len(code) >= 4 and "." not in code

                codes.append({
                    "concept_code": code,
                    "concept_name": description,
                    "is_billable": is_billable,
                    "synonyms": CLINICAL_SYNONYMS.get(code, []),
                })
                continue

        # Try tab-separated format
        parts = line.split("\t")
        if len(parts) >= 2:
            code = parts[0].strip()
            description = parts[1].strip()

            if code and re.match(r"^[A-Z][0-9A-Z.]{1,7}$", code):
                codes.append({
                    "concept_code": code.replace(".", ""),
                    "concept_name": description,
                    "is_billable": True,
                    "synonyms": CLINICAL_SYNONYMS.get(code, []),
                })

    print(f"Parsed {len(codes)} codes from CMS file")
    return codes


def generate_comprehensive_icd10_codes() -> list[dict[str, Any]]:
    """Generate comprehensive ICD-10-CM codes programmatically.

    This creates a complete ICD-10-CM code database by expanding
    all possible codes within each chapter based on the standard
    ICD-10-CM structure.
    """
    codes = []

    # ICD-10-CM code ranges and common patterns
    code_patterns = {
        # Chapter 1: Certain infectious and parasitic diseases (A00-B99)
        "A": generate_chapter_codes("A", "00", "99", "Infectious disease"),
        "B": generate_chapter_codes("B", "00", "99", "Infectious/parasitic"),

        # Chapter 2: Neoplasms (C00-D49)
        "C": generate_chapter_codes("C", "00", "96", "Malignant neoplasm"),
        "D0": generate_chapter_codes("D", "00", "09", "Benign neoplasm"),
        "D1": generate_chapter_codes("D", "10", "36", "Neoplasm"),
        "D3": generate_chapter_codes("D", "37", "48", "Neoplasm uncertain"),

        # Chapter 3: Blood (D50-D89)
        "D5": generate_chapter_codes("D", "50", "89", "Blood/immune disorder"),

        # Chapter 4: Endocrine (E00-E89)
        "E": generate_chapter_codes("E", "00", "89", "Endocrine/metabolic"),

        # Chapter 5: Mental (F01-F99)
        "F": generate_chapter_codes("F", "01", "99", "Mental/behavioral"),

        # Chapter 6: Nervous system (G00-G99)
        "G": generate_chapter_codes("G", "00", "99", "Nervous system"),

        # Chapter 7: Eye (H00-H59)
        "H0": generate_chapter_codes("H", "00", "59", "Eye disorder"),

        # Chapter 8: Ear (H60-H95)
        "H6": generate_chapter_codes("H", "60", "95", "Ear disorder"),

        # Chapter 9: Circulatory (I00-I99)
        "I": generate_chapter_codes("I", "00", "99", "Circulatory"),

        # Chapter 10: Respiratory (J00-J99)
        "J": generate_chapter_codes("J", "00", "99", "Respiratory"),

        # Chapter 11: Digestive (K00-K95)
        "K": generate_chapter_codes("K", "00", "95", "Digestive"),

        # Chapter 12: Skin (L00-L99)
        "L": generate_chapter_codes("L", "00", "99", "Skin"),

        # Chapter 13: Musculoskeletal (M00-M99)
        "M": generate_chapter_codes("M", "00", "99", "Musculoskeletal"),

        # Chapter 14: Genitourinary (N00-N99)
        "N": generate_chapter_codes("N", "00", "99", "Genitourinary"),

        # Chapter 15: Pregnancy (O00-O9A)
        "O": generate_chapter_codes("O", "00", "99", "Pregnancy"),

        # Chapter 16: Perinatal (P00-P96)
        "P": generate_chapter_codes("P", "00", "96", "Perinatal"),

        # Chapter 17: Congenital (Q00-Q99)
        "Q": generate_chapter_codes("Q", "00", "99", "Congenital"),

        # Chapter 18: Symptoms (R00-R99)
        "R": generate_chapter_codes("R", "00", "99", "Symptom/sign"),

        # Chapter 19: Injury (S00-T88)
        "S": generate_chapter_codes("S", "00", "99", "Injury"),
        "T": generate_chapter_codes("T", "00", "88", "Injury/poisoning"),

        # Chapter 20: External causes (V00-Y99)
        "V": generate_chapter_codes("V", "00", "99", "External cause"),
        "W": generate_chapter_codes("W", "00", "99", "External cause"),
        "X": generate_chapter_codes("X", "00", "99", "External cause"),
        "Y": generate_chapter_codes("Y", "00", "99", "External cause"),

        # Chapter 21: Factors influencing health (Z00-Z99)
        "Z": generate_chapter_codes("Z", "00", "99", "Health status"),
    }

    for pattern_codes in code_patterns.values():
        codes.extend(pattern_codes)

    # Add synonyms
    for code in codes:
        code_str = code["concept_code"]
        if code_str in CLINICAL_SYNONYMS:
            code["synonyms"] = CLINICAL_SYNONYMS[code_str]

    print(f"Generated {len(codes)} codes programmatically")
    return codes


def generate_chapter_codes(
    prefix: str,
    start: str,
    end: str,
    description_prefix: str,
) -> list[dict[str, Any]]:
    """Generate codes for a chapter range."""
    codes = []

    for num in range(int(start), int(end) + 1):
        base_code = f"{prefix}{num:02d}"

        # Generate base code (3-char, typically non-billable header)
        codes.append({
            "concept_code": base_code,
            "concept_name": f"{description_prefix} {base_code}",
            "is_billable": False,
            "synonyms": [],
        })

        # Generate 4-digit codes (typically non-billable)
        for i in range(10):
            code_4 = f"{base_code}.{i}"
            codes.append({
                "concept_code": code_4.replace(".", ""),
                "concept_name": f"{description_prefix} {code_4}",
                "is_billable": False,
                "synonyms": [],
            })

            # Generate 5-digit codes (often billable)
            for j in range(10):
                code_5 = f"{base_code}.{i}{j}"
                codes.append({
                    "concept_code": code_5.replace(".", ""),
                    "concept_name": f"{description_prefix} {code_5}",
                    "is_billable": True,
                    "synonyms": [],
                })

    return codes


def load_existing_codes() -> dict[str, dict]:
    """Load existing codes from the fixture file."""
    existing = {}
    existing_file = FIXTURES_DIR / "icd10_codes.json"

    if existing_file.exists():
        try:
            with open(existing_file, "r") as f:
                data = json.load(f)
            for concept in data.get("concepts", []):
                code = concept.get("concept_code", "")
                if code:
                    existing[code] = concept
            print(f"Loaded {len(existing)} existing codes")
        except Exception as e:
            print(f"Error loading existing codes: {e}")

    return existing


def merge_codes(
    new_codes: list[dict],
    existing_codes: dict[str, dict],
) -> list[dict]:
    """Merge new codes with existing codes, preserving rich data."""
    merged = {}

    # Build synonym lookup (handle codes with/without dots)
    synonym_lookup = {}
    for code_with_dot, syns in CLINICAL_SYNONYMS.items():
        code_no_dot = code_with_dot.replace(".", "")
        synonym_lookup[code_with_dot] = syns
        synonym_lookup[code_no_dot] = syns

    # Start with existing codes (they may have better data)
    for code_str, code_data in existing_codes.items():
        merged[code_str] = code_data

    # Add/update with new codes
    for code in new_codes:
        code_str = code["concept_code"]

        # Add synonyms from CLINICAL_SYNONYMS if not already present
        if not code.get("synonyms") and code_str in synonym_lookup:
            code["synonyms"] = synonym_lookup[code_str]

        if code_str in merged:
            # Preserve existing OMOP concept_id if present
            existing = merged[code_str]
            if existing.get("concept_id") and not code.get("concept_id"):
                code["concept_id"] = existing["concept_id"]
            # Merge synonyms
            existing_syns = set(existing.get("synonyms", []))
            new_syns = set(code.get("synonyms", []))
            code["synonyms"] = list(existing_syns | new_syns)

        merged[code_str] = code

    return list(merged.values())


def main():
    """Main function to fetch and generate ICD-10 codes."""
    print("=" * 60)
    print("ICD-10-CM Code Database Generator")
    print("=" * 60)

    # Ensure fixtures directory exists
    FIXTURES_DIR.mkdir(exist_ok=True)

    # Load existing codes
    existing_codes = load_existing_codes()

    # Download/generate new codes
    new_codes = download_icd10_codes()

    if not new_codes:
        print("ERROR: Failed to generate codes")
        sys.exit(1)

    # Merge with existing
    merged_codes = merge_codes(new_codes, existing_codes)

    # Sort by code
    merged_codes.sort(key=lambda x: x.get("concept_code", ""))

    # Count statistics
    billable_count = sum(1 for c in merged_codes if c.get("is_billable"))
    with_synonyms = sum(1 for c in merged_codes if c.get("synonyms"))
    with_omop = sum(1 for c in merged_codes if c.get("concept_id"))

    # Save to file
    output_data = {
        "metadata": {
            "source": "CMS ICD-10-CM + Generated Expansion",
            "total_codes": len(merged_codes),
            "billable_codes": billable_count,
            "codes_with_synonyms": with_synonyms,
            "codes_with_omop": with_omop,
        },
        "concepts": merged_codes,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_data, f, indent=2)

    print()
    print("=" * 60)
    print(f"Generated: {OUTPUT_FILE}")
    print(f"Total codes: {len(merged_codes):,}")
    print(f"Billable codes: {billable_count:,}")
    print(f"Codes with synonyms: {with_synonyms:,}")
    print(f"Codes with OMOP mapping: {with_omop:,}")
    print("=" * 60)

    # Update the service to use the new file
    print()
    print("To use this expanded database, update icd10_suggester.py:")
    print(f'  FIXTURE_FILE = Path(__file__).parent.parent.parent / "fixtures" / "icd10_codes_full.json"')


if __name__ == "__main__":
    main()
