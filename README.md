# 🧬 PhenoAgent (`pheno_agent`) — Stuttering Branch (`stutter_dev`)

This package implements a modular, **multi-agent clinical phenotyping system** that automates phenotype assignment from Electronic Health Records (EHR) using local LLM inference via Ollama.

> [!NOTE]
> This branch adapts PhenoAgent (originally built for celiac disease on `main`) to **developmental / persistent stuttering and speech disfluency**. Lab-value logic is disabled for this phenotype (`USE_LABS = False`); classification is driven entirely by clinical notes, a curated keyword lexicon, and clinician-authored phenotyping rules.

The framework combines:
* A **keyword lexicon** ([stuttering_keywords.yaml](data/stuttering/stuttering_keywords.yaml)) derived from Pruett et al. (2021) and Shaw et al. (2021).
* **Clinician phenotyping rules** ([stuttering_rules.md](data/stuttering/stuttering_rules.md)) with longitudinal synthesis.
* A **corrective reflection loop** between the Signal Extractor and Critic agents, with **targeted (delta) re-extraction** of only the flawed notes.

---

## 🎯 Phenotype Outcomes

Each patient is assigned one of four outcomes:

| Outcome | Meaning |
|---|---|
| **Positive** | Confirmed diagnosis, SLP / speech-therapy evaluation, standardized test (SSI, OASES, %SS), or affirmative developmental speech-disfluency documentation for the patient. |
| **Negative** | No stuttering signal, all mentions explicitly negated, or formally ruled out. |
| **Indeterminate** | Ambiguous mention or query (e.g. *"mother asks about stuttering?"*) without clinical confirmation. |
| **Excluded** | Mentions are only non-speech jargon (*stuttering gait/angina/priapism/stroke*), family history only, or attributed solely to a competing psychiatric condition (psychosis, clanging). |

Longitudinal aggregation priority: **Positive > Indeterminate > Excluded > Negative**. A single confirmed pediatric / SLP diagnosis establishes Positive; later notes stating "speech fluent" do not override it.

---

## 📐 System Architecture & Data Flow

```text
  ┌─────────────────────┐   ┌───────────────────────┐   ┌────────────────────────┐
  │ EHR Markdown (.md)  │   │ ChromaDB (fallback /  │   │ stuttering_rules.md +  │
  │ ehr_markdown_dataset│   │ stuttering_notes)     │   │ stuttering_keywords.yaml│
  └─────────┬───────────┘   └──────────┬────────────┘   └───────────┬────────────┘
            │ (ehr_reader.py)          │ (chroma_retriever.py)      │
            ▼                          ▼                            │
  ┌──────────────────────────────────────────────┐                  │
  │              DataGatherer Agent              │                  │
  │  keyword_scanner.py → select relevant notes  │ ◄────────────────┤
  │  (drops routine "Speech: clear" templates)   │                  │
  └──────────────────────┬───────────────────────┘                  │
                         ▼                                          │
         ┌──────►┌────────────────┐                                 │
         │       │SignalExtractor │ ◄───────────────────────────────┤
  (Targeted      └───────┬────────┘                                 │
   re-extraction   (Raw Signals)                                    │
   of flawed notes)      ▼                                          │
         └───────┌────────────────┐                                 │
                 │  Critic Agent  │ ◄───────────────────────────────┤
                 └───────┬────────┘                                 │
                 (Verified Signals)                                 │
                         ▼                                          │
                 ┌────────────────┐                                 │
                 │  Adjudicator   │ ◄───────────────────────────────┘
                 └───────┬────────┘
                         ▼
     [ Per-patient JSON + aggregated CSV + evaluation report ]
```

---

## 📂 Directory Structure

```text
PhenoAgent/
├── pyproject.toml                 # Project configuration & dependencies
├── README.md                      # This file
├── data/stuttering/               # (data files are git-ignored except .yaml / .md)
│   ├── stuttering_keywords.yaml   # Keyword lexicon (primary, confirmatory, SLP, negation, FH, exclusions…)
│   ├── stuttering_rules.md        # Clinician phenotyping & longitudinal synthesis rules
│   ├── stuttering_case_notes.csv  # Raw case notes (input to ingestion)
│   ├── stuttering_control_notes.csv
│   ├── ehr_markdown_dataset/      # Generated per-patient {grid}.md files
│   ├── rag_chunks.csv             # Generated sliding-window chunks
│   └── chroma_db/                 # Persistent ChromaDB store (collection: stuttering_notes)
├── docs/                          # Manuscript outline & technical reports
├── notebooks/stuttering.ipynb     # Exploratory analysis
├── tests/
│   ├── test_ingest_stuttering.py
│   └── test_pheno_agent_stuttering.py
└── src/
    ├── run_pipeline_parallel.sh   # 2-shard parallel runner (remote + local GPU)
    ├── pheno_agent/
    │   ├── config.py              # Phenotype, paths, models, agent parameters
    │   ├── llm.py                 # Ollama wrapper (Outlines structured output, JSON repair, retries)
    │   ├── orchestrator.py        # Per-patient flow incl. targeted delta re-extraction
    │   ├── pipeline.py            # CLI entry point, aggregation, evaluation
    │   ├── agents/
    │   │   ├── data_gatherer.py   # Loads notes (EHR md → ChromaDB fallback), selects relevant notes
    │   │   ├── signal_extractor.py# LLM extraction of stuttering signals per note
    │   │   ├── critic.py          # Quote verification + keyword/LLM consistency checks
    │   │   └── adjudicator.py     # Deterministic decision table + LLM rationale
    │   └── tools/
    │       ├── chroma_retriever.py# BioClinicalBERT retrieval + full-patient chunk reconstruction
    │       ├── ehr_reader.py      # EHR Markdown parser
    │       ├── keyword_scanner.py # YAML-driven stuttering keyword / negation / context scanner
    │       └── lab_lookup.py      # Lab evaluator (inactive when USE_LABS = False)
    └── utils/                     # Ingestion, evaluation, and expert-review helpers (see below)
```

---

## 🤖 Agent Personas

### 1. DataGatherer
* **Type**: Deterministic heuristics
* **Role**: Loads the patient's notes from `ehr_markdown_dataset/{grid}.md`, falling back to reconstructing notes from ChromaDB chunks if no Markdown file exists. Runs the keyword scanner and selects notes with primary, SLP / formal-assessment, confirmatory, or speech-context hits. Routine normal speech-exam templates (e.g. `Speech: clear`) are dropped. If no signal is found, all notes are sent for small records (≤ 30 notes); larger records are sampled (first 10, middle 10, last 10).

### 2. SignalExtractor
* **Type**: LLM-based (`qwen3.6:35b-a3b` by default)
* **Role**: Reads selected notes in dynamically sized, concurrent batches and extracts per-note signals:
  * `stuttering_mentioned` (bool)
  * `speech_context`: `speech` / `non_speech` / `not_found`
  * `subject_attribution`: `patient` / `family_only` / `unknown`
  * `assertion`: `affirmative` / `negated` / `ruled_out` / `ambiguous` / `not_found`
  * `slp_or_formal_assessment` (bool)
  * `competing_condition` (bool)
  * `supporting_quotes`

### 3. Critic
* **Type**: Hybrid (deterministic + LLM `qwen3.8:27b` by default)
* **Role**:
  * **Quote verification**: Fuzzy-matches quotes against the raw note and removes phantom quotes. Notes that claim affirmative stuttering with no valid quote are flagged.
  * **Consistency check**: Compares LLM signals with keyword-scanner hits (non-speech exclusions, family history, negation, SLP / assessment, competing conditions). It also re-checks affirmative claims with uncertain context or attribution. Corrections are applied in place.
  * Falls back to raw-JSON parsing if structured output fails. Only notes that remain unresolved go back for **targeted re-extraction**.

### 4. Adjudicator
* **Type**: Hybrid (deterministic decision table + LLM `qwen3.8:27b` by default)
* **Role**: Applies the per-note decision table (priority order below), aggregates decisions across the patient's history, and has the LLM write a 2–4 sentence, citation-backed rationale.
  1. Non-speech context → Excluded
  2. Family history only → Excluded
  3. Competing psychiatric condition → Excluded
  4. Negated / ruled out → Negative
  5. Affirmative + SLP / formal assessment → Positive
  6. Affirmative + speech context → Positive
  7. Ambiguous / query only → Indeterminate
  8. No signal → Negative

---

## ⚙️ Installation & Setup

### 1. Prerequisites
* **Python** `3.10+` (verified up to `3.12`)
* **uv** package manager:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
* **Ollama** ([ollama.com](https://ollama.com/)) for local LLM inference.

### 2. Environment Setup
```bash
cd PhenoAgent
uv sync
```

### 3. Model Provisioning
```bash
ollama serve
ollama pull qwen3.6:35b-a3b   # extraction + fast model
ollama pull qwen3.8:27b       # reasoning model (Critic, Adjudicator)
```

> [!NOTE]
> Override models with `--reasoning-model`, `--extraction-model`, `--fast-model`, or edit `ModelConfig` in [config.py](src/pheno_agent/config.py).

### 4. Ollama Connection
By default `use_remote_ollama = True`, which targets `http://localhost:11435`, an SSH tunnel to a remote GPU:
```bash
ssh -N -f -L 11435:localhost:11434 <user>@<gpu-host>
```
Pass `--use-local-ollama` to use `http://localhost:11434`, or `--ollama-url <url>` for any other endpoint.

### 5. Data Configuration
All paths are derived from `PROJECT_ROOT` in [config.py](src/pheno_agent/config.py). By default `DATA_DIR = data/stuttering`. Key settings:

| Setting | Default |
|---|---|
| `PHENOTYPE` / `USE_LABS` | `stuttering` / `False` |
| `KEYWORDS_PATH` | `data/stuttering/stuttering_keywords.yaml` |
| `DIAGNOSIS_LOGIC_PATH` | `data/stuttering/stuttering_rules.md` |
| `EHR_MARKDOWN_DIR` | `data/stuttering/ehr_markdown_dataset/` |
| `CHROMA_DB_PATH` / collection | `data/stuttering/chroma_db/` / `stuttering_notes` |
| `EMBED_MODEL` | local `Bio_ClinicalBERT` if present, else `emilyalsentzer/Bio_ClinicalBERT` |
| Output | `results/stuttering/json_results/`, `results/stuttering_results.csv` |

---

## 📥 Data Ingestion

Before running the pipeline, build the EHR Markdown dataset and ChromaDB store from the raw notes CSVs.

```bash
# Case cohort: filter notes → markdown → chunks → ChromaDB (all steps)
uv run python src/utils/ingest_stuttering.py --step all

# Quick test on a subset
uv run python src/utils/ingest_stuttering.py --step all --sample-patients 10

# Individual steps
uv run python src/utils/ingest_stuttering.py --step markdown
uv run python src/utils/ingest_stuttering.py --step prep-chunks
uv run python src/utils/ingest_stuttering.py --step chroma

# Synthetic self-test
uv run python src/utils/ingest_stuttering.py --test

# Control cohort (appends to the same markdown dir, chunks CSV, and collection)
uv run python src/utils/ingest_control_cohort.py
```

Useful flags: `--no-filter` (keep all notes), `--reset` (wipe collection / markdown dir), `--chunk-size` (default 1500), `--chunk-overlap`, `--limit-rows`.

---

## 🛠 Running the Pipeline

### Single patient
```bash
uv run python src/pheno_agent/pipeline.py --grids R201643869 --use-local-ollama
```

### Patients from a file (CSV / Excel)
```bash
uv run python src/pheno_agent/pipeline.py \
  --grids-from-file data/stuttering/control_patient_grids.csv \
  --sample 10 \
  --use-local-ollama
```

### All patients (EHR Markdown dir / ChromaDB)
```bash
uv run python src/pheno_agent/pipeline.py --all --use-local-ollama
```

### Evaluate against ground truth
```bash
uv run python src/pheno_agent/pipeline.py \
  --grids-from-file data/stuttering/patients.csv \
  --evaluate --ground-truth data/stuttering/ground_truth.csv \
  --use-local-ollama
```
Ground truth may be CSV or Excel. The label column is auto-detected (`diagnosis` / `label` / `status` / `phenotype`). Values such as `case`/`control`/`excluded` are normalized to the four outcomes.

### Parallel multi-GPU run
[run_pipeline_parallel.sh](src/run_pipeline_parallel.sh) splits patients into 2 shards: one on a remote GPU (port 11435) and one on the local GPU. It then merges the JSON results into a CSV and writes an evaluation report.
```bash
./src/run_pipeline_parallel.sh                                   # all patients, exp "stuttering_parallel"
./src/run_pipeline_parallel.sh stuttering_full                   # custom experiment name
./src/run_pipeline_parallel.sh stuttering_cohort patients.csv    # patient list
./src/run_pipeline_parallel.sh stuttering_eval patients.csv gt.csv
SAMPLE_SIZE=20 ./src/run_pipeline_parallel.sh stuttering_smoke   # limit patients
```
Outputs go to `results/<exp>/`: `json_results/`, `<exp>_results.csv`, `summary/evaluation_report.md`, and `shard*.log`.

### Other CLI options
| Flag | Purpose |
|---|---|
| `--shard N --shard-total M` | Process a slice of patients |
| `--max-reflections N` | Extractor ↔ Critic loops (default 2) |
| `--no-chroma` | Skip ChromaDB retrieval |
| `--no-resume` | Re-process patients that already have results |
| `--output-dir`, `--output-csv` | Custom output locations |

---

## 🧰 Utility Scripts (`src/utils/`)

| Category | Scripts |
|---|---|
| Ingestion | `ingest_stuttering.py`, `ingest_control_cohort.py` |
| Evaluation & stats | `generate_eval_report.py` (`--res_dir`, `--out_file`, `--gt_path`, `--phenotype`), `analyze_full_results.py`, `analyze_timing.py`, `analyze_fps.py`, `extract_cohort_stats.py` |
| Expert review exports | `extract_snippets.py`, `generate_expert_review_docx.py`, `generate_expert_review_md.py`, `generate_individual_patient_docx.py`, `docx_helpers.py` |
| Inspection / debugging | `inspect_*.py`, `check_*.py`, `verify_all_17_notes.py`, `test_parse_ehr_notes.py` |

---

## 🧪 Tests

```bash
uv run pytest tests/
```

---

## 🧬 Domain-Specific Heuristics
* **Non-speech exclusion**: Medical uses of "stuttering" (gait, angina, priapism, myocardial ischemia, stroke/infarct) are excluded.
* **Subject attribution**: Mentions found only in family history (e.g. *"father stutters"*) are excluded.
* **Negation & rule-out**: Phrases such as *"denies stuttering"* or *"speech fluent without stutter"* are treated as Negative.
* **Formal assessment boost**: SLP involvement, speech therapy, SSI / OASES, and %SS count as strong positive evidence.
* **Competing conditions**: Disfluency attributed solely to psychosis, formal thought disorder, mania, or clanging is excluded.
* **Longitudinal synthesis**: Developmental onset is typically ages 2–6, and a confirmed early diagnosis persists across later normal-speech notes.
* **Hallucination guard**: Affirmative claims without a verifiable quote trigger targeted re-extraction.
