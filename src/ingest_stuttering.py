"""
ingest_stuttering.py
--------------------
Ingestion and preprocessing pipeline for stuttering clinical notes.

Mirrors the workflow from Celiac BioVU (curate_dataset.py, rag_data_prep.py, rag_ingest.py):
  1. Filters and cleans clinical notes from stuttering_case_notes.csv using stuttering_keywords.yaml.
  2. Generates patient EHR markdown files at data/stuttering/ehr_markdown_dataset/{grid}.md.
  3. Chunks notes into sliding-window text segments saved at data/stuttering/rag_chunks.csv.
  4. Embeds chunks via BioClinicalBERT and upserts them into a persistent ChromaDB vector store
     at data/stuttering/chroma_db/ (collection: stuttering_notes).

Usage Examples:
  # Full pipeline on entire dataset:
  uv run python src/ingest_stuttering.py --step all

  # Test run on first 10 patients:
  uv run python src/ingest_stuttering.py --step all --sample-patients 10

  # Test run on first 5,000 rows of the CSV:
  uv run python src/ingest_stuttering.py --step all --limit-rows 5000

  # Individual steps:
  uv run python src/ingest_stuttering.py --step markdown
  uv run python src/ingest_stuttering.py --step prep-chunks
  uv run python src/ingest_stuttering.py --step chroma

  # Run automated self-test (dry-run on synthetic data):
  uv run python src/ingest_stuttering.py --test
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple

import pandas as pd
import yaml
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ingest_stuttering")

# ---------------------------------------------------------------------------
# Default Paths and Parameters
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STUTTERING_DATA_DIR = PROJECT_ROOT / "data" / "stuttering"

DEFAULT_NOTES_PATH = STUTTERING_DATA_DIR / "stuttering_case_notes.csv"
DEFAULT_KEYWORDS_PATH = STUTTERING_DATA_DIR / "stuttering_keywords.yaml"
DEFAULT_EHR_DIR = STUTTERING_DATA_DIR / "ehr_markdown_dataset"
DEFAULT_CHUNKS_PATH = STUTTERING_DATA_DIR / "rag_chunks.csv"
DEFAULT_CHROMA_DB_PATH = STUTTERING_DATA_DIR / "chroma_db"
DEFAULT_COLLECTION_NAME = "stuttering_notes"

# Embedding model fallback hierarchy:
# 1. Local cached model in Celiac_BioVU
# 2. Hugging Face hub repository
LOCAL_MODEL_PATH = Path("/home/biand/Projects/Celiac_BioVU/models/Bio_ClinicalBERT")
HF_MODEL_NAME = "emilyalsentzer/Bio_ClinicalBERT"
DEFAULT_EMBED_MODEL = str(LOCAL_MODEL_PATH) if LOCAL_MODEL_PATH.exists() else HF_MODEL_NAME

CHUNK_SIZE = 1500      # characters per chunk
CHUNK_OVERLAP = 100    # overlap characters between consecutive chunks
STREAM_CHUNKSIZE = 10_000  # rows per pandas streaming chunk
EMBED_BATCH_SIZE = 64  # chunks per embedding batch


# ---------------------------------------------------------------------------
# Keywords Loading & Text Preprocessing
# ---------------------------------------------------------------------------

def load_keywords(keywords_path: Path) -> List[str]:
    """
    Load stuttering keywords from YAML file.
    Prefers 'popular_words' (matching Celiac pattern), but falls back
    to combining primary and confirmatory keywords if not present.
    """
    if not keywords_path.exists():
        logger.warning("Keywords file %s not found. Using empty keywords list.", keywords_path)
        return []

    with open(keywords_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    popular_words = data.get("popular_words", [])
    if popular_words:
        keywords = [str(kw).strip().lower() for kw in popular_words if str(kw).strip()]
    else:
        # Fallback to union of list fields in YAML
        keywords_set: Set[str] = set()
        for key in ("primary_keywords", "confirmatory_keywords", "diagnostic_tests_and_assessments", "slp_clinical_context"):
            items = data.get(key, [])
            if isinstance(items, list):
                for item in items:
                    val = str(item).strip().lower()
                    if val:
                        keywords_set.add(val)
        keywords = sorted(list(keywords_set))

    logger.info("Loaded %d keywords from %s", len(keywords), keywords_path)
    return keywords


def clean_note_text(text: str) -> str:
    """
    Clean note text:
      - Normalize HTML tags (e.g. <br>) to newlines
      - Remove PHI bracket placeholders (e.g. [**DOCTOR**], [**DATE**])
      - Normalize horizontal whitespace and excessive blank lines
    """
    if not isinstance(text, str):
        text = str(text) if pd.notnull(text) else ""

    # Replace HTML break tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # Remove PHI placeholders like [** ... **]
    text = re.sub(r"\[\*\*.*?\*\*\]", " ", text)
    # Normalize tabs and multiple spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Condense 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_keyword_regex(keywords: List[str]) -> Optional[re.Pattern]:
    """Compile a case-insensitive regex pattern from the keywords list."""
    if not keywords:
        return None
    pattern_str = "|".join(re.escape(k) for k in keywords)
    return re.compile(pattern_str, re.IGNORECASE)


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping character-level chunks.
    Matches the sliding window logic from rag_data_prep.py.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


# ---------------------------------------------------------------------------
# EHR Markdown Generation
# ---------------------------------------------------------------------------

def create_markdown_for_grid(grid: str, notes_list: List[Dict]) -> str:
    """
    Build structured EHR Markdown for a single patient GRID.
    Complies with PhenoAgent's ehr_reader.py parsing expectations.
    """
    lines = [f"# Grid: {grid}", "", "## Labs", "No labs available.", "", "## Medical Notes"]

    if notes_list:
        # Sort chronologically by note_datetime
        sorted_notes = sorted(
            notes_list,
            key=lambda n: n.get("note_datetime_parsed") or pd.Timestamp.min,
        )
        for row in sorted_notes:
            date_str = row.get("date_str") or "Unknown Date"
            title = row.get("note_title") or "Untitled Note"
            source = row.get("note_source_value") or "Unknown Source"
            text = row.get("note_text") or ""

            lines.append(f"### [{date_str}] {title}")
            lines.append(f"**Source:** {source}")
            lines.append("")
            lines.append(text.strip())
            lines.append("")
    else:
        lines.append("No notes available.")

    return "\n".join(lines)


def generate_ehr_markdown_dataset(
    notes_path: Path = DEFAULT_NOTES_PATH,
    ehr_dir: Path = DEFAULT_EHR_DIR,
    keywords_path: Path = DEFAULT_KEYWORDS_PATH,
    sample_patients: Optional[int] = None,
    limit_rows: Optional[int] = None,
    filter_keywords: bool = True,
    stream_chunksize: int = STREAM_CHUNKSIZE,
    reset: bool = False,
) -> Dict[str, int]:
    """
    Stream the notes CSV, filter relevant notes, aggregate by patient GRID,
    and save individual Markdown files to ehr_dir/{grid}.md.
    """
    logger.info("=" * 60)
    logger.info("STEP: Generating EHR Markdown Dataset")
    logger.info("Notes source: %s", notes_path)
    logger.info("EHR output dir: %s", ehr_dir)
    logger.info("=" * 60)

    ehr_dir.mkdir(parents=True, exist_ok=True)
    if reset:
        logger.info("Reset requested: cleaning existing markdown files in %s...", ehr_dir)
        for f in ehr_dir.glob("*.md"):
            try:
                f.unlink()
            except Exception as e:
                logger.warning("Could not delete %s: %e", f, e)

    keywords = load_keywords(keywords_path)
    kw_regex = build_keyword_regex(keywords) if filter_keywords else None

    # Patient notes accumulation: grid -> list of note dicts
    patients_notes: Dict[str, List[Dict]] = {}
    seen_grids: Set[str] = set()
    total_rows_read = 0
    total_notes_kept = 0

    reader = pd.read_csv(
        notes_path,
        chunksize=stream_chunksize,
        low_memory=False,
        escapechar="\\",
        on_bad_lines="skip",
    )

    try:
        with tqdm(desc="Streaming notes for Markdown generation", unit="batch") as pbar:
            for batch in reader:
                # Column mapping: person_source_value -> grid
                grid_col = "grid" if "grid" in batch.columns else "person_source_value"
                if grid_col not in batch.columns:
                    raise ValueError(f"Neither 'grid' nor 'person_source_value' found in columns: {list(batch.columns)}")

                batch[grid_col] = batch[grid_col].astype(str).str.strip()
                batch["note_text"] = batch["note_text"].astype(str)

                # Optional keyword filtering
                if kw_regex is not None:
                    mask = batch["note_text"].str.contains(kw_regex, na=False)
                    filtered_batch = batch[mask].copy()
                else:
                    filtered_batch = batch.copy()

                for _, row in filtered_batch.iterrows():
                    grid = row[grid_col]
                    if not grid or grid == "nan":
                        continue

                    if sample_patients is not None and grid not in seen_grids and len(seen_grids) >= sample_patients:
                        continue

                    seen_grids.add(grid)
                    cleaned_text = clean_note_text(row.get("note_text", ""))
                    if not cleaned_text:
                        continue

                    raw_dt = row.get("note_datetime") or row.get("note_date")
                    parsed_dt = pd.to_datetime(raw_dt, errors="coerce", utc=True)
                    date_str = parsed_dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(parsed_dt) else "Unknown Date"

                    note_entry = {
                        "note_id": str(row.get("note_id", "")),
                        "note_datetime_parsed": parsed_dt,
                        "date_str": date_str,
                        "note_title": str(row.get("note_title", "Untitled Note")),
                        "note_source_value": str(row.get("note_source_value", "Unknown Source")),
                        "note_text": cleaned_text,
                    }

                    if grid not in patients_notes:
                        patients_notes[grid] = []
                    patients_notes[grid].append(note_entry)
                    total_notes_kept += 1

                total_rows_read += len(batch)
                pbar.update(1)
                pbar.set_postfix(rows=total_rows_read, patients=len(seen_grids), notes=total_notes_kept)

                if limit_rows is not None and total_rows_read >= limit_rows:
                    logger.info("Reached limit_rows=%d, stopping CSV read.", limit_rows)
                    break
                if sample_patients is not None and len(seen_grids) >= sample_patients:
                    logger.info("Reached sample_patients=%d, stopping CSV read.", sample_patients)
                    break
    finally:
        reader.close()

    # Write Markdown files
    logger.info("Writing %d patient EHR Markdown files to %s ...", len(patients_notes), ehr_dir)
    for grid, notes_list in tqdm(patients_notes.items(), desc="Writing Markdown files", unit="patient"):
        md_content = create_markdown_for_grid(grid, notes_list)
        out_file = ehr_dir / f"{grid}.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(md_content)

    summary = {
        "total_rows_read": total_rows_read,
        "patients_created": len(patients_notes),
        "notes_written": total_notes_kept,
    }
    logger.info("EHR Markdown generation complete. Summary: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# Note Chunking (rag_chunks.csv)
# ---------------------------------------------------------------------------

def prepare_chunks(
    notes_path: Path = DEFAULT_NOTES_PATH,
    output_path: Path = DEFAULT_CHUNKS_PATH,
    keywords_path: Path = DEFAULT_KEYWORDS_PATH,
    sample_patients: Optional[int] = None,
    limit_rows: Optional[int] = None,
    filter_keywords: bool = True,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    stream_chunksize: int = STREAM_CHUNKSIZE,
) -> pd.DataFrame:
    """
    Stream medical notes, clean, filter by keywords, split into overlapping chunks,
    and save to rag_chunks.csv.
    """
    logger.info("=" * 60)
    logger.info("STEP: Chunking Notes for Vector Store")
    logger.info("Notes source: %s", notes_path)
    logger.info("Chunks destination: %s", output_path)
    logger.info("Chunk size: %d, Overlap: %d", chunk_size, overlap)
    logger.info("=" * 60)

    keywords = load_keywords(keywords_path)
    kw_regex = build_keyword_regex(keywords) if filter_keywords else None

    all_chunks = []
    seen_grids: Set[str] = set()
    total_rows_read = 0
    chunk_counter = 0

    reader = pd.read_csv(
        notes_path,
        chunksize=stream_chunksize,
        low_memory=False,
        escapechar="\\",
        on_bad_lines="skip",
    )

    try:
        with tqdm(desc="Processing note batches into chunks", unit="batch") as pbar:
            for batch in reader:
                grid_col = "grid" if "grid" in batch.columns else "person_source_value"
                if grid_col not in batch.columns:
                    raise ValueError(f"Neither 'grid' nor 'person_source_value' found in columns: {list(batch.columns)}")

                batch[grid_col] = batch[grid_col].astype(str).str.strip()
                batch["note_text"] = batch["note_text"].astype(str)

                if kw_regex is not None:
                    mask = batch["note_text"].str.contains(kw_regex, na=False)
                    filtered_batch = batch[mask].copy()
                else:
                    filtered_batch = batch.copy()

                for _, row in filtered_batch.iterrows():
                    grid = row[grid_col]
                    if not grid or grid == "nan":
                        continue

                    if sample_patients is not None and grid not in seen_grids and len(seen_grids) >= sample_patients:
                        continue

                    seen_grids.add(grid)
                    cleaned = clean_note_text(row.get("note_text", ""))
                    if not cleaned:
                        continue

                    note_id = str(row.get("note_id", ""))
                    note_datetime = str(row.get("note_datetime", "") or row.get("note_date", ""))
                    note_type = str(row.get("note_title", "") or row.get("x_doc_type", "") or "Note")

                    chunks = split_into_chunks(cleaned, chunk_size=chunk_size, overlap=overlap)
                    for i, chunk_text in enumerate(chunks):
                        all_chunks.append({
                            "chunk_id": f"{grid}_{note_id}_{i}",
                            "grid": grid,
                            "note_id": note_id,
                            "note_datetime": note_datetime,
                            "note_type": note_type,
                            "chunk_text": chunk_text,
                        })
                        chunk_counter += 1

                total_rows_read += len(batch)
                pbar.update(1)
                pbar.set_postfix(rows=total_rows_read, patients=len(seen_grids), chunks=chunk_counter)

                if limit_rows is not None and total_rows_read >= limit_rows:
                    logger.info("Reached limit_rows=%d, stopping CSV read.", limit_rows)
                    break
                if sample_patients is not None and len(seen_grids) >= sample_patients:
                    logger.info("Reached sample_patients=%d, stopping CSV read.", sample_patients)
                    break
    finally:
        reader.close()

    df = pd.DataFrame(all_chunks)
    logger.info("Total generated chunks: %d from %d patients.", len(df), df["grid"].nunique() if not df.empty else 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("Chunks saved successfully to %s", output_path)
    return df


# ---------------------------------------------------------------------------
# BioClinicalBERT Model Loader & Embedder
# ---------------------------------------------------------------------------

_tokenizer = None
_embed_model = None


def load_bioclinicalbert(model_name: str = DEFAULT_EMBED_MODEL):
    """Load tokenizer and AutoModel for BioClinicalBERT with caching."""
    global _tokenizer, _embed_model
    if _tokenizer is not None and _embed_model is not None:
        return _tokenizer, _embed_model

    import torch
    from transformers import AutoModel, AutoTokenizer

    logger.info("Loading BioClinicalBERT model: %s ...", model_name)
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    _embed_model = AutoModel.from_pretrained(model_name)
    _embed_model.eval()

    if torch.cuda.is_available():
        _embed_model = _embed_model.cuda()
        logger.info("BioClinicalBERT successfully loaded onto GPU (%s).", torch.cuda.get_device_name(0))
    else:
        logger.info("BioClinicalBERT loaded on CPU.")

    return _tokenizer, _embed_model


def embed_batch(texts: List[str], model_name: str = DEFAULT_EMBED_MODEL, sub_batch_size: int = 32) -> List[List[float]]:
    """
    Embed a list of strings with mean pooling over token embeddings (ignoring padding).
    Processes in sub-batches to prevent GPU OOM on large batches.
    """
    import torch

    tokenizer, model = load_bioclinicalbert(model_name)
    device = next(model.parameters()).device
    all_embeddings: List[List[float]] = []

    for start in range(0, len(texts), sub_batch_size):
        sub_texts = texts[start : start + sub_batch_size]
        encoded = tokenizer(
            sub_texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model(**encoded)

        # Mean pooling
        attention_mask = encoded["attention_mask"].unsqueeze(-1)  # (B, T, 1)
        token_embeddings = outputs.last_hidden_state             # (B, T, D)
        summed = (token_embeddings * attention_mask).sum(dim=1)
        counts = attention_mask.sum(dim=1).clamp(min=1e-9)
        mean_pooled = summed / counts                            # (B, D)

        all_embeddings.extend(mean_pooled.cpu().tolist())

    return all_embeddings


# ---------------------------------------------------------------------------
# ChromaDB Vector Store Ingestion
# ---------------------------------------------------------------------------

def ingest_to_chroma(
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    db_path: Path = DEFAULT_CHROMA_DB_PATH,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embed_model_name: str = DEFAULT_EMBED_MODEL,
    batch_size: int = EMBED_BATCH_SIZE,
    reset: bool = False,
) -> int:
    """
    Embed all chunks from rag_chunks.csv and upsert into persistent ChromaDB.
    Supports incremental upsert (skips previously indexed chunk IDs).
    """
    import chromadb

    logger.info("=" * 60)
    logger.info("STEP: Upserting Chunks into ChromaDB Vector Store")
    logger.info("Chunks path: %s", chunks_path)
    logger.info("ChromaDB path: %s", db_path)
    logger.info("Collection: %s", collection_name)
    logger.info("=" * 60)

    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file {chunks_path} not found. Run step 'prep-chunks' first.")

    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))

    if reset:
        try:
            client.delete_collection(collection_name)
            logger.info("Reset collection '%s'.", collection_name)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    existing_count = collection.count()
    logger.info("Collection '%s' currently has %d documents.", collection_name, existing_count)

    df = pd.read_csv(chunks_path)
    if df.empty:
        logger.warning("Chunks file %s is empty. Nothing to ingest.", chunks_path)
        return existing_count

    # Incremental update: skip already ingested chunks
    existing_ids = set(collection.get(include=[])["ids"])
    df = df[~df["chunk_id"].astype(str).isin(existing_ids)]
    logger.info("%d new chunks to ingest (skipping %d already stored).", len(df), len(existing_ids))

    if df.empty:
        logger.info("All chunks already present in ChromaDB. Ingestion complete.")
        return collection.count()

    total_batches = (len(df) + batch_size - 1) // batch_size
    for batch_idx in tqdm(range(total_batches), desc="Embedding & Upserting to ChromaDB", unit="batch"):
        batch = df.iloc[batch_idx * batch_size : (batch_idx + 1) * batch_size]

        ids = batch["chunk_id"].astype(str).tolist()
        texts = batch["chunk_text"].fillna("").astype(str).tolist()
        metadatas = batch[["grid", "note_id", "note_datetime", "note_type"]].fillna("").astype(str).to_dict("records")

        # Filter out empty texts
        valid_mask = [bool(t.strip()) for t in texts]
        if not any(valid_mask):
            continue
        if not all(valid_mask):
            ids = [v for v, ok in zip(ids, valid_mask) if ok]
            texts = [v for v, ok in zip(texts, valid_mask) if ok]
            metadatas = [v for v, ok in zip(metadatas, valid_mask) if ok]

        try:
            embeddings = embed_batch(texts, model_name=embed_model_name)
        except Exception as e:
            logger.error("Failed to embed batch %d: %s. Skipping.", batch_idx, e)
            continue

        # Guard against empty embeddings
        valid_embed = [len(e) > 0 for e in embeddings]
        if not all(valid_embed):
            ids = [v for v, ok in zip(ids, valid_embed) if ok]
            embeddings = [v for v, ok in zip(embeddings, valid_embed) if ok]
            texts = [v for v, ok in zip(texts, valid_embed) if ok]
            metadatas = [v for v, ok in zip(metadatas, valid_embed) if ok]

        if not ids:
            continue

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

    final_count = collection.count()
    logger.info("ChromaDB ingestion complete. Collection '%s' now has %d documents.", collection_name, final_count)
    return final_count


# ---------------------------------------------------------------------------
# Self-Test Mode
# ---------------------------------------------------------------------------

def run_self_test() -> bool:
    """
    Run an end-to-end self-test using a synthetic temporary dataset.
    Verifies:
      1. Keyword loading and regex building
      2. Text cleaning and chunk splitting
      3. Markdown generation matching PhenoAgent format
      4. Chunk generation and CSV saving
      5. ChromaDB persistent client initialization, embedding, and upsert
    """
    import shutil
    import tempfile

    logger.info("Running automated self-test on synthetic sample data...")
    test_dir = Path(tempfile.mkdtemp(prefix="stuttering_ingest_test_"))
    try:
        test_notes_path = test_dir / "test_notes.csv"
        test_keywords_path = test_dir / "test_keywords.yaml"
        test_ehr_dir = test_dir / "ehr_markdown_dataset"
        test_chunks_path = test_dir / "rag_chunks.csv"
        test_chroma_dir = test_dir / "chroma_db"

        # Create synthetic keywords YAML
        test_keywords = {
            "popular_words": ["stutter", "stuttering", "disfluency", "slp", "speech"],
            "primary_keywords": ["stutter", "stuttering"],
        }
        with open(test_keywords_path, "w", encoding="utf-8") as f:
            yaml.dump(test_keywords, f)

        # Create synthetic notes CSV
        test_df = pd.DataFrame([
            {
                "person_source_value": "RTEST0001",
                "note_id": "1001",
                "note_datetime": "2020-05-10T10:00:00.000-05:00",
                "note_title": "Speech Therapy Evaluation",
                "note_source_value": "CLINIC NOTE",
                "note_text": "Patient is a 5-year-old child evaluated by SLP. Mom reports severe stuttering and disfluency on initial syllables.<br>Fluency therapy recommended.",
            },
            {
                "person_source_value": "RTEST0001",
                "note_id": "1002",
                "note_datetime": "2020-08-15T14:30:00.000-05:00",
                "note_title": "Follow-up Clinic Note",
                "note_source_value": "PROGRESS NOTE",
                "note_text": "Follow-up visit: Child shows improvement with stuttering severity after 8 weeks of speech therapy.",
            },
            {
                "person_source_value": "RTEST0002",
                "note_id": "2001",
                "note_datetime": "2021-01-20T09:15:00.000-06:00",
                "note_title": "Well Child Check",
                "note_source_value": "PEDIATRIC NOTE",
                "note_text": "Routine 4yo checkup. Normal development. Denies disfluency or speech problems.",
            },
        ])
        test_df.to_csv(test_notes_path, index=False)

        # Test 1: Generate EHR Markdown
        md_summary = generate_ehr_markdown_dataset(
            notes_path=test_notes_path,
            ehr_dir=test_ehr_dir,
            keywords_path=test_keywords_path,
            filter_keywords=True,
            reset=True,
        )
        assert md_summary["patients_created"] == 2, f"Expected 2 patients, got {md_summary['patients_created']}"
        test_file = test_ehr_dir / "RTEST0001.md"
        assert test_file.exists(), "RTEST0001.md was not created."
        content = test_file.read_text(encoding="utf-8")
        assert "# Grid: RTEST0001" in content, "Missing Grid header in markdown."
        assert "## Labs" in content, "Missing Labs section."
        assert "## Medical Notes" in content, "Missing Medical Notes section."
        assert "Speech Therapy Evaluation" in content, "Missing note title in markdown."
        logger.info("Test 1 (EHR Markdown Generation): PASSED")

        # Test 2: Chunk preparation
        chunks_df = prepare_chunks(
            notes_path=test_notes_path,
            output_path=test_chunks_path,
            keywords_path=test_keywords_path,
            filter_keywords=True,
            chunk_size=500,
            overlap=50,
        )
        assert not chunks_df.empty, "Chunks DataFrame should not be empty."
        assert test_chunks_path.exists(), "rag_chunks.csv was not created."
        assert "chunk_id" in chunks_df.columns, "chunk_id column missing."
        logger.info("Test 2 (Chunk Preparation): PASSED (generated %d chunks)", len(chunks_df))

        # Test 3: ChromaDB vector ingestion
        doc_count = ingest_to_chroma(
            chunks_path=test_chunks_path,
            db_path=test_chroma_dir,
            collection_name="test_stuttering_notes",
            embed_model_name=DEFAULT_EMBED_MODEL,
            batch_size=4,
            reset=True,
        )
        assert doc_count == len(chunks_df), f"Expected {len(chunks_df)} docs in ChromaDB, got {doc_count}"
        logger.info("Test 3 (ChromaDB Ingestion): PASSED (collection count: %d)", doc_count)

        logger.info("=" * 60)
        logger.info("ALL SELF-TESTS PASSED SUCCESSFULLY!")
        logger.info("=" * 60)
        return True

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest stuttering case notes into EHR Markdown and ChromaDB vector store.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--step",
        choices=["all", "database", "db", "markdown", "prep-chunks", "chroma"],
        default="all",
        help="Pipeline step to execute: 'all' (default), 'database'/'db' (prep chunks + ChromaDB, skipping markdown), 'markdown' (EHR files), 'prep-chunks' (rag_chunks.csv), or 'chroma' (vector store only)",
    )

    # Input paths
    parser.add_argument("--notes", type=Path, default=DEFAULT_NOTES_PATH, help="Path to stuttering_case_notes.csv")
    parser.add_argument("--keywords", type=Path, default=DEFAULT_KEYWORDS_PATH, help="Path to stuttering_keywords.yaml")

    # Output paths
    parser.add_argument("--ehr-dir", type=Path, default=DEFAULT_EHR_DIR, help="Directory for generated EHR Markdown files")
    parser.add_argument("--chunks-path", type=Path, default=DEFAULT_CHUNKS_PATH, help="Path to save rag_chunks.csv")
    parser.add_argument("--db", type=Path, default=DEFAULT_CHROMA_DB_PATH, help="Directory for persistent ChromaDB store")
    parser.add_argument("--collection", type=str, default=DEFAULT_COLLECTION_NAME, help="ChromaDB collection name")

    # Model & Chunk parameters
    parser.add_argument("--model", type=str, default=DEFAULT_EMBED_MODEL, help="Hugging Face model or local path for BioClinicalBERT")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Maximum characters per chunk (default: 1500)")
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP, help="Character overlap between consecutive chunks (default: 100)")
    parser.add_argument("--batch-size", type=int, default=EMBED_BATCH_SIZE, help="Chunks per embedding batch (default: 64)")
    parser.add_argument("--stream-chunksize", type=int, default=STREAM_CHUNKSIZE, help="CSV rows per streaming chunk (default: 10000)")

    # Execution controls
    parser.add_argument("--skip-markdown", action="store_true", help="Skip EHR Markdown dataset generation during ingestion")
    parser.add_argument("--sample-patients", type=int, default=None, help="Process only the first N unique patients")
    parser.add_argument("--limit-rows", type=int, default=None, help="Process only the first N rows of the notes CSV")
    parser.add_argument("--no-filter", action="store_true", help="Do not filter notes by keywords (include all notes)")
    parser.add_argument("--reset", action="store_true", help="Wipe and recreate collection and/or markdown directory")
    parser.add_argument("--test", action="store_true", help="Run automated self-test on synthetic data and exit")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    filter_kw = not args.no_filter

    # 1. EHR Markdown Dataset
    if args.step in ("all", "markdown") and not args.skip_markdown and args.step not in ("database", "db"):
        generate_ehr_markdown_dataset(
            notes_path=args.notes,
            ehr_dir=args.ehr_dir,
            keywords_path=args.keywords,
            sample_patients=args.sample_patients,
            limit_rows=args.limit_rows,
            filter_keywords=filter_kw,
            stream_chunksize=args.stream_chunksize,
            reset=args.reset,
        )

    # 2. Text Chunks Preparation
    if args.step in ("all", "prep-chunks", "database", "db") or (args.step == "chroma" and not args.chunks_path.exists()):
        prepare_chunks(
            notes_path=args.notes,
            output_path=args.chunks_path,
            keywords_path=args.keywords,
            sample_patients=args.sample_patients,
            limit_rows=args.limit_rows,
            filter_keywords=filter_kw,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap,
            stream_chunksize=args.stream_chunksize,
        )

    # 3. ChromaDB Vector Store Ingestion
    if args.step in ("all", "chroma", "database", "db"):
        ingest_to_chroma(
            chunks_path=args.chunks_path,
            db_path=args.db,
            collection_name=args.collection,
            embed_model_name=args.model,
            batch_size=args.batch_size,
            reset=args.reset,
        )

    logger.info("Pipeline execution for step '%s' completed successfully.", args.step)


if __name__ == "__main__":
    main()
