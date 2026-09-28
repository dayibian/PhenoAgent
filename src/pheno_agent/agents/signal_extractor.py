"""
signal_extractor.py — Signal Extractor Agent for Stuttering.

Uses an LLM to extract structured speech disfluency and stuttering signals
from each medical note. The clinical phenotyping rules (stuttering_rules.md)
are injected into every prompt so the LLM extracts standardized categories
(speech context, patient attribution, assertion, SLP/eval, exclusions).

Supports a **reflection mode**: when the Critic returns feedback, the
Extractor re-processes only the flagged notes with the feedback included.
"""

import concurrent.futures
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from pheno_agent.config import cfg
from pheno_agent.llm import OllamaHandler, parse_json_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas for Structured LLM Output
# ---------------------------------------------------------------------------

class NoteSignalSchema(BaseModel):
    note_label: str = Field(description="The label of the note, e.g. Note_1")
    stuttering_mentioned: bool = Field(description="Is stuttering, stammering, or speech disfluency mentioned in the note?")
    speech_context: Literal["speech", "non_speech", "not_found"] = Field(
        description="'speech' if describing spoken communication, 'non_speech' if describing non-speech jargon (gait, angina, priapism, stroke), or 'not_found'"
    )
    subject_attribution: Literal["patient", "family_only", "unknown"] = Field(
        description="'patient' if describing the patient, 'family_only' if restricted to family history/relatives, or 'unknown'"
    )
    assertion: Literal["affirmative", "negated", "ruled_out", "ambiguous", "not_found"] = Field(
        description="Clinical assertion: affirmative symptoms, explicitly negated, formally ruled out, ambiguous/query, or not_found"
    )
    slp_or_formal_assessment: bool = Field(
        description="True if there is confirmed clinical diagnosis by physician/SLP, formal speech therapy / SLP encounter / referral, or standardized test (SSI, OASES, %SS)"
    )
    competing_condition: bool = Field(
        description="True if speech irregularity is described solely within the context of active psychosis, schizophrenia, or clanging"
    )
    supporting_quotes: List[str] = Field(
        default_factory=list,
        description="Exact verbatim phrases from the note text supporting the extracted signals"
    )


class NoteSignalsResponseSchema(BaseModel):
    notes: List[NoteSignalSchema]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NoteSignals:
    """Extracted stuttering signals for a single note."""
    note_label: str = ""
    note_date: str = ""
    note_type: str = ""
    stuttering_mentioned: bool = False
    speech_context: str = "not_found"          # speech / non_speech / not_found
    subject_attribution: str = "unknown"       # patient / family_only / unknown
    assertion: str = "not_found"               # affirmative / negated / ruled_out / ambiguous / not_found
    slp_or_formal_assessment: bool = False
    competing_condition: bool = False
    supporting_quotes: List[str] = field(default_factory=list)


@dataclass
class CriticFeedback:
    """Feedback from the Critic agent for re-extraction."""
    note_label: str
    issue_type: str  # phantom_quote / attribution_error / non_speech_mismatch / negation_error
    description: str


# ---------------------------------------------------------------------------
# Diagnosis logic loader
# ---------------------------------------------------------------------------

_diagnosis_logic: Optional[str] = None


def _load_diagnosis_logic(path: Optional[Path] = None) -> str:
    """Load the clinical phenotyping rules markdown (cached)."""
    global _diagnosis_logic
    if _diagnosis_logic is not None:
        return _diagnosis_logic

    path = path or cfg.diagnosis_logic_path
    if not path.exists():
        logger.warning("Diagnosis rules file %s not found. Using empty text.", path)
        return ""

    with open(path, "r", encoding="utf-8") as f:
        _diagnosis_logic = f.read()
    return _diagnosis_logic


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_extraction_prompt(
    notes_batch: list,
    keyword_hints: str = "",
    critic_feedback: Optional[List[CriticFeedback]] = None,
) -> str:
    """
    Build the signal extraction prompt for stuttering phenotyping.
    Includes the clinical phenotyping rules as in-context guidance.
    """
    diagnosis_logic = _load_diagnosis_logic()

    # Format notes
    notes_parts = []
    for note in notes_batch:
        notes_parts.append(
            f"### {note['label']} (Date: {note['date']}, Type: {note['source']})\n"
            f"{note['text']}"
        )
    notes_text = "\n\n---\n\n".join(notes_parts) if notes_parts else "(No notes provided)"

    # Keyword hints section
    kw_section = ""
    if keyword_hints:
        kw_section = f"""
## Keyword Pre-Screen Hints
The following keyword-based signals were detected automatically. Use these as
hints to guide your attention, but verify each one against the actual note text:

{keyword_hints}
"""

    # Critic feedback section (for reflection loop)
    feedback_section = ""
    if critic_feedback:
        fb_lines = []
        for fb in critic_feedback:
            fb_lines.append(
                f"- **{fb.note_label}**: [{fb.issue_type}] {fb.description}"
            )
        feedback_section = f"""
## ⚠ Critic Feedback — Please Re-examine
The following issues were found in your previous extraction. Please carefully
re-examine the flagged notes and correct any errors:

{chr(10).join(fb_lines)}
"""

    prompt = f"""You are a clinical data extraction assistant specialising in speech disfluency and developmental stuttering phenotyping.

## Reference: Clinical Phenotyping Rules for Stuttering

{diagnosis_logic}

{kw_section}
{feedback_section}
## Patient Medical Notes

{notes_text}

## Task

For EACH note above, extract the clinical stuttering signals strictly following the clinical phenotyping rules above.
Do NOT determine the final overall diagnosis — only extract the objective signals for each note.

Respond ONLY with valid JSON matching this schema:
{{
  "notes": [
    {{
      "note_label": "Note_1",
      "stuttering_mentioned": true | false,
      "speech_context": "speech" | "non_speech" | "not_found",
      "subject_attribution": "patient" | "family_only" | "unknown",
      "assertion": "affirmative" | "negated" | "ruled_out" | "ambiguous" | "not_found",
      "slp_or_formal_assessment": true | false,
      "competing_condition": true | false,
      "supporting_quotes": ["<exact phrase from note>"]
    }}
  ]
}}

Rules:
- Report signals for EACH note separately.
- speech_context: Use "speech" if describing spoken language/fluency. Use "non_speech" if describing non-speech medical jargon (stuttering gait, stuttering angina, stuttering priapism, stuttering stroke).
- subject_attribution: Use "patient" if describing the patient. Use "family_only" if the mention appears ONLY in family history or refers only to relatives (e.g. "father stutters", "positive family history of stuttering").
- assertion:
  * "affirmative": Clear clinical mention that the patient stutters, has speech disfluency, or is undergoing speech therapy.
  * "negated": Explicit negation (e.g. "denies stuttering", "no stuttering", "speech is fluent without stutter", "normal speech fluency").
  * "ruled_out": Formal evaluation determined typical development and explicitly ruled out stuttering.
  * "ambiguous": Unconfirmed query, parental question without clinical evaluation, or uncertain context.
  * "not_found": No stuttering or disfluency mentioned.
- slp_or_formal_assessment: Set to true if there is an explicit diagnosis by physician/SLP, formal speech therapy / SLP referral / encounter, or standardized test score (SSI, SSI-3, SSI-4, OASES, %SS).
- competing_condition: Set to true if speech difficulty is described solely in the context of active psychosis, schizophrenia, or clanging.
- For supporting_quotes, copy EXACT verbatim phrases from the note text. Do not paraphrase.
- Do not include text outside the JSON."""

    return prompt


# ---------------------------------------------------------------------------
# Signal Extractor Agent
# ---------------------------------------------------------------------------

class SignalExtractor:
    """
    LLM-based agent that extracts structured stuttering signals from notes.
    """

    def __init__(self, llm: OllamaHandler):
        self.llm = llm
        self.model = cfg.models.extraction_model

    def extract(
        self,
        notes: list,
        keyword_hints: str = "",
        critic_feedback: Optional[List[CriticFeedback]] = None,
    ) -> List[NoteSignals]:
        """
        Extract signals from a list of notes.
        """
        if not notes:
            return []

        # Prepare note dicts for the prompt (preserving any pre-existing note label)
        note_dicts = []
        for i, note in enumerate(notes):
            note_dicts.append({
                "label": getattr(note, "label", None) or f"Note_{i + 1}",
                "date": getattr(note, "date", "unknown"),
                "source": getattr(note, "source", "unknown"),
                "text": getattr(note, "text", str(note)),
            })

        # Dynamic batching: group by count AND character length
        batch_size = cfg.agent.extraction_batch_size
        max_chars = getattr(cfg.agent, "extraction_max_chars_per_batch", 15000)
        batches = []
        current_batch = []
        current_chars = 0

        for nd in note_dicts:
            n_chars = len(nd.get("text", ""))
            # If current batch is full or adding this note exceeds char budget, start a new batch
            if current_batch and (len(current_batch) >= batch_size or (current_chars + n_chars > max_chars)):
                batches.append(current_batch)
                current_batch = []
                current_chars = 0

            current_batch.append(nd)
            current_chars += n_chars

        if current_batch:
            batches.append(current_batch)

        system_prompt = (
            "You are a clinical data extraction assistant. "
            "Extract structured speech disfluency and stuttering signals from medical notes. "
            "Respond only in valid JSON format."
        )

        def _process_single_batch(args):
            b_idx, batch = args
            # Filter critic feedback to only this batch's notes
            batch_labels = {n["label"] for n in batch}
            batch_feedback = None
            if critic_feedback:
                batch_feedback = [
                    fb for fb in critic_feedback if fb.note_label in batch_labels
                ]
                if not batch_feedback:
                    batch_feedback = None

            prompt = _build_extraction_prompt(
                batch, keyword_hints=keyword_hints, critic_feedback=batch_feedback,
            )

            logger.info(
                "[SignalExtractor] Processing batch %d/%d (%d notes: %s) …",
                b_idx + 1, len(batches), len(batch), [n["label"] for n in batch],
            )

            try:
                parsed_response = self.llm.get_structured(
                    system_prompt, prompt, NoteSignalsResponseSchema, model=self.model,
                )
                return self._process_extracted_signals(parsed_response, batch)
            except Exception as e:
                logger.warning("[SignalExtractor] Structured extraction failed (%s). Attempting raw JSON fallback...", e)
                raw_response = self.llm.get_completion(
                    system_prompt, prompt, model=self.model, expect_json=True,
                )
                parsed_dict = parse_json_response(raw_response)
                notes_data = parsed_dict.get("notes", []) if isinstance(parsed_dict, dict) else []
                signals = []
                for i, nd in enumerate(notes_data):
                    matching_dict = batch[i] if i < len(batch) else {}
                    signals.append(NoteSignals(
                        note_label=nd.get("note_label", matching_dict.get("label", f"Note_{i+1}")),
                        note_date=matching_dict.get("date", ""),
                        note_type=matching_dict.get("source", ""),
                        stuttering_mentioned=bool(nd.get("stuttering_mentioned", False)),
                        speech_context=str(nd.get("speech_context", "not_found")),
                        subject_attribution=str(nd.get("subject_attribution", "unknown")),
                        assertion=str(nd.get("assertion", "not_found")),
                        slp_or_formal_assessment=bool(nd.get("slp_or_formal_assessment", False)),
                        competing_condition=bool(nd.get("competing_condition", False)),
                        supporting_quotes=nd.get("supporting_quotes", []),
                    ))
                return signals

        indexed_batches = list(enumerate(batches))
        concurrency = getattr(cfg.agent, "extraction_concurrency", 1)

        all_signals: List[NoteSignals] = []
        if concurrency > 1 and len(batches) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(concurrency, len(batches))) as executor:
                batch_results = list(executor.map(_process_single_batch, indexed_batches))
        else:
            batch_results = [_process_single_batch(b) for b in indexed_batches]

        for b_sigs in batch_results:
            all_signals.extend(b_sigs)

        return all_signals

    def _process_extracted_signals(
        self, parsed_response: NoteSignalsResponseSchema, note_dicts: list
    ) -> List[NoteSignals]:
        """Convert Pydantic schemas back to NoteSignals dataclass objects."""
        signals = []
        for nd in parsed_response.notes:
            label = nd.note_label
            matching_dict = next(
                (d for d in note_dicts if d["label"] == label), {}
            )

            sig = NoteSignals(
                note_label=label,
                note_date=matching_dict.get("date", ""),
                note_type=matching_dict.get("source", ""),
                stuttering_mentioned=nd.stuttering_mentioned,
                speech_context=nd.speech_context,
                subject_attribution=nd.subject_attribution,
                assertion=nd.assertion,
                slp_or_formal_assessment=nd.slp_or_formal_assessment,
                competing_condition=nd.competing_condition,
                supporting_quotes=nd.supporting_quotes or [],
            )
            signals.append(sig)

        return signals
