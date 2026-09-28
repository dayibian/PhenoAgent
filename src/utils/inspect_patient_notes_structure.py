import os
import json

with open("non_positive_raw_dump.json") as f:
    d = json.load(f)

for g, v in d.items():
    j = v["json"]
    steps = j.get("trace", {}).get("steps", [])
    dg_summary = [s.get("summary", "") for s in steps if s.get("agent") == "DataGatherer"]
    print(g, dg_summary[0] if dg_summary else "No DG summary")
