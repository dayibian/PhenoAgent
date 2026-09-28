import json

with open("non_positive_raw_dump.json", "r") as f:
    data = json.load(f)

grids_negative = ["R210758594", "R212870908", "R216716673", "R243641111", "R250115464", "R252590287", "R260516492", "R260607966"]

for g in grids_negative:
    j = data[g]["json"]
    print(f"\n==================== {g} (Negative, conf {j.get('confidence')}) ====================")
    print("Decision path:", j.get("decision_path"))
    print("Reasoning snippet:\n", j.get("reasoning"))
    print("Evidence:")
    for ev in j.get("evidence", []):
        print("  -", ev)
