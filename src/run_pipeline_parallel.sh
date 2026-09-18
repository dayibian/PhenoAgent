#!/bin/bash
# ==============================================================================
# run_pipeline_parallel.sh — Parallel Multi-GPU Stuttering Phenotyping Pipeline
# ==============================================================================
# Usage:
#   # Run across all patients discovered in dataset/ChromaDB:
#   ./src/run_pipeline_parallel.sh
#
#   # Run with custom experiment name on all patients:
#   ./src/run_pipeline_parallel.sh stuttering_full
#
#   # Run on a specific patient list CSV/Excel file:
#   ./src/run_pipeline_parallel.sh stuttering_cohort data/stuttering/patients.csv
#
#   # Run with ground truth evaluation file:
#   ./src/run_pipeline_parallel.sh stuttering_eval data/stuttering/patients.csv data/stuttering/ground_truth.csv
# ==============================================================================

set -e

# Configuration
EXP_NAME="${1:-stuttering_parallel}"
OUT_DIR="results/${EXP_NAME}"
JSON_DIR="${OUT_DIR}/json_results"
SUMMARY_DIR="${OUT_DIR}/summary"
CSV_FILE="${OUT_DIR}/${EXP_NAME}_results.csv"
GPU1_IP="10.151.30.251"

# Patient Input Resolution:
# $2 can be a file path, "--all", or empty (defaults to --all)
INPUT_ARG="${2:-}"
GT_PATH="${3:-}"
EXTRA_SAMPLE="${SAMPLE_SIZE:-}"

PATIENT_FLAGS="--all"
if [ "$INPUT_ARG" == "--all" ] || [ -z "$INPUT_ARG" ]; then
    PATIENT_FLAGS="--all"
    echo "Processing ALL patients from dataset / ChromaDB."
elif [ -f "$INPUT_ARG" ]; then
    PATIENT_FLAGS="--grids-from-file $INPUT_ARG"
    echo "Processing patients from file: $INPUT_ARG"
else
    echo "Warning: Patient input '$INPUT_ARG' not found as a file. Falling back to --all."
    PATIENT_FLAGS="--all"
fi

if [ -n "$EXTRA_SAMPLE" ]; then
    PATIENT_FLAGS="$PATIENT_FLAGS --sample $EXTRA_SAMPLE"
    echo "Sample limit applied: first $EXTRA_SAMPLE patients."
fi

echo "Creating output directories..."
mkdir -p "$JSON_DIR"
mkdir -p "$SUMMARY_DIR"

echo "Setting up background port forwarding to Remote GPU 1..."
ssh -N -f -L 11435:localhost:11434 biand@$GPU1_IP || echo "Port 11435 already forwarded or SSH failed."

echo "Starting Shard 1/2 on Remote GPU 1 (port 11435)..."
uv run python src/pheno_agent/pipeline.py \
    $PATIENT_FLAGS \
    --shard 1 \
    --shard-total 2 \
    --ollama-url "http://localhost:11435" \
    --output-dir "$JSON_DIR" \
    --output-csv "${OUT_DIR}/shard1_results.csv" \
    > "$OUT_DIR/shard1.log" 2>&1 &
PID1=$!

echo "Starting Shard 2/2 on Local GPU (port 11434)..."
uv run python src/pheno_agent/pipeline.py \
    $PATIENT_FLAGS \
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
echo "You can monitor live progress by running:"
echo "tail -f $OUT_DIR/shard1.log $OUT_DIR/shard2.log"
echo ""

echo "Waiting for all shards to finish..."
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
    with open(jf, 'r', encoding='utf-8') as f:
        try:
            d = json.load(f)
        except Exception:
            continue
    evidence_str = '; '.join(d.get('evidence', [])[:5]) if isinstance(d.get('evidence'), list) else str(d.get('evidence', ''))
    records.append({
        'grid': d.get('grid'),
        'diagnosis': d.get('diagnosis'),
        'confidence': d.get('confidence', 0.0),
        'reasoning': d.get('reasoning', ''),
        'evidence': evidence_str,
        'decision_path': d.get('decision_path', ''),
        'time_taken_s': d.get('time_taken_s', 0.0)
    })
if records:
    df = pd.DataFrame(records).sort_values(by='grid').reset_index(drop=True)
    df.to_csv(csv_file, index=False)
    print(f'Successfully consolidated {len(df)} patient records into {csv_file}')
else:
    print('Warning: No records found to consolidate.')
"

echo "Generating Stuttering Phenotyping Summary & Evaluation Report..."
EVAL_ARGS="--res_dir $JSON_DIR --out_file ${SUMMARY_DIR}/evaluation_report.md --phenotype Stuttering"
if [ -n "$GT_PATH" ] && [ -f "$GT_PATH" ]; then
    EVAL_ARGS="$EVAL_ARGS --gt_path $GT_PATH"
fi

uv run python src/generate_eval_report.py $EVAL_ARGS

echo "=============================================================================="
echo "Pipeline complete! Results saved in $OUT_DIR"
echo "  - Aggregated CSV: $CSV_FILE"
echo "  - Summary Report: ${SUMMARY_DIR}/evaluation_report.md"
echo "=============================================================================="

