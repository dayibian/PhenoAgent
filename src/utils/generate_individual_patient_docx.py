import os
import json
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def set_cell_background(cell, fill_hex):
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shd)

def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_cell_border_left_accent(cell, color_hex="2B6CB0", sz="24"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="none"/><w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color_hex}"/><w:bottom w:val="none"/><w:right w:val="none"/></w:tcBorders>')
    tcPr.append(borders)

def set_table_borders(table, color="D2D6DC", sz="4"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'<w:tblBorders {nsdecls("w")}><w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/><w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/><w:left w:val="none"/><w:right w:val="none"/><w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/><w:insideV w:val="none"/></w:tblBorders>')
    tblPr.append(borders)

def set_box_borders(cell, color="CBD5E0", sz="8"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/><w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/><w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/><w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/></w:tcBorders>')
    tcPr.append(borders)

def parse_ehr_notes(ehr_content):
    pattern = r"(###\s*\[\d{4}-\d{2}-\d{2}[^\]]*\][^\n]*)"
    parts = re.split(pattern, ehr_content)
    if len(parts) <= 1:
        pattern = r"(###\s*[^\n]+)"
        parts = re.split(pattern, ehr_content)
    notes = []
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i+1].strip() if i+1 < len(parts) else ""
        date_match = re.search(r"\[(\d{4}-\d{2}-\d{2}[^\]]*)\]", header)
        date_str = date_match.group(1) if date_match else ""
        title = re.sub(r"###\s*(\[[^\]]*\])?", "", header).strip()
        source = ""
        source_match = re.search(r"\*\*Source:\*\*\s*([^\n]+)", body)
        if source_match:
            source = source_match.group(1).strip()
            body = re.sub(r"\*\*Source:\*\*\s*[^\n]+\n*", "", body).strip()
        notes.append({
            "header": header,
            "date": date_str,
            "title": title,
            "source": source,
            "body": body
        })
    return notes

# Load detailed snippets & metadata
with open("detailed_non_positive_snippets.json", "r") as f:
    patient_meta = json.load(f)

ehr_dir = "data/stuttering/ehr_markdown_dataset"
output_dir = "results/stuttering_parallel/expert_review_patients"
os.makedirs(output_dir, exist_ok=True)

COLOR_NAVY = RGBColor(26, 54, 93)      # #1A365D
COLOR_SLATE = RGBColor(43, 108, 176)    # #2B6CB0
COLOR_BODY = RGBColor(45, 55, 72)      # #2D3748
COLOR_MUTED = RGBColor(113, 128, 150)   # #718096

pre_screen_triggers = {
    "R249876813": "Matched keyword 'stutter*' in note text. Pre-screen assigned Positive without checking family history attribution.",
    "R212618220": "Matched keyword 'stutter*' in note text. Pre-screen failed to detect that stuttering was attributed strictly to father.",
    "R257016144": "Matched keyword 'stutter*' in note text. Pre-screen assigned Positive; deep synthesis confirmed mother was the sole stutterer.",
    "R272837566": "Matched keyword 'stutter*' in note text. Pre-screen failed to parse maternal childhood tic context.",
    "R275078358": "Matched keyword 'stutter*' in problem list. Pre-screen assigned Positive; mention was strictly cousin's diagnosis.",
    "R290040058": "Matched keyword 'stutter*' repeatedly in longitudinal records. Pre-screen misclassified maternal communication barrier as patient phenotype.",
    "R250115464": "Matched keyword 'stutter*' in formal evaluation text. Pre-screen missed maternal denial and formal <3% disfluency rule-out.",
    "R293758494": "Matched 'speech therapy' and 'speech disturbance'. Pre-screen missed explicit motor diagnosis of spastic dysarthria.",
    "R243641111": "Matched 'speech evaluation' and CPT 92506. Pre-screen misidentified audiology-linked general speech order as stuttering.",
    "R284656655": "Matched 'speech evaluation' and DX 315.39. Pre-screen assigned Positive for general speech delay evaluation.",
    "R260516492": "Matched 'speech evaluation and treatment' DX 315.39 with CCC-SLP. Pre-screen mislabeled non-stuttering speech disorder.",
    "R260607966": "Matched general CCC-SLP evaluation scheduling order. Pre-screen flagged administrative order lacking stuttering symptoms.",
    "R252590287": "Matched administrative DX 307.0 billing code. Pre-screen flagged scheduling order lacking clinical stuttering documentation.",
    "R212870908": "Matched CCC-SLP provider and speech CPT codes (92567, 92582). Pre-screen captured administrative scheduling notes.",
    "R291752631": "Matched administrative 'S/L/fluency eval' order with CCC-SLP across 3 decades. Zero clinical stuttering symptoms documented.",
    "R210758594": "Heuristic token match on longitudinal record. Clinical deep synthesis confirmed zero stuttering keywords in clinical context.",
    "R216716673": "Administrative regex token match. Deep evaluation confirmed complete absence of affirmative patient stuttering signal."
}

def generate_patient_document(grid):
    meta = patient_meta.get(grid, {})
    dx = meta.get("diagnosis", "Negative")
    conf = meta.get("confidence", 0.80)
    year_span = meta.get("year_span", "")
    reasoning = meta.get("reasoning", "").replace("**", "")
    evidence = meta.get("evidence", [])
    
    # Load and parse EHR notes
    ehr_path = os.path.join(ehr_dir, f"{grid}.md")
    ehr_content = ""
    if os.path.exists(ehr_path):
        with open(ehr_path, "r", encoding="utf-8") as f:
            ehr_content = f.read()
            
    notes = parse_ehr_notes(ehr_content)
    
    doc = docx.Document()
    
    # Page Setup
    for s in doc.sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        
        # Header
        h = s.header
        ph = h.paragraphs[0]
        ph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        rh = ph.add_run(f"PHENOAGENT CLINICAL EXPERT REVIEW | PATIENT: {grid}")
        rh.font.name = "Calibri"
        rh.font.size = Pt(8.5)
        rh.font.color.rgb = COLOR_MUTED
        
        # Footer
        ft = s.footer
        pf = ft.paragraphs[0]
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        rf = pf.add_run(f"Confidential — Medical Record Review for Stuttering Phenotyping ({grid})")
        rf.font.name = "Calibri"
        rf.font.size = Pt(8.5)
        rf.font.color.rgb = COLOR_MUTED

    # Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(8)
    p_title.paragraph_format.space_after = Pt(2)
    r_t = p_title.add_run(f"Clinical Expert Review: Patient {grid}")
    r_t.bold = True
    r_t.font.name = "Calibri"
    r_t.font.size = Pt(20)
    r_t.font.color.rgb = COLOR_NAVY
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(8)
    r_s = p_sub.add_run("Phenotyping Adjudication Dossier & Complete Clinical Notes for Manual Review")
    r_s.font.name = "Calibri"
    r_s.font.size = Pt(11)
    r_s.font.color.rgb = COLOR_SLATE
    
    # Summary Box Table
    sum_tbl = doc.add_table(rows=5, cols=2)
    sum_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sum_tbl.autofit = False
    set_table_borders(sum_tbl, color="CBD5E0", sz="6")
    
    box_fields = [
        ("Patient Identifier", grid),
        ("PhenoAgent Classification", f"{dx.upper()} {'(Family History Only)' if dx == 'Excluded' else ''}"),
        ("Model Confidence Score", f"{conf:.2f}"),
        ("Longitudinal Record Volume", f"{len(notes)} Clinical Notes ({len(ehr_content):,} characters)"),
        ("Longitudinal Timeline Span", year_span)
    ]
    for row_idx, (lbl, val) in enumerate(box_fields):
        c0 = sum_tbl.cell(row_idx, 0)
        c1 = sum_tbl.cell(row_idx, 1)
        c0.width = Inches(2.2)
        c1.width = Inches(4.3)
        set_cell_background(c0, "FAF5FF" if dx == "Excluded" else "F7FAFC")
        set_cell_background(c1, "FFFFFF")
        set_cell_margins(c0, top=50, bottom=50, left=80, right=80)
        set_cell_margins(c1, top=50, bottom=50, left=80, right=80)
        
        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(lbl)
        r0.bold = True
        r0.font.name = "Calibri"
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = COLOR_NAVY
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(val)
        r1.font.name = "Calibri"
        r1.font.size = Pt(9.5)
        if row_idx == 1:
            r1.bold = True
            r1.font.color.rgb = RGBColor(128, 90, 213) if dx == "Excluded" else RGBColor(197, 48, 48)
        else:
            r1.font.color.rgb = COLOR_BODY
            
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Section 1: Clinical Rationale
    p_h1 = doc.add_paragraph()
    p_h1.paragraph_format.space_before = Pt(8)
    p_h1.paragraph_format.space_after = Pt(4)
    rh1 = p_h1.add_run("1. PhenoAgent Clinical Decision Rationale")
    rh1.bold = True
    rh1.font.name = "Calibri"
    rh1.font.size = Pt(13)
    rh1.font.color.rgb = COLOR_NAVY
    
    p_r = doc.add_paragraph()
    p_r.paragraph_format.space_before = Pt(2)
    p_r.paragraph_format.space_after = Pt(6)
    rr = p_r.add_run(reasoning)
    rr.font.name = "Calibri"
    rr.font.size = Pt(9.5)
    rr.font.color.rgb = COLOR_BODY
    
    # Section 2: Naive Pre-Screen Trigger
    p_h2 = doc.add_paragraph()
    p_h2.paragraph_format.space_before = Pt(6)
    p_h2.paragraph_format.space_after = Pt(4)
    rh2 = p_h2.add_run("2. Naive Pre-Screening Flag Trigger")
    rh2.bold = True
    rh2.font.name = "Calibri"
    rh2.font.size = Pt(13)
    rh2.font.color.rgb = COLOR_NAVY
    
    p_t = doc.add_paragraph()
    p_t.paragraph_format.space_before = Pt(2)
    p_t.paragraph_format.space_after = Pt(6)
    trig_text = pre_screen_triggers.get(grid, "Captured by preliminary heuristic search rules.")
    rt = p_t.add_run(f"Initial Capture Context: {trig_text}")
    rt.font.name = "Calibri"
    rt.font.size = Pt(9.5)
    rt.font.color.rgb = COLOR_BODY
    
    # Section 3: Extracted Evidence
    p_h3 = doc.add_paragraph()
    p_h3.paragraph_format.space_before = Pt(6)
    p_h3.paragraph_format.space_after = Pt(4)
    rh3 = p_h3.add_run("3. Extracted Stuttering-Related Findings & Quotes")
    rh3.bold = True
    rh3.font.name = "Calibri"
    rh3.font.size = Pt(13)
    rh3.font.color.rgb = COLOR_NAVY
    
    # Callout box for quotes
    call_tbl = doc.add_table(rows=1, cols=1)
    call_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    call_tbl.autofit = False
    cc = call_tbl.cell(0, 0)
    cc.width = Inches(6.5)
    set_cell_background(cc, "FAF5FF" if dx == "Excluded" else "F0F4F8")
    set_cell_border_left_accent(cc, "805AD5" if dx == "Excluded" else "2B6CB0", sz="24")
    set_cell_margins(cc, top=100, bottom=100, left=140, right=120)
    
    cp0 = cc.paragraphs[0]
    cp0.paragraph_format.space_after = Pt(4)
    rc_title = cp0.add_run("Key Text Mentions Identified in Record:")
    rc_title.bold = True
    rc_title.font.name = "Calibri"
    rc_title.font.size = Pt(9.5)
    rc_title.font.color.rgb = COLOR_NAVY
    
    if evidence:
        for ev in evidence:
            cp = cc.add_paragraph()
            cp.paragraph_format.space_before = Pt(1)
            cp.paragraph_format.space_after = Pt(2)
            cp.paragraph_format.left_indent = Inches(0.15)
            rb = cp.add_run("• ")
            rb.bold = True
            rb.font.color.rgb = COLOR_SLATE
            rev = cp.add_run(f'"{ev}"')
            rev.font.name = "Calibri"
            rev.font.size = Pt(9.0)
            rev.font.color.rgb = COLOR_BODY
    else:
        cp = cc.add_paragraph()
        cp.paragraph_format.space_before = Pt(1)
        cp.paragraph_format.space_after = Pt(2)
        cp.paragraph_format.left_indent = Inches(0.15)
        rev = cp.add_run("No affirmative patient-level stuttering symptoms or test scores found in record.")
        rev.font.name = "Calibri"
        rev.font.size = Pt(9.0)
        rev.font.color.rgb = COLOR_MUTED
        
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # Section 4: Expert Adjudication Options (NO SIGN-OFF TABLE)
    p_h4 = doc.add_paragraph()
    p_h4.paragraph_format.space_before = Pt(6)
    p_h4.paragraph_format.space_after = Pt(4)
    rh4 = p_h4.add_run("4. Expert Review Adjudication Options")
    rh4.bold = True
    rh4.font.name = "Calibri"
    rh4.font.size = Pt(13)
    rh4.font.color.rgb = COLOR_NAVY
    
    adj_tbl = doc.add_table(rows=1, cols=1)
    adj_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    adj_tbl.autofit = False
    ac = adj_tbl.cell(0, 0)
    ac.width = Inches(6.5)
    set_cell_background(ac, "FAFAFA")
    set_box_borders(ac, color="CBD5E0", sz="8")
    set_cell_margins(ac, top=100, bottom=100, left=140, right=140)
    
    ap0 = ac.paragraphs[0]
    ap0.paragraph_format.space_after = Pt(4)
    rap = ap0.add_run("Please select your clinical adjudication verdict for this case:")
    rap.bold = True
    rap.font.name = "Calibri"
    rap.font.size = Pt(9.5)
    rap.font.color.rgb = COLOR_NAVY
    
    options = [
        f"☐ AGREE with PhenoAgent: Confirm classification as {dx.upper()} {'(Family History Only)' if dx == 'Excluded' else ''}",
        "☐ OVERTURN to POSITIVE: Patient demonstrates true developmental or persistent stuttering",
        "☐ OVERTURN to INDETERMINATE: Documentation is inconclusive, contradictory, or insufficient",
        "☐ OTHER (specify in reviewer commentary below)"
    ]
    for opt in options:
        p_opt = ac.add_paragraph()
        p_opt.paragraph_format.space_before = Pt(1)
        p_opt.paragraph_format.space_after = Pt(2)
        p_opt.paragraph_format.left_indent = Inches(0.15)
        ro = p_opt.add_run(opt)
        ro.font.name = "Calibri"
        ro.font.size = Pt(9.5)
        ro.font.color.rgb = COLOR_BODY
        
    p_c = ac.add_paragraph()
    p_c.paragraph_format.space_before = Pt(6)
    p_c.paragraph_format.space_after = Pt(2)
    rc_lbl = p_c.add_run("Reviewer Notes & Clinical Observations:")
    rc_lbl.bold = True
    rc_lbl.font.name = "Calibri"
    rc_lbl.font.size = Pt(9.5)
    
    for _ in range(2):
        p_l = ac.add_paragraph()
        p_l.paragraph_format.space_before = Pt(0)
        p_l.paragraph_format.space_after = Pt(2)
        rl = p_l.add_run("_________________________________________________________________________________")
        rl.font.color.rgb = RGBColor(203, 213, 224)
        rl.font.size = Pt(9)
        
    doc.add_paragraph().paragraph_format.space_after = Pt(10)
    
    # Section 5: Full Clinical Notes
    doc.add_page_break()
    
    p_h5 = doc.add_paragraph()
    p_h5.paragraph_format.space_before = Pt(8)
    p_h5.paragraph_format.space_after = Pt(4)
    rh5 = p_h5.add_run(f"5. Longitudinal Clinical Notes ({len(notes)} Notes)")
    rh5.bold = True
    rh5.font.name = "Calibri"
    rh5.font.size = Pt(14)
    rh5.font.color.rgb = COLOR_NAVY
    
    p_desc = doc.add_paragraph()
    p_desc.paragraph_format.space_before = Pt(0)
    p_desc.paragraph_format.space_after = Pt(8)
    r_desc = p_desc.add_run(
        "Below are the complete, unedited clinical notes from the patient's EHR arranged in chronological order. "
        "Reviewers may inspect these encounters to evaluate speech development, physician impressions, and provider communications."
    )
    r_desc.font.name = "Calibri"
    r_desc.font.size = Pt(9.5)
    r_desc.font.color.rgb = COLOR_MUTED
    
    for idx, n in enumerate(notes, 1):
        # Note Header
        nh_tbl = doc.add_table(rows=1, cols=1)
        nh_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        nh_tbl.autofit = False
        nhc = nh_tbl.cell(0, 0)
        nhc.width = Inches(6.5)
        set_cell_background(nhc, "EDF2F7")
        set_cell_margins(nhc, top=40, bottom=40, left=60, right=60)
        
        nhp = nhc.paragraphs[0]
        nhp.paragraph_format.space_after = Pt(0)
        r_nh1 = nhp.add_run(f"Note {idx}: ")
        r_nh1.bold = True
        r_nh1.font.name = "Calibri"
        r_nh1.font.size = Pt(9.5)
        r_nh1.font.color.rgb = COLOR_NAVY
        
        date_str = f"[{n['date']}] " if n['date'] else ""
        title_str = n['title'] if n['title'] else "Clinical Encounter Note"
        r_nh2 = nhp.add_run(f"{date_str}{title_str}")
        r_nh2.bold = True
        r_nh2.font.name = "Calibri"
        r_nh2.font.size = Pt(9.5)
        r_nh2.font.color.rgb = COLOR_SLATE
        
        if n['source']:
            r_nh3 = nhp.add_run(f"  |  Source: {n['source']}")
            r_nh3.font.name = "Calibri"
            r_nh3.font.size = Pt(8.5)
            r_nh3.font.color.rgb = COLOR_MUTED
            
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        
        # Note Body
        body_text = n['body'].strip()
        if not body_text:
            body_text = "(No additional note text recorded)"
            
        # Add paragraphs of note body
        body_paras = body_text.split("\n\n")
        for bp_text in body_paras:
            clean_bp = bp_text.strip()
            if not clean_bp:
                continue
            np_p = doc.add_paragraph()
            np_p.paragraph_format.space_before = Pt(1)
            np_p.paragraph_format.space_after = Pt(3)
            np_p.paragraph_format.line_spacing = 1.15
            r_body = np_p.add_run(clean_bp)
            r_body.font.name = "Calibri"
            r_body.font.size = Pt(9.0)
            r_body.font.color.rgb = COLOR_BODY
            
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        
    out_file = os.path.join(output_dir, f"{grid}_Review.docx")
    doc.save(out_file)
    print(f"Generated {out_file} ({len(notes)} notes, {os.path.getsize(out_file):,} bytes)")
    return out_file

# Process all 17 patients
grids_all = [
    "R212618220", "R249876813", "R257016144", "R272837566", "R275078358", "R290040058",
    "R210758594", "R212870908", "R216716673", "R243641111", "R250115464", "R252590287",
    "R260516492", "R260607966", "R284656655", "R291752631", "R293758494"
]

generated_files = []
for g in grids_all:
    fpath = generate_patient_document(g)
    generated_files.append(fpath)

print(f"\nAll {len(generated_files)} individual review documents successfully generated in '{output_dir}'.")
