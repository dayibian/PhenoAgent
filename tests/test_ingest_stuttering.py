"""
test_ingest_stuttering.py
-------------------------
Unit and integration tests for the stuttering notes ingestion pipeline (src/ingest_stuttering.py).
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add src to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pandas as pd
import yaml

from ingest_stuttering import (
    DEFAULT_EMBED_MODEL,
    clean_note_text,
    create_markdown_for_grid,
    generate_ehr_markdown_dataset,
    ingest_to_chroma,
    load_keywords,
    prepare_chunks,
    split_into_chunks,
)
from pheno_agent.tools.ehr_reader import parse_ehr_sections


class TestIngestStuttering(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_stutter_ingest_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_real_keywords(self):
        """Test loading keywords from the actual stuttering_keywords.yaml."""
        kw_path = PROJECT_ROOT / "data" / "stuttering" / "stuttering_keywords.yaml"
        keywords = load_keywords(kw_path)
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        self.assertIn("stutter", keywords)
        self.assertIn("stuttering", keywords)
        self.assertIn("disfluency", keywords)

    def test_clean_note_text(self):
        """Test text cleaning for HTML tags, PHI brackets, and whitespace."""
        raw = "Line 1<br>Line 2<br />[**DOCTOR 1234**] was present.   Too   many    spaces.\n\n\n\nLine 3"
        cleaned = clean_note_text(raw)
        self.assertNotIn("<br>", cleaned)
        self.assertNotIn("<br />", cleaned)
        self.assertNotIn("[**", cleaned)
        self.assertNotIn("**]", cleaned)
        self.assertNotIn("   ", cleaned)
        self.assertNotIn("\n\n\n", cleaned)
        self.assertIn("Line 1\nLine 2", cleaned)
        self.assertIn("was present.", cleaned)
        self.assertIn("Line 3", cleaned)

    def test_split_into_chunks(self):
        """Test character-level sliding window chunking."""
        # Short text should return 1 chunk
        short_text = "Patient has mild developmental stuttering."
        chunks = split_into_chunks(short_text, chunk_size=100, overlap=20)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], short_text)

        # Longer text should create overlapping chunks
        long_text = "A" * 250
        chunks = split_into_chunks(long_text, chunk_size=100, overlap=20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 100 for c in chunks))

    def test_markdown_format_compatibility_with_ehr_reader(self):
        """Test that generated markdown format is cleanly parsed by PhenoAgent's ehr_reader."""
        grid = "R123456789"
        notes = [
            {
                "note_id": "1",
                "note_datetime_parsed": pd.Timestamp("2021-03-15 10:00:00", tz="UTC"),
                "date_str": "2021-03-15 10:00:00",
                "note_title": "Pediatric Speech Evaluation",
                "note_source_value": "CLINIC NOTE",
                "note_text": "Child presents with speech disfluency and block repetitions.",
            },
            {
                "note_id": "2",
                "note_datetime_parsed": pd.Timestamp("2021-06-20 14:00:00", tz="UTC"),
                "date_str": "2021-06-20 14:00:00",
                "note_title": "Speech Therapy Progress Note",
                "note_source_value": "SLP NOTE",
                "note_text": "Patient completed 8 sessions of fluency therapy. Stuttering improved.",
            },
        ]
        md_content = create_markdown_for_grid(grid, notes)

        # Verify raw markdown contents
        self.assertIn(f"# Grid: {grid}", md_content)
        self.assertIn("## Labs", md_content)
        self.assertIn("## Medical Notes", md_content)
        self.assertIn("Pediatric Speech Evaluation", md_content)

        # Test parser roundtrip via PhenoAgent's ehr_reader
        parsed = parse_ehr_sections(md_content)
        self.assertEqual(parsed.grid, grid)
        self.assertEqual(len(parsed.notes), 2)
        self.assertEqual(parsed.notes[0].title, "Pediatric Speech Evaluation")
        self.assertIn("speech disfluency", parsed.notes[0].text)
        self.assertEqual(parsed.notes[1].title, "Speech Therapy Progress Note")

    def test_synthetic_end_to_end_pipeline(self):
        """Test end-to-end markdown, chunking, and ChromaDB ingestion with synthetic data."""
        notes_csv = self.test_dir / "notes.csv"
        keywords_yaml = self.test_dir / "keywords.yaml"
        ehr_dir = self.test_dir / "ehr_markdown"
        chunks_csv = self.test_dir / "rag_chunks.csv"
        chroma_dir = self.test_dir / "chroma_db"

        # Write test keywords
        with open(keywords_yaml, "w", encoding="utf-8") as f:
            yaml.dump({"popular_words": ["stutter", "disfluency", "speech"]}, f)

        # Write test notes
        df = pd.DataFrame([
            {
                "person_source_value": "R_SYNTH_01",
                "note_id": "901",
                "note_datetime": "2022-01-01T10:00:00.000-06:00",
                "note_title": "SLP Initial Consultation",
                "note_source_value": "OUTPATIENT",
                "note_text": "Child has developmental stutter with repetitions.",
            },
            {
                "person_source_value": "R_SYNTH_02",
                "note_id": "902",
                "note_datetime": "2022-02-01T11:00:00.000-06:00",
                "note_title": "Routine Checkup",
                "note_source_value": "GENERAL CLINIC",
                "note_text": "No concerns. Speech fluency is completely normal.",
            },
        ])
        df.to_csv(notes_csv, index=False)

        # Step 1: EHR Markdown
        md_res = generate_ehr_markdown_dataset(
            notes_path=notes_csv,
            ehr_dir=ehr_dir,
            keywords_path=keywords_yaml,
            filter_keywords=True,
            reset=True,
        )
        self.assertEqual(md_res["patients_created"], 2)
        self.assertTrue((ehr_dir / "R_SYNTH_01.md").exists())
        self.assertTrue((ehr_dir / "R_SYNTH_02.md").exists())

        # Step 2: Chunks Prep
        chunks_df = prepare_chunks(
            notes_path=notes_csv,
            output_path=chunks_csv,
            keywords_path=keywords_yaml,
            filter_keywords=True,
            chunk_size=500,
            overlap=50,
        )
        self.assertEqual(len(chunks_df), 2)
        self.assertTrue(chunks_csv.exists())

        # Step 3: ChromaDB Ingestion
        count = ingest_to_chroma(
            chunks_path=chunks_csv,
            db_path=chroma_dir,
            collection_name="test_notes",
            embed_model_name=DEFAULT_EMBED_MODEL,
            batch_size=4,
            reset=True,
        )
        self.assertEqual(count, 2)
        self.assertTrue(chroma_dir.exists())

    def test_real_notes_csv_small_sample_smoke_test(self):
        """Smoke test running pipeline on real stuttering_case_notes.csv with limit_rows=200."""
        real_csv = PROJECT_ROOT / "data" / "stuttering" / "stuttering_case_notes.csv"
        real_kw = PROJECT_ROOT / "data" / "stuttering" / "stuttering_keywords.yaml"

        if not real_csv.exists() or not real_kw.exists():
            self.skipTest("Real stuttering data files not found.")

        ehr_dir = self.test_dir / "real_ehr_sample"
        chunks_csv = self.test_dir / "real_rag_chunks.csv"
        chroma_dir = self.test_dir / "real_chroma_sample"

        # Generate markdown for small sample of rows
        md_res = generate_ehr_markdown_dataset(
            notes_path=real_csv,
            ehr_dir=ehr_dir,
            keywords_path=real_kw,
            limit_rows=300,
            sample_patients=3,
            filter_keywords=True,
            reset=True,
        )
        self.assertGreater(md_res["total_rows_read"], 0)
        self.assertGreaterEqual(md_res["patients_created"], 1)

        # Prepare chunks for small sample
        chunks_df = prepare_chunks(
            notes_path=real_csv,
            output_path=chunks_csv,
            keywords_path=real_kw,
            limit_rows=300,
            sample_patients=3,
            filter_keywords=True,
        )
        self.assertGreater(len(chunks_df), 0)

        # Ingest to ChromaDB for small sample
        doc_count = ingest_to_chroma(
            chunks_path=chunks_csv,
            db_path=chroma_dir,
            collection_name="sample_stuttering_notes",
            embed_model_name=DEFAULT_EMBED_MODEL,
            batch_size=16,
            reset=True,
        )
        self.assertEqual(doc_count, len(chunks_df))


if __name__ == "__main__":
    unittest.main()
