import os
import json
import re

ehr_dir = "data/stuttering/ehr_markdown_dataset"
json_dir = "results/stuttering_parallel/json_results"

grids_all = [
    "R212618220", "R249876813", "R257016144", "R272837566", "R275078358", "R290040058",
    "R210758594", "R212870908", "R216716673", "R243641111", "R250115464", "R252590287",
    "R260516492", "R260607966", "R284656655", "R291752631", "R293758494"
]

results = {}

for grid in grids_all:
    json_path = os.path.join(json_dir, f"{grid}.json")
    ehr_path = os.path.join(ehr_dir, f"{grid}.md")
    
    with open(json_path) as f:
        j = json.load(f)
    with open(ehr_path) as f:
        ehr = f.read()
        
    # Extract notes by splitting on markdown headers like '### Note' or similar
    # Check how ehr markdown is structured
    notes = []
    # Find all Note sections or dates
    current_note = []
    for line in ehr.split("\n"):
        if line.startswith("## ") or line.startswith("### "):
            if current_note:
                notes.append("\n".join(current_note))
                current_note = []
        current_note.append(line)
    if current_note:
        notes.append("\n".join(current_note))
        
    # Find mentions of stutter, stammer, speech, slp, etc. in notes
    relevant_snippets = []
    for idx, n in enumerate(notes, 1):
        n_lower = n.lower()
        if any(k in n_lower for k in ["stutter", "stammer", "disfluen", "dysfluen", "speech", "slp", "dysarthria"]):
            # Find matching lines
            matched_lines = [l.strip() for l in n.split("\n") if any(k in l.lower() for k in ["stutter", "stammer", "disfluen", "dysfluen", "speech", "slp", "dysarthria", "date", "service date"]) and len(l.strip()) > 0]
            relevant_snippets.append({
                "note_index": idx,
                "lines": matched_lines[:6]
            })
            
    # Extract date span from EHR
    date_matches = re.findall(r"\b(19\d\d|20\d\d)[-/]\d\d[-/]\d\d\b", ehr)
    date_years = sorted(list(set(re.findall(r"\b(19\d\d|20\d\d)\b", ehr))))
    year_span = f"{date_years[0]} – {date_years[-1]}" if len(date_years) > 1 else (date_years[0] if date_years else "Unknown")
    
    results[grid] = {
        "grid": grid,
        "diagnosis": j.get("diagnosis"),
        "confidence": j.get("confidence"),
        "year_span": year_span,
        "total_notes": len(notes),
        "char_len": len(ehr),
        "reasoning": j.get("reasoning"),
        "evidence": j.get("evidence", []),
        "decision_path": j.get("decision_path", ""),
        "relevant_snippets": relevant_snippets[:5]
    }

with open("detailed_non_positive_snippets.json", "w") as f:
    json.dump(results, f, indent=2)

print("Processed all 17 patients, saved detailed_non_positive_snippets.json")
