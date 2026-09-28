import os
import json
import statistics
import math

# Load cohort_stats.json
with open("cohort_stats.json", "r", encoding="utf-8") as f:
    cohort_stats = json.load(f)

# Also load full json results for rich details
json_dir = "results/stuttering_parallel/json_results"

full_records = {}
for p in os.listdir(json_dir):
    if p.endswith(".json"):
        grid = p.replace(".json", "")
        with open(os.path.join(json_dir, p), "r", encoding="utf-8") as f:
            full_records[grid] = json.load(f)

print(f"Total cohort_stats: {len(cohort_stats)}, Total full_records: {len(full_records)}")

def percentile(data, p):
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    d0 = s[int(f)] * (c - k)
    d1 = s[int(c)] * (k - f)
    return d0 + d1

# Merge data
records = []
for item in cohort_stats:
    grid = item["grid"]
    full = full_records.get(grid, {})
    item["reasoning"] = full.get("reasoning", "")
    item["evidence"] = full.get("evidence", [])
    item["criteria_met"] = full.get("criteria_met", {})
    item["signals"] = full.get("signals", {})
    records.append(item)

# 1. Phenotype Distribution
phenotypes = {}
confidences = {}
timings = []
notes_counts = []
critic_rounds = []
re_extractions = []

positive_features = {
    "slp_eval": 0,
    "ssi_score": 0,
    "therapy": 0,
    "group_therapy": 0,
    "oases": 0
}

for r in records:
    dx = r["diagnosis"]
    conf = r["confidence"]
    t = r["time_s"]
    notes = r["notes"]
    rounds = r["critic_rounds"]
    re_ex = r["re_extractions"]
    
    phenotypes[dx] = phenotypes.get(dx, 0) + 1
    if dx not in confidences:
        confidences[dx] = []
    confidences[dx].append(conf)
    
    timings.append(t)
    notes_counts.append(notes)
    critic_rounds.append(rounds)
    re_extractions.append(re_ex)
    
    if dx == "Positive":
        crit = r.get("criteria_met") or {}
        reasoning = (r.get("reasoning") or "").lower()
        signals_text = json.dumps(r.get("signals") or {}).lower()
        evidence_text = json.dumps(r.get("evidence") or []).lower()
        full_text = reasoning + " " + signals_text + " " + evidence_text
        
        if crit.get("slp_evaluated") or "ccc-slp" in full_text or "speech-language pathologist" in full_text or "slp" in full_text:
            positive_features["slp_eval"] += 1
        if crit.get("standardized_test_administered") or "ssi-3" in full_text or "ssi-4" in full_text or "ssi" in full_text or "%ss" in full_text:
            positive_features["ssi_score"] += 1
        if crit.get("speech_therapy_enrolled") or "therapy" in full_text or "treatment" in full_text:
            positive_features["therapy"] += 1
        if "group" in full_text or "parent-child" in full_text:
            positive_features["group_therapy"] += 1
        if "oases" in full_text:
            positive_features["oases"] += 1

print("\n--- PHENOTYPE DISTRIBUTION ---")
for dx, count in sorted(phenotypes.items(), key=lambda x: x[1], reverse=True):
    pct = count / len(records) * 100
    mean_conf = statistics.mean(confidences[dx])
    min_conf = min(confidences[dx])
    max_conf = max(confidences[dx])
    med_conf = statistics.median(confidences[dx])
    print(f"{dx}: {count} ({pct:.2f}%) | Conf: mean={mean_conf:.3f}, med={med_conf:.2f}, min={min_conf:.2f}, max={max_conf:.2f}")

print("\n--- POSITIVE CLINICAL CHARACTERISTICS ---")
pos_total = phenotypes.get("Positive", 0)
for k, v in positive_features.items():
    print(f"{k}: {v} / {pos_total} ({v/pos_total*100:.1f}%)")

print("\n--- OVERALL TIMING ANALYSIS ---")
print(f"Total Cohort Time: {sum(timings):.1f} s ({sum(timings)/3600:.2f} hours)")
print(f"Mean Time: {statistics.mean(timings):.1f} s ({statistics.mean(timings)/60:.2f} min)")
print(f"Median Time (P50): {statistics.median(timings):.1f} s ({statistics.median(timings)/60:.2f} min)")
print(f"Std Time: {statistics.stdev(timings):.1f} s")
print(f"Min Time: {min(timings):.1f} s")
print(f"P25 Time: {percentile(timings, 25):.1f} s ({percentile(timings, 25)/60:.2f} min)")
print(f"P50 Time: {percentile(timings, 50):.1f} s ({percentile(timings, 50)/60:.2f} min)")
print(f"P75 Time: {percentile(timings, 75):.1f} s ({percentile(timings, 75)/60:.2f} min)")
print(f"P90 Time: {percentile(timings, 90):.1f} s ({percentile(timings, 90)/60:.2f} min)")
print(f"P95 Time: {percentile(timings, 95):.1f} s ({percentile(timings, 95)/60:.2f} min)")
print(f"P99 Time: {percentile(timings, 99):.1f} s ({percentile(timings, 99)/60:.2f} min)")
print(f"Max Time: {max(timings):.1f} s ({max(timings)/3600:.2f} hours)")

print("\n--- NOTES DISTRIBUTION ---")
print(f"Total Notes Analyzed: {sum(notes_counts)}")
print(f"Mean Notes: {statistics.mean(notes_counts):.1f}")
print(f"Median Notes: {statistics.median(notes_counts):.1f}")
print(f"Min Notes: {min(notes_counts)}")
print(f"Max Notes: {max(notes_counts)}")
print(f"P25 Notes: {percentile(notes_counts, 25):.1f}")
print(f"P75 Notes: {percentile(notes_counts, 75):.1f}")
print(f"P90 Notes: {percentile(notes_counts, 90):.1f}")
print(f"P95 Notes: {percentile(notes_counts, 95):.1f}")
print(f"P99 Notes: {percentile(notes_counts, 99):.1f}")

# Sort by time
sorted_by_time = sorted(records, key=lambda x: x["time_s"], reverse=True)
slow_20 = sorted_by_time[:20]
fast_rest = sorted_by_time[20:]

slow_20_time = sum(p["time_s"] for p in slow_20)
fast_rest_time = sum(p["time_s"] for p in fast_rest)
print(f"\n--- TOP 20 SLOWEST VS REST 1,112 ---")
print(f"Slowest 20 Total Time: {slow_20_time:.1f}s ({slow_20_time/3600:.2f}h) -> {slow_20_time/sum(timings)*100:.1f}% of total cohort time!")
print(f"Slowest 20 Mean Time: {statistics.mean([p['time_s'] for p in slow_20]):.1f}s ({statistics.mean([p['time_s'] for p in slow_20])/3600:.2f}h)")
print(f"Slowest 20 Median Time: {statistics.median([p['time_s'] for p in slow_20]):.1f}s ({statistics.median([p['time_s'] for p in slow_20])/3600:.2f}h)")
print(f"Slowest 20 Mean Notes: {statistics.mean([p['notes'] for p in slow_20]):.1f}")
print(f"Slowest 20 Median Notes: {statistics.median([p['notes'] for p in slow_20]):.1f}")

print(f"\nRest 1,112 Total Time: {fast_rest_time:.1f}s ({fast_rest_time/3600:.2f}h) -> {fast_rest_time/sum(timings)*100:.1f}% of total cohort time")
print(f"Rest 1,112 Mean Time: {statistics.mean([p['time_s'] for p in fast_rest]):.1f}s ({statistics.mean([p['time_s'] for p in fast_rest])/60:.2f} min)")
print(f"Rest 1,112 Median Time: {statistics.median([p['time_s'] for p in fast_rest]):.1f}s ({statistics.median([p['time_s'] for p in fast_rest])/60:.2f} min)")
print(f"Rest 1,112 Mean Notes: {statistics.mean([p['notes'] for p in fast_rest]):.1f}")
print(f"Rest 1,112 Median Notes: {statistics.median([p['notes'] for p in fast_rest]):.1f}")

# Time per note analysis
time_per_note = [r["time_s"] / max(r["notes"], 1) for r in records if r["notes"] > 0]
print(f"\n--- TIME PER NOTE (for patients with notes > 0) ---")
print(f"Mean Time per Note: {statistics.mean(time_per_note):.2f} s")
print(f"Median Time per Note: {statistics.median(time_per_note):.2f} s")
print(f"P75 Time per Note: {percentile(time_per_note, 75):.2f} s")
print(f"P90 Time per Note: {percentile(time_per_note, 90):.2f} s")

# Re-extraction stats
re_ex_patients = [r for r in records if r["re_extractions"] > 0]
print(f"\n--- RE-EXTRACTIONS ---")
print(f"Patients requiring re-extraction: {len(re_ex_patients)} ({len(re_ex_patients)/len(records)*100:.2f}%)")
if re_ex_patients:
    print(f"Re-extracted patients mean time: {statistics.mean([p['time_s'] for p in re_ex_patients]):.1f}s ({statistics.mean([p['time_s'] for p in re_ex_patients])/60:.2f} min)")
    print(f"Non-re-extracted patients mean time: {statistics.mean([p['time_s'] for p in records if p['re_extractions'] == 0]):.1f}s ({statistics.mean([p['time_s'] for p in records if p['re_extractions'] == 0])/60:.2f} min)")

# Check the 11 Negative patients
negatives = [r for r in records if r["diagnosis"] == "Negative"]
print(f"\n--- ALL 11 NEGATIVE PATIENTS ---")
for n in sorted(negatives, key=lambda x: x["grid"]):
    print(f"{n['grid']} | Notes: {n['notes']} | Time: {n['time_s']:.1f}s | Reasoning snippet: {n['reasoning'][:120]}...")

# Check the 6 Excluded patients
excluded = [r for r in records if r["diagnosis"] == "Excluded"]
print(f"\n--- ALL 6 EXCLUDED PATIENTS ---")
for e in sorted(excluded, key=lambda x: x["grid"]):
    print(e["grid"], f"Notes: {e['notes']}", f"Time: {e['time_s']:.1f}s", f"Reasoning: {e['reasoning'][:100]}...")

# Save detailed analysis
with open("detailed_cohort_analysis.json", "w", encoding="utf-8") as fp:
    json.dump({
        "total_patients": len(records),
        "phenotypes": phenotypes,
        "confidences": {k: {"mean": statistics.mean(v), "median": statistics.median(v), "min": min(v), "max": max(v)} for k, v in confidences.items()},
        "positive_features": positive_features,
        "overall_timing": {
            "total_hours": sum(timings)/3600,
            "mean_s": statistics.mean(timings),
            "median_s": statistics.median(timings),
            "p25_s": percentile(timings, 25),
            "p75_s": percentile(timings, 75),
            "p90_s": percentile(timings, 90),
            "p95_s": percentile(timings, 95),
            "p99_s": percentile(timings, 99),
            "max_hours": max(timings)/3600
        },
        "notes_distribution": {
            "total_notes": sum(notes_counts),
            "mean_notes": statistics.mean(notes_counts),
            "median_notes": statistics.median(notes_counts),
            "p25_notes": percentile(notes_counts, 25),
            "p75_notes": percentile(notes_counts, 75),
            "p90_notes": percentile(notes_counts, 90),
            "p95_notes": percentile(notes_counts, 95),
            "p99_notes": percentile(notes_counts, 99),
            "max_notes": max(notes_counts)
        },
        "slowest_20": slow_20,
        "negatives": negatives,
        "excluded": excluded
    }, fp, indent=2)

print("\nSaved detailed_cohort_analysis.json")
