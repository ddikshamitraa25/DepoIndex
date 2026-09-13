from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

ROOT = Path(__file__).resolve().parents[1]
SLIDES_DIR = ROOT / "slides"
SLIDES_DIR.mkdir(parents=True, exist_ok=True)

prs = Presentation()
# 16:9 widescreen slides
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Styling palette (Professional Legal Tech Navy & Warm Amber)
NAVY = RGBColor(26, 38, 57)
AMBER = RGBColor(190, 115, 45)
SLATE = RGBColor(90, 100, 115)
LIGHT_BG = RGBColor(248, 249, 250)
WHITE = RGBColor(255, 255, 255)
DARK_TEXT = RGBColor(30, 30, 30)
GREEN = RGBColor(40, 130, 80)

def add_header(slide, title_text: str, subtitle_text: str = ""):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.1))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = NAVY
    if subtitle_text:
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.size = Pt(14)
        p2.font.color.rgb = SLATE
        p2.space_before = Pt(4)

def add_card(slide, left, top, width, height, title: str, bullets: list[str]):
    shape = slide.shapes.add_shape(1, left, top, width, height) # 1 = MSO_SHAPE.RECTANGLE
    shape.fill.solid()
    shape.fill.fore_color.rgb = WHITE
    shape.line.color.rgb = RGBColor(215, 220, 228)
    shape.line.width = Pt(1)
    
    tb = slide.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), height - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = AMBER
    p.space_after = Pt(8)
    
    for b in bullets:
        p = tf.add_paragraph()
        p.text = "• " + b
        p.font.size = Pt(12)
        p.font.color.rgb = DARK_TEXT
        p.space_after = Pt(6)

# SLIDE 1: Title & Executive Summary
slide_layout = prs.slide_layouts[6] # Blank
slide1 = prs.slides.add_slide(slide_layout)

title_box = slide1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(4.5))
tf1 = title_box.text_frame
tf1.word_wrap = True
p = tf1.paragraphs[0]
p.text = "DepoIndex"
p.font.size = Pt(44)
p.font.bold = True
p.font.color.rgb = NAVY

p2 = tf1.add_paragraph()
p2.text = "AI-Powered Deposition Topic Index with Deterministic Provenance"
p2.font.size = Pt(22)
p2.font.color.rgb = AMBER
p2.space_before = Pt(8)

p3 = tf1.add_paragraph()
p3.text = "Target: Persis Yu Deposition (Heather Turrey v. Vervent, Inc.) | Problem #3 Implementation"
p3.font.size = Pt(14)
p3.font.color.rgb = SLATE
p3.space_before = Pt(16)

p4 = tf1.add_paragraph()
p4.text = (
    "Core Mission: Deliver a provenance-first legal indexing system where every generated topic is deterministically "
    "grounded in verified page/line transcript coordinates. The LLM or semantic layer is never permitted to invent citations. "
    "Proven through 100% reproducible execution across 122 pages, 2,042 testimony lines, and 29 chronological topics."
)
p4.font.size = Pt(13)
p4.font.color.rgb = DARK_TEXT
p4.space_before = Pt(24)

# SLIDE 2: Architecture & Provenance Strategy
slide2 = prs.slides.add_slide(slide_layout)
add_header(slide2, "System Architecture & Deterministic Provenance", "Extracting canonical transcript truth without probabilistic hallucinations")

add_card(slide2, Inches(0.8), Inches(1.8), Inches(3.6), Inches(5.0), "1. Coordinate Extraction", [
    "PyMuPDF word bounding boxes extract visual text columns.",
    "Geometric rule: Q & A speaker cues occur strictly at x0=145.5 pt.",
    "Eliminates false-speaker bugs where words like 'A couple' were misclassified as witness answers.",
    "Extracts 122 total pages, identifying 82 testimony pages (P7:L1 to P88:L17) and 2,042 testimony lines."
])

add_card(slide2, Inches(4.8), Inches(1.8), Inches(3.6), Inches(5.0), "2. Immutable Provenance IDs", [
    "Every extracted transcript line receives an immutable source ID: P<page>:L<line>.",
    "Topic records maintain exact start/end page and line plus complete list of enclosed source_ids.",
    "Deterministic ProvenanceValidator verifies line existence, start <= end ordering, and evidence quotes.",
    "Zero invented references: citations come from transcript coordinates, never LLM text outputs."
])

add_card(slide2, Inches(8.8), Inches(1.8), Inches(3.6), Inches(5.0), "3. Chunking & Segmentation", [
    "Testimony is segmented into conversational Turns and grouped into QAUnits (question, answers, colloquy).",
    "Procedural tags detect objections, recesses, and reporter announcements.",
    "Chunks are assigned immutable IDs (C001, C002) and bounded to target character windows.",
    "Attorney UI links each topic directly to underlying verified transcript lines."
])

# SLIDE 3: Topic Segmentation & Real Output Examples
slide3 = prs.slides.add_slide(slide_layout)
add_header(slide3, "Topic Segmentation & Recurrence Strategy", "Balancing conversational continuity with non-contiguous legal recurrence")

add_card(slide3, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), "Dispersed Recurrence & Digression Policy", [
    "Conversational Digressions: Brief procedural interruptions (breaks at P37:L10, P76:L5) are coalesced into enclosing chunks rather than creating artificial micro-topics.",
    "Recurrence Policy: Key subjects (CFPB Settlement, PEAKS unenforceability) appear at non-contiguous intervals (P61, P82, P86).",
    "Locality Constraints: MAX_PAGES_CONTINUE = 8 prevents runaway topic drift. Intervening testimony forces clean chronological topic boundaries.",
    "Recurrence Handling: Recurrence architecture implemented (recurrence_of, related_topic_ids); no recurrence link was triggered on this deposition."
])

add_card(slide3, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), "Real Generated Output Samples (from 29 topics)", [
    "T001 (P7:L1 - P9:L18): Counsel introduction, perjury admonition, prior depositions.",
    "T002 (P9:L19 - P11:L17): Marking Exhibit 1 (Expert Report), law school & CV.",
    "T005 (P16:L16 - P23:L22): Initiatives directed at student loan servicers.",
    "T010 (P29:L2 - P34:L7): Economic value of ITT diploma, Senate HELP report.",
    "T016 (P44:L18 - P51:L2): Qualifications regarding PEAKS loans, bankruptcy orders.",
    "T023 (P66:L22 - P75:L4): Multistate AG, SEC, and CFPB investigations into PEAKS.",
    "T029 (P86:L10 - P88:L17): Core opinion: loans unenforceable at inception."
])

# SLIDE 4: Empirical Validation & 3-Run Stability Test
slide4 = prs.slides.add_slide(slide_layout)
add_header(slide4, "Empirical Validation & 3-Run Stability Testing", "Real experimental results demonstrating bit-level determinism and coverage")

add_card(slide4, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), "Manual Quality Audit (25 Selected Topics)", [
    "Audit Sample: 25 topics evaluated across early, middle, and concluding testimony.",
    "Location Accuracy: 100.0% (all start/end coordinates match canonical transcript lines).",
    "Topic Relevance: 100.0% (labels accurately capture substantive lines of inquiry).",
    "Boundary Quality: 95.5% (clean alignment with question transitions and exhibit shifts).",
    "Coverage & Zero Gaps: 100% of 2,042 testimony lines mapped without missing spans.",
    "Documented in validation/manual_validation_report.json and .md."
])

add_card(slide4, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), "Three-Run Stability Comparison (runs/run1-3)", [
    "Pipeline executed 3 independent times on the Persis Yu PDF.",
    "Topic Count: 29 in Run 1, 29 in Run 2, 29 in Run 3 (100% Identical).",
    "Boundaries: All 29 start and end coordinates match identically across runs.",
    "SHA-256 Checksums: canonical_transcript.json, chunks.json, completeness_report.json, topic_index.json, and topic_index.md match bit-for-bit.",
    "Proves mathematical determinism of coordinate extraction, vector centroids, and threshold segmentation.",
    "Documented in outputs/stability_report.md."
])

# SLIDE 5: Failure Analysis & Engineering Limitations
slide5 = prs.slides.add_slide(slide_layout)
add_header(slide5, "Failure Analysis & Engineering Limitations", "Real edge cases analyzed, fixes implemented, and production trade-offs")

add_card(slide5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), "Resolved Failure Modes (Real Edge Cases)", [
    "Case 1 (False 'A' Speaker): Regex ^A\\b stripped leading 'A' from sentences like 'A couple questions'. Fixed via PyMuPDF column coordinate filtering (x0=145.5).",
    "Case 2 (Interrupted Fragments): Greedy selection picked '-- talking about?' at P36:L7 after simultaneous speech parenthetical. Fixed with fragment rejection and courtesy stripping.",
    "Case 3 (Semantic Drift Across Spans): Risk of merging distant CFPB passages across 26 pages. Fixed via MAX_PAGES_CONTINUE (8) and RECURRENCE_GAP (4).",
    "Case 4 (Procedural Interruptions): Off-the-record breaks causing topic fragmentation. Fixed with procedural turn coalescing."
])

add_card(slide5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), "Current Limitations & Production Roadmap", [
    "Single-Speaker Monologue Spans: Extended multi-paragraph answers by an expert require finer sub-sentence semantic boundary detection.",
    "External LLM Token Costs: Running large commercial LLMs over 2,000 lines requires chunk batching; fallback deterministic engine ensures zero downtime.",
    "Cross-Deposition Scaling: Expanding from single deposition to multi-witness depositions in complex MDL litigation.",
    "Attorney App: FastAPI + Vanilla JS provides search, filter, and exact source line viewing; future iteration can support deposition video timestamp sync."
])

out_path = SLIDES_DIR / "DepoIndex_Presentation.pptx"
prs.save(str(out_path))
print(f"Saved presentation to {out_path}")
