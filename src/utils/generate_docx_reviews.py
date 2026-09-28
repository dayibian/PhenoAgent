import os
import re
import glob
import json
import yaml
from copy import deepcopy
import pandas as pd
import openpyxl

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# Paths
results_csv = "/home/biand/Projects/PhenoAgent/results/controls_151/controls_151_results.csv"
gt_path = "/home/biand/Projects/Celiac_BioVU/data/Celiac Diagnosis by Manual Review.xlsx"
controls_path = "/home/biand/Projects/Celiac_BioVU/data/controls_need_review.csv"
dataset_dir = "/home/biand/Projects/Celiac_BioVU/data/ehr_markdown_dataset"
yaml_path = "/home/biand/Projects/Celiac_BioVU/data/celiac_keywords_latest.yaml"
out_dir = "/home/biand/Projects/PhenoAgent/data/additional_notes_for_review"

os.makedirs(out_dir, exist_ok=True)

# Styling Helpers
def set_cell_background(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for margin, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{margin}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_styled_heading(doc, text, level, space_before=12, space_after=6):
    heading = doc.add_heading(text, level=level)
    heading.paragraph_format.space_before = Pt(space_before)
    heading.paragraph_format.space_after = Pt(space_after)
    heading.paragraph_format.keep_with_next = True
    
    run = heading.runs[0]
    run.font.name = 'Calibri'
    if level == 1:
        run.font.size = Pt(17)
        run.font.bold = True
        run.font.color.rgb = RGBColor(26, 54, 93)  # Deep Blue
    elif level == 2:
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(44, 82, 130)  # Slate Blue
    elif level == 3:
        run.font.size = Pt(10.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(74, 85, 104)  # Charcoal
        
    return heading

def style_document(doc):
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
        
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(10.5)
    font.color.rgb = RGBColor(33, 37, 41)
    style.paragraph_format.line_spacing = 1.15
    style.paragraph_format.space_after = Pt(4)

# Quality Filtering Helpers
def is_low_quality_line(line: str) -> bool:
    """Detect lines that are OCR noise, fax transmission garbage, or non-readable text."""
    s = line.strip()
    if not s:
        return False
    
    # Check for fax headers or transmission junk
    if re.search(r'FACSIMILE TRANSMIT|FAX N0\.|NOV~?\d+~\d+|FHX N0\.|ADMIMBTEHEO|TRANSMITAL', s, re.IGNORECASE):
        return True
        
    # Check symbol density
    symbol_chars = sum(1 for c in s if c in "~@#$%^&*`_+=|\\{}[]<>'\"?")
    if len(s) >= 8 and (symbol_chars / len(s)) > 0.20:
        return True
        
    # Check alpha character ratio
    alpha_chars = sum(1 for c in s if c.isalpha())
    total_non_space = sum(1 for c in s if not c.isspace())
    if total_non_space >= 8 and (alpha_chars / total_non_space) < 0.50:
        return True

    # Check for repeated isolated junk tokens (e.g., 'A '0 UPPW on ... W um Q ...')
    words = s.split()
    if len(words) >= 4:
        short_words = sum(1 for w in words if len(w) <= 2 or not any(c.isalpha() for c in w))
        if (short_words / len(words)) >= 0.70:
            return True
            
    # Check for long strings of random numbers or punctuation
    if re.search(r'[\d\.\-\:\;\,\~]{7,}', s):
        return True

    return False

def clean_body_text(body: str) -> str:
    """Filter out OCR artifacts and low quality lines from note body."""
    lines = body.split('\n')
    cleaned_lines = []
    
    for line in lines:
        if is_low_quality_line(line):
            continue
        cleaned_lines.append(line)
        
    cleaned_body = '\n'.join(cleaned_lines).strip()
    
    # Check if remaining text has meaningful clinical content
    words = [w for w in re.split(r'\s+', cleaned_body) if w and any(c.isalpha() for c in w)]
    if len(words) < 8:
        return ""
        
    # Clean excessive empty lines
    cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body)
    return cleaned_body

# Load keywords
with open(yaml_path, 'r', encoding='utf-8') as f:
    kw_data = yaml.safe_load(f)
popular_words = kw_data.get('popular_words', [])
kw_pattern = re.compile('|'.join([re.escape(w) for w in popular_words]), re.IGNORECASE) if popular_words else None

def parse_patient_markdown(md_path):
    if not os.path.exists(md_path):
        return {'labs': [], 'notes': []}
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Labs
    labs = []
    labs_match = re.search(r'## Labs\n(.*?)(## Medical Notes|\Z)', content, re.DOTALL)
    if labs_match:
        labs_text = labs_match.group(1).strip()
        for line in labs_text.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                labs.append(line.replace('- ', '').strip())
            elif line and line != 'No labs available.':
                labs.append(line)
                
    # Medical Notes
    notes = []
    notes_match = re.search(r'## Medical Notes\n(.*)', content, re.DOTALL)
    if notes_match:
        notes_text = notes_match.group(1).strip()
        splits = re.split(r'###\s+\[', notes_text)
        for sp in splits:
            sp = sp.strip()
            if not sp:
                continue
            parts = sp.split(']', 1)
            if len(parts) < 2:
                continue
            date_str = parts[0].strip()
            rest = parts[1].strip()
            lines = rest.split('\n')
            title = lines[0].strip()
            source = "Unknown"
            body_start = 1
            if len(lines) > 1 and lines[1].strip().startswith('**Source:**'):
                source = lines[1].replace('**Source:**', '').strip()
                body_start = 2
            raw_body = "\n".join(lines[body_start:]).strip()
            
            # Clean OCR noise and low quality text
            cleaned_body = clean_body_text(raw_body)
            if not cleaned_body:
                continue
                
            notes.append({
                'date': date_str,
                'title': title,
                'source': source,
                'body': cleaned_body
            })
            
    filtered_notes = []
    if kw_pattern:
        for n in notes:
            text_to_check = f"{n['title']} {n['source']} {n['body']}"
            if kw_pattern.search(text_to_check):
                filtered_notes.append(n)
    if not filtered_notes and notes:
        filtered_notes = notes
        
    return {'labs': labs, 'notes': filtered_notes, 'total_notes_count': len(notes)}

def add_patient_to_doc(doc, p_data, clinical_data):
    # 1. Heading: Patient Grid ID
    add_styled_heading(doc, f"Clinical Review Packet: Patient {p_data['grid']}", level=1, space_before=14, space_after=8)
    
    # 2. Metadata Table
    table = doc.add_table(rows=6, cols=2)
    table.style = 'Light Shading Accent 1'
    table.autofit = False
    
    table.columns[0].width = Inches(1.8)
    table.columns[1].width = Inches(4.9)
    
    headers = [
        ("Patient Identifier", p_data['grid']),
        ("Cohort / Study Group", f"Controls Need Review (no_ttgiga) — ICD Code Count: {p_data['icd_count']}"),
        ("Model Prediction", f"{p_data['diagnosis']} (Confidence: {p_data['confidence']:.2f})"),
        ("Key Extracted Evidence", p_data['evidence'] if p_data['evidence'] else "None extracted"),
        ("Algorithm Decision Logic", p_data['reasoning']),
        ("Clinical Adjudication", "[ ] Positive (Confirmed Celiac)\n[ ] Negative (Not Celiac / Alternate Etiology)\n[ ] PMH Only (Unconfirmed billing/history)\n[ ] Unknown / Indeterminate\n\nReviewer Notes: ____________________________________")
    ]
    
    for idx, (label, val) in enumerate(headers):
        row = table.rows[idx]
        cell_lbl, cell_val = row.cells[0], row.cells[1]
        
        # Style label cell
        p_lbl = cell_lbl.paragraphs[0]
        run_lbl = p_lbl.add_run(label)
        run_lbl.bold = True
        run_lbl.font.size = Pt(9.5)
        run_lbl.font.color.rgb = RGBColor(26, 54, 93)
        set_cell_background(cell_lbl, "F0F4F8")
        set_cell_margins(cell_lbl, top=70, bottom=70, left=100, right=100)
        
        # Style value cell
        p_val = cell_val.paragraphs[0]
        run_val = p_val.add_run(val)
        run_val.font.size = Pt(9.5)
        set_cell_margins(cell_val, top=70, bottom=70, left=100, right=100)
        
    doc.add_paragraph().paragraph_format.space_after = Pt(8)
    
    # 3. Labs Section
    add_styled_heading(doc, "Laboratory Results", level=2, space_before=10, space_after=4)
    if clinical_data['labs']:
        for lab in clinical_data['labs']:
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_after = Pt(2)
            match = re.match(r'^\[(.*?)\]', lab)
            if match:
                date_str = match.group(1)
                rest = lab[len(date_str)+2:].strip()
                r_date = p.add_run(f"[{date_str}] ")
                r_date.bold = True
                p.add_run(rest)
            else:
                p.add_run(lab)
    else:
        p = doc.add_paragraph()
        r = p.add_run("No relevant laboratory values identified in the electronic medical record.")
        r.italic = True
        
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    
    # 4. Clinical Notes Section
    add_styled_heading(doc, f"Relevant Medical Notes ({len(clinical_data['notes'])} notes containing celiac-specific signals)", level=2, space_before=10, space_after=4)
    
    if clinical_data['notes']:
        for idx, note in enumerate(clinical_data['notes'], 1):
            p_title = doc.add_paragraph()
            p_title.paragraph_format.space_before = Pt(6)
            p_title.paragraph_format.space_after = Pt(1)
            p_title.paragraph_format.keep_with_next = True
            
            r_num = p_title.add_run(f"Note {idx}: [{note['date']}] ")
            r_num.bold = True
            r_num.font.color.rgb = RGBColor(44, 82, 130)
            
            r_title = p_title.add_run(note['title'])
            r_title.bold = True
            
            p_src = doc.add_paragraph()
            p_src.paragraph_format.space_after = Pt(3)
            p_src.paragraph_format.keep_with_next = True
            r_src_lbl = p_src.add_run("Document Source: ")
            r_src_lbl.font.size = Pt(9.0)
            r_src_lbl.bold = True
            r_src_val = p_src.add_run(note['source'])
            r_src_val.font.size = Pt(9.0)
            r_src_val.italic = True
            
            body_text = note['body'].strip()
            blocks = re.split(r'\n\s*\n', body_text)
            for block in blocks:
                block_clean = block.strip()
                if not block_clean:
                    continue
                chunk_size = 15000
                chunks = [block_clean[i:i+chunk_size] for i in range(0, len(block_clean), chunk_size)]
                for chunk in chunks:
                    p_body = doc.add_paragraph()
                    p_body.paragraph_format.left_indent = Inches(0.2)
                    p_body.paragraph_format.space_after = Pt(3)
                    r_body = p_body.add_run(chunk)
                    r_body.font.size = Pt(9.0)
                
            if idx < len(clinical_data['notes']):
                p_div = doc.add_paragraph()
                p_div.paragraph_format.space_before = Pt(4)
                p_div.paragraph_format.space_after = Pt(4)
                p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_div = p_div.add_run("·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·")
                r_div.font.color.rgb = RGBColor(160, 174, 192)
                r_div.font.size = Pt(8.5)
    else:
        p = doc.add_paragraph()
        r = p.add_run("No clinical notes identified in the electronic medical record.")
        r.italic = True

def main():
    print("Identifying 33 unreviewed positive patients...")
    df_res = pd.read_csv(results_csv)
    pos = df_res[df_res['diagnosis'] == 'Positive'].copy()

    wb = openpyxl.load_workbook(gt_path, data_only=True)
    sheet = wb.active
    gt_grids = set()
    for row in sheet.iter_rows(min_row=2, values_only=True):
        g = str(row[0]).strip() if row[0] is not None else ''
        if g:
            gt_grids.add(g)

    unreviewed_pos = pos[~pos['grid'].isin(gt_grids)].copy()
    unreviewed_pos = unreviewed_pos.sort_values(by='grid').reset_index(drop=True)

    df_ctrl = pd.read_csv(controls_path)
    unreviewed_pos = pd.merge(unreviewed_pos, df_ctrl[['grid', 'icd_count']], on='grid', how='left')
    unreviewed_pos['icd_count'] = unreviewed_pos['icd_count'].fillna(0).astype(int)

    print(f"Generating Word documents for {len(unreviewed_pos)} patients (with low-quality OCR text filtered)...")

    # Combined master docx
    combined_doc = docx.Document()
    style_document(combined_doc)

    # Title Page
    p_title = combined_doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(100)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run("CLINICAL REVIEW PACKAGE\nCeliac Disease Diagnostic Classification")
    r_title.font.size = Pt(24)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(26, 54, 93)

    p_sub = combined_doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(30)
    r_sub = p_sub.add_run("Audit of Unreviewed Positive EHR Records (N=33)\nBioVU Controls Requiring Manual Review")
    r_sub.font.size = Pt(13)
    r_sub.font.color.rgb = RGBColor(74, 85, 104)

    p_meta = combined_doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_meta.paragraph_format.space_before = Pt(140)
    r_meta = p_meta.add_run("Prepared for Clinical Reviewers and Medical Evaluators\nPhenoAgent Diagnostic Phenotyping System\nDate: August 2026")
    r_meta.font.size = Pt(10.5)
    r_meta.italic = True

    combined_doc.add_page_break()

    for idx, row in unreviewed_pos.iterrows():
        grid = row['grid']
        print(f"[{idx+1}/{len(unreviewed_pos)}] Processing {grid}...")
        p_data = {
            'grid': grid,
            'diagnosis': row['diagnosis'],
            'confidence': row['confidence'],
            'reasoning': str(row['reasoning']),
            'evidence': str(row['evidence']) if pd.notna(row['evidence']) else "",
            'icd_count': row['icd_count']
        }
        md_file = os.path.join(dataset_dir, f"{grid}.md")
        clinical_data = parse_patient_markdown(md_file)

        # Individual Word document
        indiv_doc = docx.Document()
        style_document(indiv_doc)
        add_patient_to_doc(indiv_doc, p_data, clinical_data)

        indiv_path = os.path.join(out_dir, f"Patient_{grid}_Review.docx")
        indiv_doc.save(indiv_path)

        # Append to combined doc
        for element in indiv_doc.element.body:
            if element.tag.endswith('sectPr'):
                continue
            combined_doc.element.body.append(deepcopy(element))

        if idx < len(unreviewed_pos) - 1:
            combined_doc.add_page_break()

    # Save combined package
    combined_path = os.path.join(out_dir, "All_33_Unreviewed_Cases_Review_Package.docx")
    combined_doc.save(combined_path)
    print(f"\nSaved combined review package: {combined_path}")

    # Delete any lingering .md files in the output directory
    md_files = glob.glob(os.path.join(out_dir, "*.md"))
    for mf in md_files:
        os.remove(mf)

    print("\nAll Word documents updated and cleaned successfully.")

if __name__ == "__main__":
    main()
