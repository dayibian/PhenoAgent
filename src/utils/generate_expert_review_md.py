import os
import json

with open("detailed_non_positive_snippets.json", "r") as f:
    patient_data = json.load(f)

md_lines = []

md_lines.append("# Clinical Expert Review Dossier: Non-Positive Cohort Adjudication")
md_lines.append("")
md_lines.append("**Target Phenotype:** Developmental & Persistent Stuttering (ICD-9 307.0 / ICD-10 F80.81)  ")
md_lines.append("**Cohort Scope:** 1,132 Total EHR Patients | 1,115 Positive (98.50%) | 17 Non-Positive (1.50%)  ")
md_lines.append("**Review Set:** 17 Cases (6 Excluded – Family History Only + 11 Negative – Rule-Out / Competing / No Signal)  ")
md_lines.append("**Word Document Saved At:** [`Non_Positive_Patients_Expert_Review_Dossier.docx`](file:///home/biand/Projects/PhenoAgent/results/stuttering_parallel/summary/Non_Positive_Patients_Expert_Review_Dossier.docx)  ")
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 1. Instructions for Clinical Expert Reviewers")
md_lines.append("")
md_lines.append("This review dossier compiles the longitudinal clinical records, extracted quotes, and multi-agent reasoning chains for the **17 non-positive patients** identified in the stuttering phenotyping cohort. In conventional automated phenotyping, these cases are frequently mislabeled as false positives due to keyword over-matching (family history, administrative SLP referrals, or competing motor-speech disorders like dysarthria).")
md_lines.append("")
md_lines.append("### Diagnostic Classification Criteria")
md_lines.append("")
md_lines.append("| Classification | Criteria & Definition |")
md_lines.append("| :--- | :--- |")
md_lines.append("| **Positive** | Documented speech-language pathology (CCC-SLP) diagnosis of developmental/persistent stuttering, standardized fluency score (SSI-3, SSI-4, %SS, OASES), or confirmed enrollment in fluency therapy. |")
md_lines.append("| **Excluded** | Stuttering keywords occur exclusively in the context of biological family history (parent, sibling, cousin, uncle) with verified absence of personal patient-level disfluency. |")
md_lines.append("| **Negative** | Explicit clinical rule-out (<3% disfluency), competing motor-speech disorder (e.g. spastic dysarthria), administrative SLP/audiology billing without stuttering, or complete absence of stuttering signal. |")
md_lines.append("| **Indeterminate** | Conflicting clinical records or insufficient evidence to definitively confirm or rule out. |")
md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 2. Cohort Master Roster of Non-Positive Cases (N=17)")
md_lines.append("")
md_lines.append("| # | Patient GRID | Classification | Confidence | Notes | Year Span | Core Clinical Mechanism / Reason |")
md_lines.append("| :- | :--- | :--- | :--- | :--- | :--- | :--- |")

roster = [
    ("R249876813", "Excluded", 0.85, 151, "2000 – 2023", "Family history only; relative had 4 yrs SLP therapy; patient fluent"),
    ("R212618220", "Excluded", 0.85, 84, "2000 – 2023", "Father stuttered as child; patient confirmed fluent in exam"),
    ("R257016144", "Excluded", 0.85, 95, "1998 – 2019", "Mother stutters; communication barrier for mom; zero patient symptoms"),
    ("R272837566", "Excluded", 0.85, 76, "2008 – 2020", "Mother had stuttering tic as child; no patient-level disfluency"),
    ("R275078358", "Excluded", 0.85, 11, "2017 – 2018", "Cousin diagnosed with stuttering; patient speech fluent"),
    ("R290040058", "Excluded", 0.85, 472, "1999 – 2025", "Mother stutters; multiple maternal notes over 26 years; patient fluent"),
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
    md_lines.append(f"| {idx} | **`{grid}`** | **{dx}** | {conf:.2f} | {notes} | {yrs} | {mech} |")

md_lines.append("")
md_lines.append("---")
md_lines.append("")
md_lines.append("## 3. Excluded Patients: Family History Only (N=6)")
md_lines.append("")

excluded_grids = ["R249876813", "R212618220", "R257016144", "R272837566", "R275078358", "R290040058"]

for p_num, grid in enumerate(excluded_grids, 1):
    p_info = patient_data.get(grid, {})
    md_lines.append(f"### Case {p_num}: Patient `{grid}`")
    md_lines.append(f"- **Classification:** **EXCLUDED (Family History Only)**")
    md_lines.append(f"- **Confidence:** `{p_info.get('confidence', 0.85):.2f}` | **Notes Analyzed:** `{p_info.get('total_notes', 0)}` | **Year Span:** `{p_info.get('year_span', '')}`")
    md_lines.append(f"- **Naive Pre-Screen Trigger:** Matched keyword `'stutter*'` in clinical notes without entity attribution.")
    md_lines.append("")
    md_lines.append(f"**Clinical Decision Rationale:**  \n{p_info.get('reasoning', '')}")
    md_lines.append("")
    md_lines.append("> [!NOTE]")
    md_lines.append("> **Extracted EHR Quotes & Mentions:**")
    for ev in p_info.get("evidence", []):
        md_lines.append(f"> - *\"{ev}\"*")
    md_lines.append("")
    md_lines.append("```")
    md_lines.append(f"[ ] AGREE with PhenoAgent (Excluded - Family History Only)")
    md_lines.append(f"[ ] OVERTURN to POSITIVE (True Patient Stuttering)")
    md_lines.append(f"[ ] OVERTURN to INDETERMINATE (Insufficient Evidence)")
    md_lines.append(f"Reviewer Notes: __________________________________________________________________")
    md_lines.append(f"Reviewer Signature: _______________________   Date: _________   Credentials: _____")
    md_lines.append("```")
    md_lines.append("")

md_lines.append("---")
md_lines.append("")
md_lines.append("## 4. Negative Patients: Rule-Outs, Competing Conditions, & Administrative Hits (N=11)")
md_lines.append("")

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

neg_idx = 1
for g_title, pts in negative_groups:
    md_lines.append(f"### {g_title}")
    md_lines.append("")
    for grid, short_desc in pts:
        p_info = patient_data.get(grid, {})
        md_lines.append(f"#### Case {neg_idx}: Patient `{grid}`")
        md_lines.append(f"- **Classification:** **NEGATIVE**")
        md_lines.append(f"- **Confidence:** `{p_info.get('confidence', 0.80):.2f}` | **Notes Analyzed:** `{p_info.get('total_notes', 0)}` | **Year Span:** `{p_info.get('year_span', '')}`")
        md_lines.append(f"- **Naive Pre-Screen Trigger:** {short_desc}")
        md_lines.append("")
        md_lines.append(f"**Clinical Decision Rationale:**  \n{p_info.get('reasoning', '')}")
        md_lines.append("")
        md_lines.append("> [!NOTE]")
        md_lines.append("> **Extracted EHR Quotes & Mentions:**")
        evs = p_info.get("evidence", [])
        if evs:
            for ev in evs:
                md_lines.append(f"> - *\"{ev}\"*")
        else:
            md_lines.append("> - *No affirmative stuttering symptoms or test scores found in record.*")
        md_lines.append("")
        md_lines.append("```")
        md_lines.append(f"[ ] AGREE with PhenoAgent (Negative)")
        md_lines.append(f"[ ] OVERTURN to POSITIVE (True Patient Stuttering)")
        md_lines.append(f"[ ] OVERTURN to INDETERMINATE (Insufficient Evidence)")
        md_lines.append(f"Reviewer Notes: __________________________________________________________________")
        md_lines.append(f"Reviewer Signature: _______________________   Date: _________   Credentials: _____")
        md_lines.append("```")
        md_lines.append("")
        neg_idx += 1

md_lines.append("---")
md_lines.append("")
md_lines.append("## 5. Expert Reviewer Consensus & Final Sign-Off Sheet")
md_lines.append("")
md_lines.append("| Field | Reviewer Input |")
md_lines.append("| :--- | :--- |")
md_lines.append("| **Lead Expert Reviewer Name** | ________________________________________________ |")
md_lines.append("| **Professional Credentials** | ________________________________________________ (e.g. CCC-SLP, MD, PhD) |")
md_lines.append("| **Review Completion Date** | ________________________________________________ |")
md_lines.append("| **Total Cases Evaluated** | 17 of 17 Non-Positive Cases |")
md_lines.append("| **Concordance Summary** | _____ Cases Agreed (_____%) \\| _____ Cases Overturned (_____%) |")
md_lines.append("| **Reviewer Signature** | ________________________________________________ |")

with open("results/stuttering_parallel/summary/non_positive_review_dossier.md", "w") as f:
    f.write("\n".join(md_lines))

print("Saved results/stuttering_parallel/summary/non_positive_review_dossier.md")
