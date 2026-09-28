import re

grids_all = [
    "R212618220", "R249876813", "R257016144", "R272837566", "R275078358", "R290040058",
    "R210758594", "R212870908", "R216716673", "R243641111", "R250115464", "R252590287",
    "R260516492", "R260607966", "R284656655", "R291752631", "R293758494"
]

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

for g in grids_all:
    with open(f"data/stuttering/ehr_markdown_dataset/{g}.md") as f:
        c = f.read()
    notes = parse_ehr_notes(c)
    print(f"{g}: {len(notes)} notes successfully parsed.")
