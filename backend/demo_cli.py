#!/usr/bin/env python3
"""
Clinical Ontology Normalizer - Interactive Demo CLI

A comprehensive visualization tool for testing clinical note analysis.
Paste a clinical note and see the full analysis pipeline in action.

Usage:
    python demo_cli.py                    # Interactive mode
    python demo_cli.py --file note.txt    # Analyze file
    python demo_cli.py --sample           # Use sample note
"""

import argparse
import sys
import time
import importlib.util
from pathlib import Path
from uuid import uuid4

# ============================================================================
# Module Loading (bypass __init__.py dependency chain)
# ============================================================================

def load_module(name: str, path: str):
    """Load a module directly from file path."""
    full_path = Path(__file__).parent / path
    spec = importlib.util.spec_from_file_location(name, full_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Load core modules
base_module = load_module('app.schemas.base', 'app/schemas/base.py')
nlp_module = load_module('app.services.nlp', 'app/services/nlp.py')
nlp_advanced_module = load_module('app.services.nlp_advanced', 'app/services/nlp_advanced.py')

# Import what we need
Assertion = base_module.Assertion
Domain = base_module.Domain
Temporality = base_module.Temporality
Experiencer = base_module.Experiencer
ExtractedMention = nlp_module.ExtractedMention
AdvancedNLPService = nlp_advanced_module.AdvancedNLPService
Laterality = nlp_advanced_module.Laterality

# ============================================================================
# Sample Clinical Note
# ============================================================================

SAMPLE_NOTE = """
HISTORY OF PRESENT ILLNESS:
64-year-old male with known HFrEF (EF ~25%), CKD stage 4, HTN, DM2, CAD s/p CABG,
and atrial fibrillation on anticoagulation presents with 3 days of worsening dyspnea
and bilateral lower extremity edema. Reports orthopnea and paroxysmal nocturnal dyspnea.
Notes 8-10 lb weight gain over 1 week. States he ran out of furosemide 5 days ago.

Denies chest pain. Denies fever or chills. Denies productive cough; has mild dry cough.
Denies hemoptysis. No recent travel. No history of DVT/PE. No unilateral leg swelling.

MEDICATIONS:
- Furosemide 40 mg PO BID (ran out 5 days ago)
- Carvedilol 12.5 mg PO BID
- Lisinopril 10 mg PO daily
- Apixaban 5 mg PO BID
- Metformin 1000 mg PO BID
- Atorvastatin 40 mg PO nightly

PHYSICAL EXAM:
General: Alert, in mild respiratory distress.
Neck: JVP elevated.
Lungs: Bilateral crackles to mid-lung fields. No wheezing.
Extremities: 2+ pitting edema to knees bilaterally. No calf tenderness.

ASSESSMENT:
1) Acute decompensated heart failure (HFrEF) with pulmonary edema
2) Acute kidney injury on chronic kidney disease (cardiorenal syndrome)
3) Hyperkalemia, mild-moderate (K 5.6)
4) Hypertension, severe on arrival
5) Atrial fibrillation with RVR
6) Type 2 diabetes mellitus with hyperglycemia

PE ruled out given low clinical suspicion and clear volume overload picture.
"""

# ============================================================================
# Display Functions
# ============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GRAY = '\033[90m'

def print_header(text: str, char: str = "="):
    """Print a formatted header."""
    width = 80
    print()
    print(f"{Colors.BOLD}{Colors.CYAN}{char * width}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{char * width}{Colors.END}")

def print_subheader(text: str):
    """Print a formatted subheader."""
    print()
    print(f"{Colors.BOLD}{Colors.YELLOW}{'─' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{'─' * 80}{Colors.END}")

def print_item(label: str, value: str, indent: int = 2):
    """Print a labeled item."""
    spaces = " " * indent
    print(f"{spaces}{Colors.GRAY}{label}:{Colors.END} {value}")

def print_success(text: str):
    """Print success message."""
    print(f"  {Colors.GREEN}✓{Colors.END} {text}")

def print_warning(text: str):
    """Print warning message."""
    print(f"  {Colors.YELLOW}!{Colors.END} {text}")

def print_error(text: str):
    """Print error/negated message."""
    print(f"  {Colors.RED}✗{Colors.END} {text}")

# ============================================================================
# Simple Rule-Based Mention Extractor
# ============================================================================

# Clinical terms to look for
CLINICAL_TERMS = {
    # Conditions
    "HFrEF": Domain.CONDITION,
    "HFpEF": Domain.CONDITION,
    "heart failure": Domain.CONDITION,
    "CKD": Domain.CONDITION,
    "chronic kidney disease": Domain.CONDITION,
    "HTN": Domain.CONDITION,
    "hypertension": Domain.CONDITION,
    "DM2": Domain.CONDITION,
    "DM": Domain.CONDITION,
    "diabetes": Domain.CONDITION,
    "diabetes mellitus": Domain.CONDITION,
    "CAD": Domain.CONDITION,
    "coronary artery disease": Domain.CONDITION,
    "atrial fibrillation": Domain.CONDITION,
    "dyspnea": Domain.CONDITION,
    "edema": Domain.CONDITION,
    "lower extremity edema": Domain.CONDITION,
    "orthopnea": Domain.CONDITION,
    "chest pain": Domain.CONDITION,
    "fever": Domain.CONDITION,
    "chills": Domain.CONDITION,
    "cough": Domain.CONDITION,
    "productive cough": Domain.CONDITION,
    "hemoptysis": Domain.CONDITION,
    "DVT": Domain.CONDITION,
    "PE": Domain.CONDITION,
    "pulmonary embolism": Domain.CONDITION,
    "leg swelling": Domain.CONDITION,
    "crackles": Domain.CONDITION,
    "wheezing": Domain.CONDITION,
    "pitting edema": Domain.CONDITION,
    "calf tenderness": Domain.CONDITION,
    "pulmonary edema": Domain.CONDITION,
    "acute kidney injury": Domain.CONDITION,
    "AKI": Domain.CONDITION,
    "cardiorenal syndrome": Domain.CONDITION,
    "hyperkalemia": Domain.CONDITION,
    "hyperglycemia": Domain.CONDITION,
    "RVR": Domain.CONDITION,
    "JVP elevated": Domain.CONDITION,
    "respiratory distress": Domain.CONDITION,
    "CABG": Domain.PROCEDURE,

    # Medications
    "furosemide": Domain.DRUG,
    "carvedilol": Domain.DRUG,
    "lisinopril": Domain.DRUG,
    "apixaban": Domain.DRUG,
    "metformin": Domain.DRUG,
    "atorvastatin": Domain.DRUG,

    # Measurements
    "EF": Domain.MEASUREMENT,
    "ejection fraction": Domain.MEASUREMENT,
    "K 5.6": Domain.MEASUREMENT,
    "weight gain": Domain.MEASUREMENT,
}

def extract_mentions_simple(text: str) -> list[ExtractedMention]:
    """Simple rule-based mention extraction."""
    mentions = []
    text_lower = text.lower()

    for term, domain in CLINICAL_TERMS.items():
        term_lower = term.lower()
        start = 0
        while True:
            idx = text_lower.find(term_lower, start)
            if idx == -1:
                break

            # Get the actual text (preserve case)
            actual_text = text[idx:idx + len(term)]

            mention = ExtractedMention(
                text=actual_text,
                start_offset=idx,
                end_offset=idx + len(term),
                lexical_variant=term_lower,
                domain_hint=domain.value,
                assertion=Assertion.PRESENT,
                temporality=Temporality.CURRENT,
                experiencer=Experiencer.PATIENT,
                confidence=0.85,
            )
            mentions.append(mention)
            start = idx + len(term)

    # Sort by position and deduplicate overlapping spans
    mentions.sort(key=lambda m: (m.start_offset, -len(m.text)))

    # Remove overlapping mentions (keep longer ones)
    filtered = []
    last_end = -1
    for m in mentions:
        if m.start_offset >= last_end:
            filtered.append(m)
            last_end = m.end_offset

    return filtered

# ============================================================================
# Analysis Functions
# ============================================================================

def analyze_note(text: str) -> dict:
    """Run full analysis pipeline on clinical note."""
    results = {
        "mentions": [],
        "enhanced": [],
        "stats": {},
        "timing": {},
    }

    # Step 1: Extract mentions
    start = time.perf_counter()
    mentions = extract_mentions_simple(text)
    results["timing"]["extraction_ms"] = (time.perf_counter() - start) * 1000
    results["mentions"] = mentions

    # Step 2: Enhance with advanced NLP
    start = time.perf_counter()
    service = AdvancedNLPService()
    enhanced = service.enhance_mentions(text, mentions)
    results["timing"]["enhancement_ms"] = (time.perf_counter() - start) * 1000
    results["enhanced"] = enhanced

    # Step 3: Calculate statistics
    results["stats"] = {
        "total_mentions": len(mentions),
        "conditions": len([m for m in mentions if m.domain_hint == Domain.CONDITION.value]),
        "drugs": len([m for m in mentions if m.domain_hint == Domain.DRUG.value]),
        "measurements": len([m for m in mentions if m.domain_hint == Domain.MEASUREMENT.value]),
        "procedures": len([m for m in mentions if m.domain_hint == Domain.PROCEDURE.value]),
        "negated": len([e for e in enhanced if e.mention.assertion == Assertion.ABSENT]),
        "with_laterality": len([e for e in enhanced if e.enhancement.laterality]),
        "with_compound": len([e for e in enhanced if e.enhancement.compound_condition_text]),
        "disambiguated": len([e for e in enhanced if e.enhancement.disambiguated_term]),
    }

    return results

def display_results(results: dict):
    """Display analysis results in formatted output."""
    enhanced = results["enhanced"]
    stats = results["stats"]
    timing = results["timing"]

    # Summary Statistics
    print_subheader("SUMMARY STATISTICS")
    total_time = timing["extraction_ms"] + timing["enhancement_ms"]
    print(f"""
  {Colors.BOLD}Processing Time:{Colors.END}
    Extraction:  {timing['extraction_ms']:.2f} ms
    Enhancement: {timing['enhancement_ms']:.2f} ms
    Total:       {total_time:.2f} ms

  {Colors.BOLD}Mentions Found:{Colors.END}
    Total:        {stats['total_mentions']}
    Conditions:   {stats['conditions']}
    Medications:  {stats['drugs']}
    Measurements: {stats['measurements']}
    Procedures:   {stats['procedures']}

  {Colors.BOLD}Enhancements:{Colors.END}
    Negated:           {stats['negated']}
    With Laterality:   {stats['with_laterality']}
    Compound:          {stats['with_compound']}
    Disambiguated:     {stats['disambiguated']}
""")

    # Abbreviation Disambiguation
    disambiguated = [e for e in enhanced if e.enhancement.disambiguated_term]
    if disambiguated:
        print_subheader("ABBREVIATION DISAMBIGUATION")
        for em in disambiguated:
            ctx = em.enhancement.disambiguation_context
            ctx_str = f" [{ctx.value}]" if ctx else ""
            print(f"  {Colors.CYAN}{em.mention.text:15s}{Colors.END} → {em.enhancement.disambiguated_term}{ctx_str}")

    # Negated Findings
    negated = [e for e in enhanced if e.mention.assertion == Assertion.ABSENT]
    if negated:
        print_subheader("NEGATED FINDINGS (ABSENT)")
        for em in negated:
            trigger = em.enhancement.negation_trigger or "?"
            print_error(f"{em.mention.text:30s} (trigger: '{trigger}')")

    # Present Conditions
    present_conditions = [e for e in enhanced
                         if e.mention.assertion == Assertion.PRESENT
                         and e.mention.domain_hint == Domain.CONDITION.value]
    if present_conditions:
        print_subheader("PRESENT CONDITIONS")
        for em in present_conditions:
            extras = []
            if em.enhancement.laterality:
                extras.append(f"{Colors.BLUE}{em.enhancement.laterality.value}{Colors.END}")
            if em.enhancement.linked_modifier:
                extras.append(f"{Colors.GREEN}{em.enhancement.linked_modifier}{Colors.END}")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            print_success(f"{em.mention.text}{extra_str}")

    # Medications
    medications = [e for e in enhanced if e.mention.domain_hint == Domain.DRUG.value]
    if medications:
        print_subheader("MEDICATIONS IDENTIFIED")
        for em in medications:
            print(f"  {Colors.GREEN}●{Colors.END} {em.mention.text}")

    # Compound Conditions
    compounds = [e for e in enhanced if e.enhancement.compound_condition_text]
    if compounds:
        print_subheader("COMPOUND CONDITIONS")
        for em in compounds:
            print(f"  {em.mention.text:25s} → {Colors.CYAN}{em.enhancement.compound_condition_text}{Colors.END}")

    # Laterality
    lateralized = [e for e in enhanced if e.enhancement.laterality]
    if lateralized:
        print_subheader("LATERALITY DETECTED")
        for em in lateralized:
            lat = em.enhancement.laterality
            lat_text = em.enhancement.laterality_text
            color = Colors.BLUE if lat == Laterality.BILATERAL else Colors.YELLOW
            print(f"  {em.mention.text:30s} → {color}{lat.value}{Colors.END} ({lat_text})")

# ============================================================================
# ASCII Architecture Diagram
# ============================================================================

def print_architecture():
    """Print ASCII architecture diagram."""
    diagram = """
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     CLINICAL ONTOLOGY NORMALIZER - SYSTEM ARCHITECTURE            │
└──────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React/Next.js)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Documents  │  │  Patients   │  │   Search    │  │      Dashboards         │ │
│  │  & Mentions │  │  & Graphs   │  │   & Q&A     │  │ Provider|Biller|Quality │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │ REST API
┌───────────────────────────────────────▼─────────────────────────────────────────┐
│                              FASTAPI BACKEND                                     │
│                                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                         API LAYER (27+ Endpoints)                          │ │
│  │  /documents  /search  /dashboard  /export  /fhir  /patients  /jobs         │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│  ┌─────────────────────────────────────┴──────────────────────────────────────┐ │
│  │                        SERVICE LAYER (45+ Services)                        │ │
│  │                                                                            │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐ │ │
│  │  │    NLP PIPELINE     │  │  CLINICAL DECISION  │  │  BILLING & CODING  │ │ │
│  │  │  ┌───────────────┐  │  │      SUPPORT        │  │                    │ │ │
│  │  │  │ Rule-Based    │  │  │  ┌───────────────┐  │  │  ┌──────────────┐  │ │ │
│  │  │  │ Clinical NER  │  │  │  │ Differential  │  │  │  │ ICD-10       │  │ │ │
│  │  │  │ Ensemble      │──┼──│  │ Diagnosis     │  │  │  │ Suggester    │  │ │ │
│  │  │  │ Advanced NLP  │  │  │  │               │  │  │  │ (with CER)   │  │ │ │
│  │  │  │ - Abbreviation│  │  │  │ Calculators   │  │  │  ├──────────────┤  │ │ │
│  │  │  │ - Negation    │  │  │  │ - BMI, CHADS₂ │  │  │  │ CPT          │  │ │ │
│  │  │  │ - Laterality  │  │  │  │ - TIMI, Wells │  │  │  │ Suggester    │  │ │ │
│  │  │  │ - Compound    │  │  │  │               │  │  │  │ (with RVU)   │  │ │ │
│  │  │  └───────────────┘  │  │  │ Drug Safety   │  │  │  ├──────────────┤  │ │ │
│  │  │                     │  │  │ - Interactions│  │  │  │ HCC Analyzer │  │ │ │
│  │  │  ┌───────────────┐  │  │  │ - Pregnancy   │  │  │  │ (RAF values) │  │ │ │
│  │  │  │ Relation      │  │  │  │ - Black Box   │  │  │  ├──────────────┤  │ │ │
│  │  │  │ Extraction    │  │  │  │               │  │  │  │ Billing      │  │ │ │
│  │  │  │               │  │  │  │ Lab Reference │  │  │  │ Optimizer    │  │ │ │
│  │  │  │ Value         │  │  │  │ - Ranges      │  │  │  ├──────────────┤  │ │ │
│  │  │  │ Extraction    │  │  │  │ - Abnormality │  │  │  │ CDI Query    │  │ │ │
│  │  │  └───────────────┘  │  │  └───────────────┘  │  │  │ Generator    │  │ │ │
│  │  └─────────────────────┘  └─────────────────────┘  │  └──────────────┘  │ │ │
│  │                                                     └────────────────────┘ │ │
│  │  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐ │ │
│  │  │ KNOWLEDGE MGMT      │  │ ANALYTICS/REPORTS   │  │ EXPORT/INTEGRATION │ │ │
│  │  │                     │  │                     │  │                    │ │ │
│  │  │ • OMOP Vocabulary   │  │ • Clinical Summary  │  │ • FHIR R4 Export   │ │ │
│  │  │ • Semantic Search   │  │ • Report Generator  │  │ • FHIR Import      │ │ │
│  │  │ • Hybrid Search     │  │ • Semantic Q&A      │  │ • OMOP CDM Export  │ │ │
│  │  │ • Concept Mapping   │  │ • Quality Metrics   │  │ • Fact Builder     │ │ │
│  │  │ • Embeddings        │  │ • Batch Processor   │  │ • Graph Builder    │ │ │
│  │  └─────────────────────┘  └─────────────────────┘  └────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│  ┌─────────────────────────────────────┴──────────────────────────────────────┐ │
│  │                           DATA LAYER                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │  PostgreSQL  │  │    Redis     │  │  Vocabulary  │  │   Embeddings   │  │ │
│  │  │  (Documents, │  │  (Job Queue) │  │  (74MB OMOP) │  │  (Vector Store)│  │ │
│  │  │   Mentions,  │  │              │  │              │  │                │  │ │
│  │  │   Facts)     │  │              │  │              │  │                │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN PATTERNS                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  • CER Framework: All recommendations include Claim-Evidence-Reasoning          │
│  • Singleton Services: Vocabulary, embeddings cached for performance            │
│  • Multi-Stage Pipeline: Pre-process → Extract → Context → Validate             │
│  • Role-Based Views: Provider | Biller | Quality | Admin dashboards             │
│  • Confidence Scoring: All outputs include confidence levels                    │
│  • Revenue Impact: Billing recommendations include $ estimates                  │
└─────────────────────────────────────────────────────────────────────────────────┘
"""
    print(diagram)

# ============================================================================
# Interactive Mode
# ============================================================================

def interactive_mode():
    """Run interactive demo mode."""
    print_header("CLINICAL ONTOLOGY NORMALIZER - INTERACTIVE DEMO")
    print("""
  This tool analyzes clinical notes using advanced NLP processing.

  {bold}Commands:{end}
    paste     - Enter multi-line note (end with blank line)
    sample    - Use the sample clinical note
    arch      - Show system architecture diagram
    help      - Show this help
    quit      - Exit

""".format(bold=Colors.BOLD, end=Colors.END))

    while True:
        try:
            cmd = input(f"{Colors.BOLD}demo>{Colors.END} ").strip().lower()

            if cmd in ('quit', 'exit', 'q'):
                print("\nGoodbye!")
                break

            elif cmd == 'help':
                print("""
  Commands:
    paste   - Enter a clinical note (paste multi-line, end with blank line)
    sample  - Analyze the built-in sample note
    arch    - Display ASCII system architecture
    help    - Show this help message
    quit    - Exit the demo
""")

            elif cmd == 'arch':
                print_architecture()

            elif cmd == 'sample':
                print_header("ANALYZING SAMPLE CLINICAL NOTE")
                print(f"\n{Colors.GRAY}{'─' * 80}{Colors.END}")
                print(SAMPLE_NOTE[:500] + "..." if len(SAMPLE_NOTE) > 500 else SAMPLE_NOTE)
                print(f"{Colors.GRAY}{'─' * 80}{Colors.END}")

                results = analyze_note(SAMPLE_NOTE)
                display_results(results)

            elif cmd == 'paste':
                print("  Paste your clinical note below (press Enter twice to finish):")
                print(f"  {Colors.GRAY}{'─' * 60}{Colors.END}")

                lines = []
                empty_count = 0
                while True:
                    line = input()
                    if line == "":
                        empty_count += 1
                        if empty_count >= 2:
                            break
                        lines.append(line)
                    else:
                        empty_count = 0
                        lines.append(line)

                note = "\n".join(lines).strip()
                if note:
                    print_header("ANALYZING YOUR CLINICAL NOTE")
                    results = analyze_note(note)
                    display_results(results)
                else:
                    print("  No note provided.")

            elif cmd:
                print(f"  Unknown command: {cmd}. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Clinical Ontology Normalizer - Interactive Demo CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo_cli.py                  # Interactive mode
  python demo_cli.py --sample         # Analyze sample note
  python demo_cli.py --file note.txt  # Analyze file
  python demo_cli.py --arch           # Show architecture
"""
    )
    parser.add_argument('--file', '-f', help='Path to clinical note file')
    parser.add_argument('--sample', '-s', action='store_true', help='Use sample clinical note')
    parser.add_argument('--arch', '-a', action='store_true', help='Show architecture diagram')

    args = parser.parse_args()

    if args.arch:
        print_architecture()
    elif args.sample:
        print_header("ANALYZING SAMPLE CLINICAL NOTE")
        results = analyze_note(SAMPLE_NOTE)
        display_results(results)
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)

        note = path.read_text()
        print_header(f"ANALYZING: {path.name}")
        results = analyze_note(note)
        display_results(results)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
