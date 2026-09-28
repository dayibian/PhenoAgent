"""
ingest_control_cohort.py
------------------------
Ingestion pipeline for 500 control patients selected from Celiac BioVU:
  1. Generates structured EHR Markdown files in data/stuttering/ehr_markdown_dataset/{grid}.md
  2. Generates sliding-window chunks (size=1500, overlap=100) and appends to data/stuttering/rag_chunks.csv
  3. Embeds chunks via local BioClinicalBERT on GPU and upserts to persistent ChromaDB (collection: stuttering_notes)
"""

import csv
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import torch
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer
import chromadb

csv.field_size_limit(sys.maxsize)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ingest_control_cohort")

PROJECT_ROOT = Path("/home/biand/Projects/PhenoAgent")
STUTTERING_DATA_DIR = PROJECT_ROOT / "data" / "stuttering"
CONTROL_NOTES_CSV = STUTTERING_DATA_DIR / "stuttering_control_notes.csv"
CONTROL_GRIDS_CSV = STUTTERING_DATA_DIR / "control_patient_grids.csv"
EHR_DIR = STUTTERING_DATA_DIR / "ehr_markdown_dataset"
CHUNKS_PATH = STUTTERING_DATA_DIR / "rag_chunks.csv"
CHROMA_DB_PATH = STUTTERING_DATA_DIR / "chroma_db"
COLLECTION_NAME = "stuttering_notes"
LOCAL_MODEL_PATH = Path("/home/biand/Projects/Celiac_BioVU/models/Bio_ClinicalBERT")

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 100
EMBED_BATCH_SIZE = 256


def clean_note_text(text: str) -> str:
    """Clean HTML tags, PHI placeholders, and whitespace from clinical note."""
    if not isinstance(text, str):
        text = str(text) if pd.notnull(text) else ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\[\*\*.*?\*\*\]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split clean note text into sliding window character chunks."""
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


def create_markdown_for_grid(grid: str, notes_list: List[Dict]) -> str:
    """Construct PhenoAgent EHR markdown document for one patient."""
    lines = [f"# Grid: {grid}", "", "## Labs", "No labs available.", "", "## Medical Notes"]
    if notes_list:
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


def step1_generate_ehr_markdown():
    logger.info("=" * 60)
    logger.info("STEP 1: Generating Patient EHR Markdown Files")
    logger.info("=" * 60)

    EHR_DIR.mkdir(parents=True, exist_ok=True)
    
    patients_notes: Dict[str, List[Dict]] = {}
    total_notes = 0

    reader = pd.read_csv(
        CONTROL_NOTES_CSV,
        escapechar="\\",
        low_memory=False,
        chunksize=50000,
    )

    with tqdm(desc="Streaming notes for EHR Markdown", unit="chunk") as pbar:
        for chunk in reader:
            for _, row in chunk.iterrows():
                grid = str(row["grid"]).strip()
                cleaned = clean_note_text(row.get("note_text", ""))
                if not cleaned:
                    continue

                raw_dt = row.get("note_datetime")
                parsed_dt = pd.to_datetime(raw_dt, errors="coerce", utc=True)
                date_str = parsed_dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(parsed_dt) else "Unknown Date"

                note_entry = {
                    "note_id": str(row.get("note_id", "")),
                    "note_datetime_parsed": parsed_dt,
                    "date_str": date_str,
                    "note_title": str(row.get("note_title", "Untitled Note")),
                    "note_source_value": str(row.get("note_source_value", "Unknown Source")),
                    "note_text": cleaned,
                }
                if grid not in patients_notes:
                    patients_notes[grid] = []
                patients_notes[grid].append(note_entry)
                total_notes += 1
            pbar.update(1)

    logger.info("Writing Markdown files for %d control patients (%d notes)...", len(patients_notes), total_notes)
    for grid, notes in tqdm(patients_notes.items(), desc="Writing Markdown files", unit="patient"):
        md_text = create_markdown_for_grid(grid, notes)
        (EHR_DIR / f"{grid}.md").write_text(md_text, encoding="utf-8")

    logger.info("Step 1 complete: 500 EHR markdown files written to %s", EHR_DIR)
    return len(patients_notes)


def step2_generate_chunks():
    logger.info("=" * 60)
    logger.info("STEP 2: Generating Text Chunks & Appending to rag_chunks.csv")
    logger.info("=" * 60)

    # First load existing chunk_ids to prevent duplicates
    existing_chunk_ids: Set[str] = set()
    if CHUNKS_PATH.exists():
        logger.info("Loading existing chunk IDs from %s...", CHUNKS_PATH)
        for c in pd.read_csv(CHUNKS_PATH, usecols=["chunk_id"], chunksize=100000):
            existing_chunk_ids.update(c["chunk_id"].astype(str))
        logger.info("Found %d existing chunks in rag_chunks.csv", len(existing_chunk_ids))

    reader = pd.read_csv(
        CONTROL_NOTES_CSV,
        escapechar="\\",
        low_memory=False,
        chunksize=50000,
    )

    new_chunks_count = 0
    temp_chunks_csv = STUTTERING_DATA_DIR / "new_control_chunks.csv"
    
    with open(temp_chunks_csv, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["chunk_id", "grid", "note_id", "note_datetime", "note_type", "chunk_text"])

        with tqdm(desc="Chunking notes", unit="batch") as pbar:
            for batch_idx, chunk_df in enumerate(reader):
                batch_rows = []
                for row_idx, row in chunk_df.iterrows():
                    grid = str(row["grid"]).strip()
                    cleaned = clean_note_text(row.get("note_text", ""))
                    if not cleaned:
                        continue
                    note_id = str(row.get("note_id", ""))
                    note_datetime = str(row.get("note_datetime", ""))
                    note_type = str(row.get("note_title", "") or row.get("note_type", "") or "Note")

                    chunks = split_into_chunks(cleaned, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
                    for i, chunk_text in enumerate(chunks):
                        cid = f"{grid}_{note_id}_{i}"
                        if cid in existing_chunk_ids:
                            continue
                        batch_rows.append([cid, grid, note_id, note_datetime, note_type, chunk_text])
                        new_chunks_count += 1

                writer.writerows(batch_rows)
                pbar.update(1)

    logger.info("Generated %d new chunks. Saved temporary chunks to %s", new_chunks_count, temp_chunks_csv)

    # Append new chunks to rag_chunks.csv
    if CHUNKS_PATH.exists():
        logger.info("Appending new chunks to %s...", CHUNKS_PATH)
        with open(CHUNKS_PATH, "a", newline="", encoding="utf-8") as f_main:
            with open(temp_chunks_csv, "r", encoding="utf-8") as f_temp:
                next(f_temp)  # skip header
                for line in f_temp:
                    f_main.write(line)
    else:
        temp_chunks_csv.rename(CHUNKS_PATH)

    logger.info("Step 2 complete: rag_chunks.csv updated with %d new chunks.", new_chunks_count)
    return temp_chunks_csv, new_chunks_count


def step3_chroma_ingestion(temp_chunks_csv: Path):
    logger.info("=" * 60)
    logger.info("STEP 3: Embedding & Upserting Chunks to ChromaDB Vector Store")
    logger.info("=" * 60)

    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    initial_count = collection.count()
    logger.info("Collection '%s' currently has %d items.", COLLECTION_NAME, initial_count)

    # Existing ChromaDB IDs to skip
    existing_ids = set(collection.get(include=[])["ids"])
    logger.info("Found %d existing indexed IDs in ChromaDB.", len(existing_ids))

    # Load BioClinicalBERT onto GPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Loading BioClinicalBERT model onto %s...", device)
    tokenizer = AutoTokenizer.from_pretrained(str(LOCAL_MODEL_PATH))
    model = AutoModel.from_pretrained(str(LOCAL_MODEL_PATH)).to(device).eval()
    logger.info("Model successfully loaded.")

    def embed_batch(texts: List[str]) -> List[List[float]]:
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            outputs = model(**encoded)
        attention_mask = encoded["attention_mask"].unsqueeze(-1)
        summed = (outputs.last_hidden_state * attention_mask).sum(dim=1)
        counts = attention_mask.sum(dim=1).clamp(min=1e-9)
        pooled = summed / counts
        return pooled.cpu().tolist()

    # Read temp_chunks_csv in batches, filter, embed, and upsert
    reader = pd.read_csv(temp_chunks_csv, chunksize=EMBED_BATCH_SIZE)
    total_upserted = 0
    t0 = time.time()

    with tqdm(desc="Embedding & Upserting to ChromaDB", unit="batch") as pbar:
        for batch in reader:
            batch = batch[~batch["chunk_id"].astype(str).isin(existing_ids)]
            if batch.empty:
                pbar.update(1)
                continue

            ids = batch["chunk_id"].astype(str).tolist()
            texts = batch["chunk_text"].fillna("").astype(str).tolist()
            metadatas = batch[["grid", "note_id", "note_datetime", "note_type"]].fillna("").astype(str).to_dict("records")

            valid = [bool(t.strip()) for t in texts]
            if not any(valid):
                pbar.update(1)
                continue
            if not all(valid):
                ids = [v for v, ok in zip(ids, valid) if ok]
                texts = [v for v, ok in zip(texts, valid) if ok]
                metadatas = [v for v, ok in zip(metadatas, valid) if ok]

            embeddings = embed_batch(texts)
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            total_upserted += len(ids)
            pbar.update(1)
            pbar.set_postfix(upserted=total_upserted)

    elapsed = time.time() - t0
    final_count = collection.count()
    logger.info(
        "ChromaDB ingestion complete in %.1fs (%.1f chunks/s). Initial: %d, Final: %d (+%d)",
        elapsed,
        total_upserted / elapsed if elapsed > 0 else 0,
        initial_count,
        final_count,
        final_count - initial_count,
    )


def main():
    start_total = time.time()
    logger.info("Starting ingestion of 500 control patients into Stuttering Cohort database...")
    
    # Step 1: EHR Markdown
    num_patients = step1_generate_ehr_markdown()
    
    # Step 2: Chunks
    temp_chunks_csv, num_chunks = step2_generate_chunks()
    
    # Step 3: ChromaDB
    step3_chroma_ingestion(temp_chunks_csv)

    total_time = time.time() - start_total
    logger.info("=" * 60)
    logger.info("ALL INGESTION STEPS COMPLETED in %.1f minutes!", total_time / 60)
    logger.info("Patients ingested: %d", num_patients)
    logger.info("Chunks generated and embedded: %d", num_chunks)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
