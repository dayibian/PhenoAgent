import os
import json

ehr_dir = "data/stuttering/ehr_markdown_dataset"
json_dir = "results/stuttering_parallel/json_results"

grids_excluded = ["R212618220", "R249876813", "R257016144", "R272837566", "R275078358", "R290040058"]
grids_negative = ["R210758594", "R212870908", "R216716673", "R243641111", "R250115464", "R252590287", "R260516492", "R260607966", "R284656655", "R291752631", "R293758494"]

all_17 = grids_excluded + grids_negative
print(f"Total non-positive grids: {len(all_17)}")

data_17 = {}
for g in all_17:
    json_path = os.path.join(json_dir, f"{g}.json")
    ehr_path = os.path.join(ehr_dir, f"{g}.md")
    
    jdata = {}
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            jdata = json.load(f)
            
    ehr_text = ""
    if os.path.exists(ehr_path):
        with open(ehr_path, "r", encoding="utf-8") as f:
            ehr_text = f.read()
            
    # Find dates in EHR
    dates = []
    for line in ehr_text.split("\n"):
        if "date:" in line.lower() or "service date:" in line.lower():
            dates.append(line.strip())
            
    data_17[g] = {
        "json": jdata,
        "ehr_char_len": len(ehr_text),
        "ehr_lines": len(ehr_text.split("\n")),
        "sample_dates": dates[:5]
    }
    print(f"{g}: {jdata.get('diagnosis')} (conf {jdata.get('confidence')}), EHR len: {len(ehr_text)} chars, {len(dates)} date hits")

with open("non_positive_raw_dump.json", "w", encoding="utf-8") as f:
    json.dump(data_17, f, indent=2)
print("Dumped non_positive_raw_dump.json")
