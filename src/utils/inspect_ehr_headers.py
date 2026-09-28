import os

for g in ["R250115464", "R260607966", "R212870908"]:
    path = f"data/stuttering/ehr_markdown_dataset/{g}.md"
    with open(path) as f:
        content = f.read()
    print(f"=== {g} ({len(content)} chars) ===")
    lines = content.split("\n")
    headers = [l for l in lines if l.startswith("#")]
    print(f"Headers ({len(headers)}):", headers[:10])
    print("First 30 lines:\n" + "\n".join(lines[:30]))
