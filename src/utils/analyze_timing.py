import os
import glob
import math

json_dir = "results/stuttering_parallel/json_results"
ehr_dir = "data/stuttering/ehr_markdown_dataset"
all_ehr = sorted([f.replace(".md", "") for f in os.listdir(ehr_dir) if f.endswith(".md")])

print(f"Total EHR patients: {len(all_ehr)}")
chunk_size = math.ceil(len(all_ehr) / 2)
shard1_grids = all_ehr[:chunk_size]
shard2_grids = all_ehr[chunk_size:]

done_grids = set(f.replace(".json", "") for f in os.listdir(json_dir) if f.endswith(".json"))
pending_shard1 = [g for g in shard1_grids if g not in done_grids]
pending_shard2 = [g for g in shard2_grids if g not in done_grids]

print(f"Pending Shard 1 ({len(pending_shard1)}): {pending_shard1}")
print(f"Pending Shard 2 ({len(pending_shard2)}): {pending_shard2}")
