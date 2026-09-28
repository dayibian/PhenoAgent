import json

with open("non_positive_raw_dump.json", "r") as f:
    data = json.load(f)

for grid, item in data.items():
    j = item["json"]
    print(f"\n==================== {grid} ({j.get('diagnosis')}, conf {j.get('confidence')}) ====================")
    print("Decision path:", j.get("decision_path"))
    print("Reasoning snippet:\n", j.get("reasoning"))
    print("Evidence:")
    for ev in j.get("evidence", []):
        print("  -", ev)
    
    # Check trace steps
    steps = j.get("trace", {}).get("steps", [])
    for s in steps:
        if s.get("agent") == "DataGatherer":
            print("DataGatherer summary:", s.get("summary"))
        elif s.get("agent") == "Adjudicator":
            print("Adjudicator decisions:", len(s.get("note_decisions", [])))
            for nd in s.get("note_decisions", []):
                print("   Note decision:", nd.get("note_label"), nd.get("decision"), nd.get("reasoning")[:100] if nd.get("reasoning") else "")
