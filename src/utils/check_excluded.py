import json

with open("non_positive_raw_dump.json", "r") as f:
    data = json.load(f)

grids_excluded = ["R212618220", "R249876813", "R257016144", "R272837566", "R275078358", "R290040058"]

for g in grids_excluded:
    j = data[g]["json"]
    print(f"\n==================== {g} (Excluded, conf {j.get('confidence')}) ====================")
    print("Decision path:", j.get("decision_path"))
    print("Reasoning snippet:\n", j.get("reasoning"))
    print("Evidence:")
    for ev in j.get("evidence", []):
        print("  -", ev)
