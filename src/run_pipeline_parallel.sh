#!/bin/bash

# Configuration
EXP_NAME="controls_151"
OUT_DIR="results/${EXP_NAME}"
JSON_DIR="${OUT_DIR}/json_results"
SUMMARY_DIR="${OUT_DIR}/summary"
CSV_FILE="${OUT_DIR}/${EXP_NAME}_results.csv"
GPU1_IP="10.151.30.251"


echo "Creating output directories..."
mkdir -p "$JSON_DIR"
mkdir -p "$SUMMARY_DIR"

echo "Setting up background port forwarding..."
# You must configure passwordless SSH or replace 'node1' and 'node2' with actual aliases

ssh -N -f -L 11435:localhost:11434 biand@$GPU1_IP || echo "Port 11435 already forwarded or SSH failed."
# ssh -N -f -L 11436:localhost:11434 biand@10.151.30.80 || echo "Port 11436 already forwarded or SSH failed."

echo "Starting Shard 1/2 on Remote GPU 1 (port 11435)..."
uv run python src/pheno_agent/pipeline.py \
    --grids-from-file "/home/biand/Projects/Celiac_BioVU/data/controls_need_review.csv" \
    --shard 1 \
    --shard-total 2 \
    --ollama-url "http://localhost:11435" \
    --output-dir "$JSON_DIR" \
    --output-csv "${OUT_DIR}/shard1_results.csv" \
    > "$OUT_DIR/shard1.log" 2>&1 &
PID1=$!

# echo "Starting Shard 2/3 on Remote GPU 2 (port 11436)..."
# uv run python src/celiac_agent/pipeline.py \
#     --grids-from-file "data/controls_need_review.csv" \
#     --shard 2 \
#     --shard-total 3 \
#     --ollama-url "http://localhost:11436" \
#     --output-dir "$JSON_DIR" \
#     --output-csv "${OUT_DIR}/shard2_results.csv" \
#     > "$OUT_DIR/shard2.log" 2>&1 &
# PID2=$!

echo "Starting Shard 2/2 on Local GPU (port 11434)..."
uv run python src/pheno_agent/pipeline.py \
    --grids-from-file "/home/biand/Projects/Celiac_BioVU/data/controls_need_review.csv" \
    --shard 2 \
    --shard-total 2 \
    --use-local-ollama \
    --output-dir "$JSON_DIR" \
    --output-csv "${OUT_DIR}/shard2_results.csv" \
    > "$OUT_DIR/shard2.log" 2>&1 &
PID2=$!

echo "All 2 shards started in the background!"
echo "PID for Remote GPU 1 process: $PID1"
echo "PID for Local GPU process:  $PID2"
echo ""
echo "You can monitor their progress by running:"
echo "tail -f $OUT_DIR/shard1.log $OUT_DIR/shard2.log"
echo ""

echo "Waiting for all shards to finish before generating the evaluation report..."
wait $PID1
wait $PID2

echo "Consolidating all shard results into $CSV_FILE..."
uv run python -c "
import glob, json, os, pandas as pd
json_dir = '${JSON_DIR}'
csv_file = '${CSV_FILE}'
json_files = sorted(glob.glob(os.path.join(json_dir, '*.json')))
records = []
for jf in json_files:
    with open(jf, 'r') as f:
        d = json.load(f)
    evidence_str = '; '.join(d.get('evidence', [])[:5]) if isinstance(d.get('evidence'), list) else str(d.get('evidence', ''))
    records.append({
        'grid': d.get('grid'),
        'diagnosis': d.get('diagnosis'),
        'confidence': d.get('confidence'),
        'reasoning': d.get('reasoning', ''),
        'evidence': evidence_str,
        'decision_path': d.get('decision_path', ''),
        'lab_decision': d.get('lab_decision', ''),
        'time_taken_s': d.get('time_taken_s', 0.0)
    })
df = pd.DataFrame(records).sort_values(by='grid').reset_index(drop=True)
df.to_csv(csv_file, index=False)
print(f'Consolidated {len(df)} records into {csv_file}')
"

echo "All shards finished. Generating Evaluation Report and Confusion Matrix..."
uv run python src/generate_eval_report.py \
    --res_dir "$JSON_DIR" \
    --out_file "${SUMMARY_DIR}/evaluation_report.md"

echo "Pipeline complete! Results saved in $OUT_DIR"
