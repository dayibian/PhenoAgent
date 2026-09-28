import json

with open("non_positive_raw_dump.json", "r") as f:
    data = json.load(f)

grids_negative = ["R210758594", "R212870908", "R216716673", "R243641111"]

for g in grids_negative:
    j = data[g]["json"]
    print(f"\n==================== {g} (Negative, conf {j.get('confidence')}) ====================")
    print("Decision path:", j.get("decision_path"))
    print("Reasoning snippet:\n", j.get("reasoning"))
    print("Evidence:")
    for ev in j.get("evidence", []):
        print("  -", ev)
