import os
import json
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from docx_helpers import (
    set_cell_background,
    set_cell_margins,
    set_cell_border_left_accent,
    set_table_borders,
    set_box_borders,
    add_callout_box,
    add_expert_adjudication_form
)

# Load data
with open("detailed_non_positive_snippets.json", "r") as f:
    patient_data = json.load(f)

doc = docx.Document()

# Page Setup: 1 inch margins
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)
    
    # Header
    header = section.header
    p_head = header.paragraphs[0]
    p_head.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_head = p_head.add_run("PHENOAGENT CLINICAL EXPERT REVIEW DOSSIER | NON-POSITIVE COHORT")
    r_head.font.name = "Calibri"
    r_head.font.size = Pt(8.5)
    r_head.font.color.rgb = RGBColor(113, 128, 150)
    
    # Footer
    footer = section.footer
    p_foot = footer.paragraphs[0]
    p_foot.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r_foot1 = p_foot.add_run("CONFIDENTIAL — FOR CLINICAL EXPERT ADJUDICATION ONLY")
    r_foot1.font.name = "Calibri"
    r_foot1.font.size = Pt(8.5)
    r_foot1.font.color.rgb = RGBColor(113, 128, 150)

# Colors
COLOR_NAVY = RGBColor(26, 54, 93)      # #1A365D
COLOR_SLATE = RGBColor(43, 108, 176)    # #2B6CB0
COLOR_BODY = RGBColor(45, 55, 72)      # #2D3748
COLOR_MUTED = RGBColor(113, 128, 150)   # #718096

# ==========================================
# TITLE & COVER SECTION
# ==========================================
p_title = doc.add_paragraph()
p_title.paragraph_format.space_before = Pt(12)
p_title.paragraph_format.space_after = Pt(2)
run_title = p_title.add_run("Clinical Expert Review Dossier: Non-Positive Cohort Adjudication")
run_title.font.name = "Calibri"
run_title.font.size = Pt(22)
run_title.font.bold = True
run_title.font.color.rgb = COLOR_NAVY

p_sub = doc.add_paragraph()
p_sub.paragraph_format.space_before = Pt(0)
p_sub.paragraph_format.space_after = Pt(12)
run_sub = p_sub.add_run("EHR Evidence, Clinical Decision Chains, and Adjudication Protocols for 17 Non-Positive Stuttering Phenotype Cases")
run_sub.font.name = "Calibri"
run_sub.font.size = Pt(12)
run_sub.font.color.rgb = COLOR_SLATE

# Metadata Table
meta_tbl = doc.add_table(rows=4, cols=2)
meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
meta_tbl.autofit = False
set_table_borders(meta_tbl, color="CBD5E0", sz="6")

meta_fields = [
    ("Target Phenotype", "Developmental & Persistent Stuttering (ICD-9 307.0 / ICD-10 F80.81)"),
    ("Cohort Scope", "1,132 Total EHR Patients | 1,115 Positive (98.50%) | 17 Non-Positive (1.50%)"),
    ("Review Set Composition", "17 Cases: 6 Excluded (Family History Only) + 11 Negative (Rule-Out / Competing / No Signal)"),
    ("Evaluation Objective", "Expert Clinical Validation & Consensus Adjudication of AI Pipeline Classifications")
]

for row_idx, (label, val) in enumerate(meta_fields):
    c0 = meta_tbl.cell(row_idx, 0)
    c1 = meta_tbl.cell(row_idx, 1)
    c0.width = Inches(2.2)
    c1.width = Inches(4.3)
    set_cell_background(c0, "F7FAFC")
    set_cell_background(c1, "FFFFFF")
    set_cell_margins(c0, top=60, bottom=60, left=100, right=100)
    set_cell_margins(c1, top=60, bottom=60, left=100, right=100)
    
    p0 = c0.paragraphs[0]
    p0.paragraph_format.space_after = Pt(0)
    r0 = p0.add_run(label)
    r0.bold = True
    r0.font.name = "Calibri"
    r0.font.size = Pt(9.5)
    r0.font.color.rgb = COLOR_NAVY
    
    p1 = c1.paragraphs[0]
    p1.paragraph_format.space_after = Pt(0)
    r1 = p1.add_run(val)
    r1.font.name = "Calibri"
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = COLOR_BODY

doc.add_paragraph().paragraph_format.space_after = Pt(8)

# ==========================================
# INSTRUCTIONS FOR CLINICAL REVIEWERS
# ==========================================
p_inst_h = doc.add_paragraph()
p_inst_h.paragraph_format.space_before = Pt(8)
p_inst_h.paragraph_format.space_after = Pt(4)
r_ih = p_inst_h.add_run("1. Instructions for Clinical Expert Reviewers")
r_ih.bold = True
r_ih.font.name = "Calibri"
r_ih.font.size = Pt(14)
r_ih.font.color.rgb = COLOR_NAVY

p_inst = doc.add_paragraph()
p_inst.paragraph_format.space_before = Pt(2)
p_inst.paragraph_format.space_after = Pt(6)
r_inst = p_inst.add_run(
    "This dossier contains the longitudinal clinical evidence and reasoning chains for the 17 non-positive patients "
    "identified across the 1,132-patient stuttering phenotyping cohort. In typical automated phenotyping workflows, "
    "these cases are frequently misclassified as false positives due to keyword over-matching (e.g., family history mentions, "
    "administrative SLP billing codes, or non-fluency motor-speech disorders like dysarthria). "
    "Please review each patient's extracted evidence, verify the clinical decision path, and complete the adjudication sign-off form."
)
r_inst.font.name = "Calibri"
r_inst.font.size = Pt(10)
r_inst.font.color.rgb = COLOR_BODY

# Phenotype Definitions Table
def_tbl = doc.add_table(rows=5, cols=2)
def_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
def_tbl.autofit = False
set_table_borders(def_tbl, color="CBD5E0", sz="6")

def_rows = [
    ("Classification", "Clinical Definition & PhenoAgent Criteria"),
    ("Positive", "Documented speech-language pathology (CCC-SLP) diagnosis of developmental or persistent stuttering, standardized fluency score (SSI-3, SSI-4, %SS, OASES), or confirmed ongoing fluency therapy."),
    ("Excluded (Family History)", "Stuttering keywords are explicitly attributed to a biological relative (e.g., parent, sibling, cousin) with verified absence of personal patient-level fluency impairment across longitudinal EHR."),
    ("Negative", "Explicit clinical rule-out (<3% disfluency), diagnosis of competing motor-speech condition (e.g. spastic dysarthria), administrative SLP/audiology billing without stuttering, or complete absence of stuttering signal."),
    ("Indeterminate", "Unresolved conflicting evidence, ambiguous clinic notes, or incomplete clinical records that preclude a definitive positive, negative, or excluded classification.")
]

for row_idx, (col0, col1) in enumerate(def_rows):
    c0 = def_tbl.cell(row_idx, 0)
    c1 = def_tbl.cell(row_idx, 1)
    c0.width = Inches(2.0)
    c1.width = Inches(4.5)
    set_cell_margins(c0, top=70, bottom=70, left=100, right=100)
    set_cell_margins(c1, top=70, bottom=70, left=100, right=100)
    
    if row_idx == 0:
        set_cell_background(c0, "1A365D")
        set_cell_background(c1, "1A365D")
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(col0)
        r0.bold = True
        r0.font.name = "Calibri"
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = RGBColor(255, 255, 255)
        
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(col1)
        r1.bold = True
        r1.font.name = "Calibri"
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGBColor(255, 255, 255)
    else:
        bg = "F7FAFC" if row_idx % 2 == 1 else "FFFFFF"
        set_cell_background(c0, bg)
        set_cell_background(c1, bg)
        
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(col0)
        r0.bold = True
        r0.font.name = "Calibri"
        r0.font.size = Pt(9)
        r0.font.color.rgb = COLOR_NAVY
        
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(col1)
        r1.font.name = "Calibri"
        r1.font.size = Pt(9)
        r1.font.color.rgb = COLOR_BODY

doc.add_paragraph().paragraph_format.space_after = Pt(12)

# ==========================================
# MASTER SUMMARY TABLE OF 17 PATIENTS
# ==========================================
p_sum_h = doc.add_paragraph()
p_sum_h.paragraph_format.space_before = Pt(8)
p_sum_h.paragraph_format.space_after = Pt(4)
r_sh = p_sum_h.add_run("2. Cohort Master Roster of Non-Positive Cases (N=17)")
r_sh.bold = True
r_sh.font.name = "Calibri"
r_sh.font.size = Pt(14)
r_sh.font.color.rgb = COLOR_NAVY

summary_tbl = doc.add_table(rows=18, cols=7)
summary_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
summary_tbl.autofit = False
set_table_borders(summary_tbl, color="CBD5E0", sz="6")

headers = ["#", "Patient GRID", "Classification", "Conf", "Notes", "Year Span", "Clinical Mechanism / Rationale"]
col_widths = [Inches(0.35), Inches(1.1), Inches(1.15), Inches(0.55), Inches(0.6), Inches(1.0), Inches(1.8)]

for col_idx, h in enumerate(headers):
    c = summary_tbl.cell(0, col_idx)
    c.width = col_widths[col_idx]
    set_cell_background(c, "1A365D")
    set_cell_margins(c, top=60, bottom=60, left=60, right=60)
    p = c.paragraphs[0]
    r = p.add_run(h)
    r.bold = True
    r.font.name = "Calibri"
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(255, 255, 255)

# Patient list ordered logically
roster = [
    # 6 Excluded
    ("R249876813", "Excluded", 0.85, 151, "2000 – 2023", "Family history only; relative had 4 yrs SLP therapy; patient fluent"),
    ("R212618220", "Excluded", 0.85, 84, "2000 – 2023", "Father stuttered as child; patient confirmed fluent in exam"),
    ("R257016144", "Excluded", 0.85, 95, "1998 – 2019", "Mother stutters; communication barrier for mom; zero patient symptoms"),
    ("R272837566", "Excluded", 0.85, 76, "2008 – 2020", "Mother had stuttering tic as child; no patient-level disfluency"),
    ("R275078358", "Excluded", 0.85, 11, "2017 – 2018", "Cousin diagnosed with stuttering; patient speech fluent"),
    ("R290040058", "Excluded", 0.85, 472, "1999 – 2025", "Mother stutters; multiple maternal notes over 26 years; patient fluent"),
    # 11 Negative
    ("R250115464", "Negative", 0.80, 1, "2007", "Formal rule-out; maternal denial; <3% disfluencies (normal limits)"),
    ("R293758494", "Negative", 0.80, 13, "2004 – 2011", "Competing motor condition: spastic dysarthria (ICD-9 784.5)"),
    ("R243641111", "Negative", 0.80, 19, "2007 – 2020", "General speech eval order (CPT 92506) linked to audiology workup"),
    ("R284656655", "Negative", 0.80, 11, "2005 – 2011", "General speech delay order (CPT 92506, DX 315.39); zero stuttering"),
    ("R260516492", "Negative", 0.80, 11, "2002 – 2009", "General speech delay order (DX 315.39); no fluency impairment"),
    ("R260607966", "Negative", 0.80, 2, "2010", "General SLP evaluation order without stuttering symptoms"),
    ("R252590287", "Negative", 0.80, 12, "2009 – 2024", "Administrative DX 307.0 billing order without clinical stuttering"),
    ("R212870908", "Negative", 0.80, 5, "2004 – 2009", "Audiology/SLP scheduling & CPT codes (92567/92582) without stuttering"),
    ("R291752631", "Negative", 0.80, 13, "1992 – 2023", "Administrative SLP order across 3 decades; zero patient symptoms"),
    ("R210758594", "Negative", 0.80, 14, "2008 – 2014", "True absence of signal; zero stuttering keywords in clinical context"),
    ("R216716673", "Negative", 0.80, 3, "2018 – 2024", "Administrative regex hit; zero clinical stuttering evidence across EHR")
]

for idx, (grid, dx, conf, notes, yrs, mech) in enumerate(roster, 1):
    row_cells = summary_tbl.rows[idx].cells
    bg = "FAF5FF" if dx == "Excluded" else ("F7FAFC" if idx % 2 == 1 else "FFFFFF")
    
    row_vals = [str(idx), grid, dx, f"{conf:.2f}", str(notes), yrs, mech]
    for c_idx, val in enumerate(row_vals):
        c = row_cells[c_idx]
        c.width = col_widths[c_idx]
        set_cell_background(c, bg)
        set_cell_margins(c, top=50, bottom=50, left=50, right=50)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(val)
        r.font.name = "Calibri"
        r.font.size = Pt(8.5)
        if c_idx == 1:
            r.bold = True
            r.font.color.rgb = COLOR_NAVY
        elif c_idx == 2:
            r.bold = True
            r.font.color.rgb = RGBColor(128, 90, 213) if dx == "Excluded" else RGBColor(197, 48, 48)
        else:
            r.font.color.rgb = COLOR_BODY

doc.add_page_break()

# ==========================================
# SECTION 1: EXCLUDED PATIENTS (FAMILY HISTORY ONLY)
# ==========================================
p_sec1_h = doc.add_paragraph()
p_sec1_h.paragraph_format.space_before = Pt(8)
p_sec1_h.paragraph_format.space_after = Pt(4)
r_s1 = p_sec1_h.add_run("3. Excluded Patients: Family History Only (N=6)")
r_s1.bold = True
r_s1.font.name = "Calibri"
r_s1.font.size = Pt(16)
r_s1.font.color.rgb = COLOR_NAVY

p_sec1_desc = doc.add_paragraph()
p_sec1_desc.paragraph_format.space_after = Pt(10)
r_s1d = p_sec1_desc.add_run(
    "Rule Definition: The patient is classified as EXCLUDED when stuttering, stammering, or speech disfluency "
    "keywords occur in the record but are explicitly and exclusively attributed to a biological family member "
    "(parent, sibling, cousin, uncle), with no documented patient-level stuttering symptoms or interventions across the longitudinal record. "
    "In naive keyword phenotyping, 100% of these cases would erroneously be called Positive."
)
r_s1d.font.name = "Calibri"
r_s1d.font.size = Pt(10)
r_s1d.font.color.rgb = COLOR_BODY

excluded_grids = ["R249876813", "R212618220", "R257016144", "R272837566", "R275078358", "R290040058"]

for p_num, grid in enumerate(excluded_grids, 1):
    p_info = patient_data.get(grid, {})
    
    # Patient Banner
    ban_tbl = doc.add_table(rows=1, cols=4)
    ban_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    ban_tbl.autofit = False
    set_table_borders(ban_tbl, color="CBD5E0", sz="8")
    
    b_widths = [Inches(2.0), Inches(1.5), Inches(1.5), Inches(1.5)]
    b_vals = [
        (f"Case {p_num}: {grid}", True, COLOR_NAVY),
        (f"Call: EXCLUDED", True, RGBColor(107, 70, 193)),
        (f"Confidence: {p_info.get('confidence', 0.85):.2f}", False, COLOR_BODY),
        (f"{p_info.get('total_notes', 0)} Notes | {p_info.get('year_span', '')}", False, COLOR_BODY)
    ]
    for b_idx, (b_text, is_bold, b_color) in enumerate(b_vals):
        bc = ban_tbl.cell(0, b_idx)
        bc.width = b_widths[b_idx]
        set_cell_background(bc, "FAF5FF")
        set_cell_margins(bc, top=70, bottom=70, left=80, right=80)
        bp = bc.paragraphs[0]
        bp.paragraph_format.space_after = Pt(0)
        br = bp.add_run(b_text)
        br.bold = is_bold
        br.font.name = "Calibri"
        br.font.size = Pt(9.5)
        br.font.color.rgb = b_color
        
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    
    # Clinical Rationale
    p_rat = doc.add_paragraph()
    p_rat.paragraph_format.space_before = Pt(2)
    p_rat.paragraph_format.space_after = Pt(4)
    r_rl = p_rat.add_run("Clinical Decision Rationale: ")
    r_rl.bold = True
    r_rl.font.name = "Calibri"
    r_rl.font.size = Pt(10)
    r_rl.font.color.rgb = COLOR_NAVY
    
    clean_reason = p_info.get("reasoning", "").replace("**", "")
    r_rt = p_rat.add_run(clean_reason)
    r_rt.font.name = "Calibri"
    r_rt.font.size = Pt(9.5)
    r_rt.font.color.rgb = COLOR_BODY
    
    # Pre-screen trigger explanation
    p_trig = doc.add_paragraph()
    p_trig.paragraph_format.space_before = Pt(2)
    p_trig.paragraph_format.space_after = Pt(4)
    r_tl = p_trig.add_run("Naive Pre-Screen Trigger: ")
    r_tl.bold = True
    r_tl.font.name = "Calibri"
    r_tl.font.size = Pt(9.5)
    r_tl.font.color.rgb = RGBColor(197, 48, 48)
    
    r_tt = p_trig.add_run("Matched keyword 'stutter*' in EHR clinical text. Heuristic pre-screener assigned Positive without performing grammatical entity attribution.")
    r_tt.font.name = "Calibri"
    r_tt.font.size = Pt(9.5)
    r_tt.font.color.rgb = COLOR_BODY
    
    # Callout Box of Evidence
    ev_list = p_info.get("evidence", [])
    if not ev_list:
        ev_list = ["No affirmative patient-level stuttering quotes identified in record."]
    add_callout_box(doc, ev_list, title=f"Verbatim EHR Quotes & Evidence Mentions ({grid})", bg_hex="FAF5FF", accent_hex="805AD5")
    
    # Adjudication Box
    add_expert_adjudication_form(doc, grid, "Excluded (Family History Only)")
    
    if p_num < len(excluded_grids):
        doc.add_paragraph().paragraph_format.space_after = Pt(10)

doc.add_page_break()

# ==========================================
# SECTION 2: NEGATIVE PATIENTS (N=11)
# ==========================================
p_sec2_h = doc.add_paragraph()
p_sec2_h.paragraph_format.space_before = Pt(8)
p_sec2_h.paragraph_format.space_after = Pt(4)
r_s2 = p_sec2_h.add_run("4. Negative Patients: Rule-Outs, Competing Conditions, & Administrative Hits (N=11)")
r_s2.bold = True
r_s2.font.name = "Calibri"
r_s2.font.size = Pt(16)
r_s2.font.color.rgb = COLOR_NAVY

p_sec2_desc = doc.add_paragraph()
p_sec2_desc.paragraph_format.space_after = Pt(10)
r_s2d = p_sec2_desc.add_run(
    "Rule Definition: The patient is classified as NEGATIVE when there is an explicit clinical rule-out (<3% disfluency), "
    "a non-fluency competing motor-speech condition (e.g., dysarthria), an administrative general speech evaluation or billing code "
    "without stuttering, or complete absence of speech disfluency signal across the longitudinal EHR."
)
r_s2d.font.name = "Calibri"
r_s2d.font.size = Pt(10)
r_s2d.font.color.rgb = COLOR_BODY

negative_groups = [
    ("4.1 Formal Clinical Rule-Out & Negation", [
        ("R250115464", "Maternal denial of concern + formal SLP evaluation showing <3% disfluencies (within normal limits, typical non-fluency). Uncle stuttered.")
    ]),
    ("4.2 Competing Motor-Speech Condition (Dysarthria)", [
        ("R293758494", "Patient explicitly diagnosed with spastic dysarthria (ICD-9 784.5). Speech therapy ordered for motor dysarthria, not a fluency disorder.")
    ]),
    ("4.3 Administrative SLP Evaluation Orders & Billing Without Fluency Disorder", [
        ("R243641111", "General speech-language evaluation order (CPT 92506, DX 315.39) linked to audiology/hearing workup. Zero stuttering symptoms."),
        ("R284656655", "General speech disorder evaluation order (CPT 92506, DX 315.39 'Other specified disorders of speech'). Zero stuttering documentation."),
        ("R260516492", "Order for speech evaluation and treatment with DX 315.39 ('Other speech disorders'). No stuttering or disfluency keywords."),
        ("R260607966", "Order to schedule speech and language evaluation with CCC-SLP. Zero clinical stuttering symptoms across 2 notes."),
        ("R252590287", "Administrative DX 307.0 billing and S/L evaluation scheduling without clinical description of stuttering or standardized testing."),
        ("R212870908", "Administrative scheduling notes and CPT billing codes (92567, 92582) with CCC-SLP. Zero stuttering symptoms across 5 notes."),
        ("R291752631", "Administrative referral for 'S/L/fluency eval' with CCC-SLP across 3 decades. Zero clinical documentation of stuttering symptoms.")
    ]),
    ("4.4 Complete Absence of Clinical Signal Across Longitudinal Record", [
        ("R210758594", "Zero stuttering, stammering, or speech disfluency keywords appear anywhere in patient's clinical EHR across 14 notes (2008–2014)."),
        ("R216716673", "Pre-screen regex hit administrative token, but clinical synthesis confirmed zero patient stuttering statements or SLP diagnoses.")
    ])
]

neg_counter = 1
for grp_title, patient_tuples in negative_groups:
    p_gh = doc.add_paragraph()
    p_gh.paragraph_format.space_before = Pt(10)
    p_gh.paragraph_format.space_after = Pt(4)
    r_gh = p_gh.add_run(grp_title)
    r_gh.bold = True
    r_gh.font.name = "Calibri"
    r_gh.font.size = Pt(12)
    r_gh.font.color.rgb = COLOR_SLATE
    
    for grid, short_mech in patient_tuples:
        p_info = patient_data.get(grid, {})
        
        # Patient Banner
        ban_tbl = doc.add_table(rows=1, cols=4)
        ban_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        ban_tbl.autofit = False
        set_table_borders(ban_tbl, color="CBD5E0", sz="8")
        
        b_widths = [Inches(2.0), Inches(1.5), Inches(1.5), Inches(1.5)]
        b_vals = [
            (f"Case {neg_counter}: {grid}", True, COLOR_NAVY),
            (f"Call: NEGATIVE", True, RGBColor(197, 48, 48)),
            (f"Confidence: {p_info.get('confidence', 0.80):.2f}", False, COLOR_BODY),
            (f"{p_info.get('total_notes', 0)} Notes | {p_info.get('year_span', '')}", False, COLOR_BODY)
        ]
        for b_idx, (b_text, is_bold, b_color) in enumerate(b_vals):
            bc = ban_tbl.cell(0, b_idx)
            bc.width = b_widths[b_idx]
            set_cell_background(bc, "FFF5F5")
            set_cell_margins(bc, top=70, bottom=70, left=80, right=80)
            bp = bc.paragraphs[0]
            bp.paragraph_format.space_after = Pt(0)
            br = bp.add_run(b_text)
            br.bold = is_bold
            br.font.name = "Calibri"
            br.font.size = Pt(9.5)
            br.font.color.rgb = b_color
            
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        
        # Clinical Rationale
        p_rat = doc.add_paragraph()
        p_rat.paragraph_format.space_before = Pt(2)
        p_rat.paragraph_format.space_after = Pt(4)
        r_rl = p_rat.add_run("Clinical Decision Rationale: ")
        r_rl.bold = True
        r_rl.font.name = "Calibri"
        r_rl.font.size = Pt(10)
        r_rl.font.color.rgb = COLOR_NAVY
        
        clean_reason = p_info.get("reasoning", "").replace("**", "")
        r_rt = p_rat.add_run(clean_reason)
        r_rt.font.name = "Calibri"
        r_rt.font.size = Pt(9.5)
        r_rt.font.color.rgb = COLOR_BODY
        
        # Pre-screen trigger explanation
        p_trig = doc.add_paragraph()
        p_trig.paragraph_format.space_before = Pt(2)
        p_trig.paragraph_format.space_after = Pt(4)
        r_tl = p_trig.add_run("Naive Pre-Screen Trigger: ")
        r_tl.bold = True
        r_tl.font.name = "Calibri"
        r_tl.font.size = Pt(9.5)
        r_tl.font.color.rgb = RGBColor(197, 48, 48)
        
        r_tt = p_trig.add_run(f"Initially flagged by pre-screener due to: {short_mech}")
        r_tt.font.name = "Calibri"
        r_tt.font.size = Pt(9.5)
        r_tt.font.color.rgb = COLOR_BODY
        
        # Callout Box of Evidence
        ev_list = p_info.get("evidence", [])
        if not ev_list:
            ev_list = ["No affirmative patient-level stuttering symptoms or standardized test scores found in record."]
        add_callout_box(doc, ev_list, title=f"Verbatim EHR Quotes & Evidence Mentions ({grid})", bg_hex="F7FAFC", accent_hex="3182CE")
        
        # Adjudication Box
        add_expert_adjudication_form(doc, grid, "Negative")
        
        neg_counter += 1
        doc.add_paragraph().paragraph_format.space_after = Pt(10)

doc.add_page_break()

# ==========================================
# SECTION 3: REVIEWER CONSENSUS & SIGN-OFF
# ==========================================
p_sec3_h = doc.add_paragraph()
p_sec3_h.paragraph_format.space_before = Pt(8)
p_sec3_h.paragraph_format.space_after = Pt(4)
r_s3 = p_sec3_h.add_run("5. Expert Reviewer Consensus & Final Sign-Off Sheet")
r_s3.bold = True
r_s3.font.name = "Calibri"
r_s3.font.size = Pt(16)
r_s3.font.color.rgb = COLOR_NAVY

p_sec3_desc = doc.add_paragraph()
p_sec3_desc.paragraph_format.space_after = Pt(8)
r_s3d = p_sec3_desc.add_run(
    "Please record your overall review summary and final sign-off below after completing the case-by-case adjudication."
)
r_s3d.font.name = "Calibri"
r_s3d.font.size = Pt(10)

sign_tbl = doc.add_table(rows=6, cols=2)
sign_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
sign_tbl.autofit = False
set_table_borders(sign_tbl, color="CBD5E0", sz="6")

sign_fields = [
    ("Lead Expert Reviewer Name", "________________________________________________"),
    ("Professional Title & Credentials", "________________________________________________ (e.g. CCC-SLP, MD, PhD)"),
    ("Review Completion Date", "________________________________________________"),
    ("Total Cases Reviewed", "17 of 17 Non-Positive Cases"),
    ("Concordance Summary", "____ Cases Agreed (____ %)  |  ____ Cases Overturned (____ %)"),
    ("Reviewer Signature", "________________________________________________")
]

for row_idx, (f_label, f_val) in enumerate(sign_fields):
    c0 = sign_tbl.cell(row_idx, 0)
    c1 = sign_tbl.cell(row_idx, 1)
    c0.width = Inches(2.5)
    c1.width = Inches(4.0)
    set_cell_background(c0, "F7FAFC")
    set_cell_background(c1, "FFFFFF")
    set_cell_margins(c0, top=80, bottom=80, left=100, right=100)
    set_cell_margins(c1, top=80, bottom=80, left=100, right=100)
    
    p0 = c0.paragraphs[0]
    p0.paragraph_format.space_after = Pt(0)
    r0 = p0.add_run(f_label)
    r0.bold = True
    r0.font.name = "Calibri"
    r0.font.size = Pt(9.5)
    r0.font.color.rgb = COLOR_NAVY
    
    p1 = c1.paragraphs[0]
    p1.paragraph_format.space_after = Pt(0)
    r1 = p1.add_run(f_val)
    r1.font.name = "Calibri"
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = COLOR_BODY

doc.add_paragraph().paragraph_format.space_after = Pt(12)

# Save files
os.makedirs("results/stuttering_parallel/summary", exist_ok=True)
out_path_summary = "results/stuttering_parallel/summary/Non_Positive_Patients_Expert_Review_Dossier.docx"
out_path_root = "Non_Positive_Patients_Expert_Review_Dossier.docx"

doc.save(out_path_summary)
doc.save(out_path_root)

print(f"Successfully generated and saved Word Document to:\n  1. {out_path_summary}\n  2. {out_path_root}")
