import os
import glob
import json

json_dir = "results/stuttering_parallel/json_results"
files = glob.glob(os.path.join(json_dir, "*.json"))

print(f"Total JSON files found: {len(files)}")

records = []
for f in files:
    try:
        with open(f) as fp:
            d = json.load(fp)
            grid = d.get("grid", os.path.basename(f).replace(".json", ""))
            dx = d.get("diagnosis", "Unknown")
            conf = d.get("confidence", 0.0)
            t = d.get("time_taken_s", 0.0)
            
            # Extract notes count and reflection info
            notes_count = 0
            critic_rounds = 0
            re_extractions = 0
            steps = d.get("trace", {}).get("steps", [])
            for s in steps:
                if s.get("agent") == "DataGatherer":
                    summary = s.get("summary", "")
                    for line in summary.split("\n"):
                        if "Relevant notes for LLM:" in line:
                            try:
                                notes_count = int(line.split(":")[-1].strip())
                            except:
                                pass
                elif s.get("agent") == "SignalExtractor":
                    if not notes_count and "num_notes" in s:
                        notes_count = s.get("num_notes", 0)
                    if s.get("mode") == "re-extraction":
                        re_extractions += 1
                elif s.get("agent") == "Critic":
                    critic_rounds = max(critic_rounds, s.get("round", 1))

            records.append({
                "grid": grid,
                "diagnosis": dx,
                "confidence": conf,
                "time_s": t,
                "notes": notes_count,
                "critic_rounds": critic_rounds,
                "re_extractions": re_extractions,
            })
    except Exception as e:
        print(f"Error loading {f}: {e}")

# Save summarized json
with open("cohort_stats.json", "w") as fp:
    json.dump(records, fp, indent=2)

print("Saved cohort_stats.json")
