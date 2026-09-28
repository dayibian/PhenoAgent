import re

def parse_ehr_notes(ehr_content):
    """
    Parses an EHR markdown file into structured notes.
    Expected format:
    # Grid: ...
    ## Labs ...
    ## Medical Notes
    ### [YYYY-MM-DD HH:MM:SS] Title
    **Source:** ...
    <content>
    """
    notes = []
    
    # Split by ### [
    pattern = r"(###\s*\[\d{4}-\d{2}-\d{2}[^\]]*\][^\n]*)"
    parts = re.split(pattern, ehr_content)
    
    if len(parts) <= 1:
        # Fallback split by ###
        pattern = r"(###\s*[^\n]+)"
        parts = re.split(pattern, ehr_content)
        
    # The first part is header/labs before the first note
    preamble = parts[0] if parts else ""
    
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i+1].strip() if i+1 < len(parts) else ""
        
        # Extract title and date
        date_match = re.search(r"\[(\d{4}-\d{2}-\d{2}[^\]]*)\]", header)
        date_str = date_match.group(1) if date_match else ""
        title = re.sub(r"###\s*(\[[^\]]*\])?", "", header).strip()
        
        # Extract source if present
        source = ""
        source_match = re.search(r"\*\*Source:\*\*\s*([^\n]+)", body)
        if source_match:
            source = source_match.group(1).strip()
            # Remove source line from body
            body = re.sub(r"\*\*Source:\*\*\s*[^\n]+\n*", "", body).strip()
            
        notes.append({
            "header": header,
            "date": date_str,
            "title": title,
            "source": source,
            "body": body
        })
        
    return preamble, notes

# Test on a few files
grids = ["R250115464", "R260607966", "R293758494", "R275078358"]
for g in grids:
    with open(f"data/stuttering/ehr_markdown_dataset/{g}.md") as f:
        c = f.read()
    preamble, notes = parse_ehr_notes(c)
    print(f"{g}: {len(notes)} notes parsed.")
    for idx, n in enumerate(notes[:3], 1):
        print(f"  Note {idx}: Date='{n['date']}', Title='{n['title']}', Source='{n['source']}', BodyLen={len(n['body'])}")
