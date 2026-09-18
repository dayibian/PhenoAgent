"""
adjudicator.py — Clinical Adjudicator Agent for Stuttering.

Applies the clinician's decision table deterministically, then uses an
LLM to generate a human-readable reasoning chain citing the specific
evidence, note IDs, and decision rules.

The decision table is a pure Python implementation of Section 3 and
Section 4, Step 9 (Longitudinal Synthesis) from ``stuttering_rules.md``.
Note: Lab values are not needed for this phenotype.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pheno_agent.agents.signal_extractor import NoteSignals
from pheno_agent.config import cfg
from pheno_agent.llm import OllamaHandler
from pheno_agent.tools.lab_lookup import LabSummary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class NoteDecision:
    """Decision for a single note."""
    note_label: str
    note_date: str
    decision: str  # Positive / Negative / Indeterminate / Excluded
    rule: str      # Which rule triggered this decision


@dataclass
class FinalDiagnosis:
    """Complete diagnosis output for a patient."""
    grid: str
    diagnosis: str = "Negative"  # Positive / Negative / Indeterminate / Excluded
    confidence: float = 0.0
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)
    decision_path: str = ""
    note_decisions: List[NoteDecision] = field(default_factory=list)
    lab_decision: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a flat dict for CSV output."""
        return {
            "grid": self.grid,
            "diagnosis": self.diagnosis,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "evidence": "; ".join(self.evidence[:10]),
            "decision_path": self.decision_path,
            "lab_decision": self.lab_decision,
        }


# ---------------------------------------------------------------------------
# Decision table (Section 3 of stuttering_rules.md)
# ---------------------------------------------------------------------------

def apply_decision_table(signals: NoteSignals) -> NoteDecision:
    """
    Apply the clinician's decision table to a single note's signals.

    Decision priority (per Section 3 of stuttering_rules.md):
      1. Non-speech context (gait, angina, priapism, stroke) → Excluded
      2. Family history only (no patient symptoms) → Excluded
      3. Competing psychiatric conditions (psychosis, clanging) → Excluded
      4. Explicit negation or formal rule-out → Negative
      5. Affirmative + SLP or formal assessment (SSI, OASES) → Positive
      6. Affirmative + Speech context (developmental / pediatric) → Positive
      7. Ambiguous context or query without confirmation → Indeterminate
      8. No signals found → Negative

    Parameters
    ----------
    signals : NoteSignals
        Extracted and verified signals for one note.

    Returns
    -------
    NoteDecision
        The decision and which rule triggered it.
    """
    # 1. Non-speech medical jargon exclusion
    if signals.speech_context == "non_speech":
        return NoteDecision(
            note_label=signals.note_label,
            note_date=signals.note_date,
            decision="Excluded",
            rule="Non-speech medical jargon (gait, angina, priapism, stroke)",
        )

    # 2. Family history only
    if signals.subject_attribution == "family_only":
        return NoteDecision(
            note_label=signals.note_label,
            note_date=signals.note_date,
            decision="Excluded",
            rule="Family history only without patient symptoms",
        )

    # 3. Competing psychiatric presentation (psychosis / clanging)
    if signals.competing_condition:
        return NoteDecision(
            note_label=signals.note_label,
            note_date=signals.note_date,
            decision="Excluded",
            rule="Speech irregularity attributed solely to psychosis/clanging",
        )

    # 4. Explicit negation or rule-out
    if signals.assertion in ("negated", "ruled_out"):
        return NoteDecision(
            note_label=signals.note_label,
            note_date=signals.note_date,
            decision="Negative",
            rule="Explicit negation or formal rule-out of stuttering",
        )

    # 5 & 6. Affirmative speech documentation
    if signals.assertion == "affirmative" and (signals.slp_or_formal_assessment or signals.speech_context == "speech"):
        if signals.slp_or_formal_assessment:
            return NoteDecision(
                note_label=signals.note_label,
                note_date=signals.note_date,
                decision="Positive",
                rule="Confirmed clinical diagnosis / SLP assessment / standardized test (SSI/OASES)",
            )
        return NoteDecision(
            note_label=signals.note_label,
            note_date=signals.note_date,
            decision="Positive",
            rule="Affirmative clinical / developmental speech disfluency documentation",
        )

    # 7. Ambiguous or query only
    if signals.assertion == "ambiguous" or (signals.stuttering_mentioned and signals.speech_context == "not_found"):
        return NoteDecision(
            note_label=signals.note_label,
            note_date=signals.note_date,
            decision="Indeterminate",
            rule="Ambiguous context or query without clinical confirmation",
        )

    # 8. No signal found
    return NoteDecision(
        note_label=signals.note_label,
        note_date=signals.note_date,
        decision="Negative",
        rule="No speech disfluency or stuttering documented",
    )


def aggregate_decisions(decisions: List[str]) -> str:
    """
    Aggregate note-level decisions across longitudinal history.
    Section 4, Step 9: Developmental stuttering onset is early childhood (ages 2–6).
    A single confirmed pediatric / SLP diagnosis establishes Positive.
    Later notes stating 'speech fluent' do not negate prior confirmed diagnosis.

    Priority: Positive > Indeterminate > Excluded > Negative
    """
    if "Positive" in decisions:
        return "Positive"
    if "Indeterminate" in decisions:
        return "Indeterminate"
    if "Excluded" in decisions:
        return "Excluded"
    return "Negative"


# ---------------------------------------------------------------------------
# Diagnosis logic loader
# ---------------------------------------------------------------------------

_diagnosis_logic: Optional[str] = None


def _load_diagnosis_logic(path: Optional[Path] = None) -> str:
    global _diagnosis_logic
    if _diagnosis_logic is not None:
        return _diagnosis_logic
    if path is None:
        path = cfg.diagnosis_logic_path
    if not path.exists():
        logger.warning("Diagnosis rules file %s not found. Using empty text.", path)
        return ""
    with open(path, "r", encoding="utf-8") as f:
        _diagnosis_logic = f.read()
    return _diagnosis_logic


# ---------------------------------------------------------------------------
# Adjudicator Agent
# ---------------------------------------------------------------------------

class Adjudicator:
    """
    Clinical Adjudicator agent for stuttering.

    Applies the clinician's decision table deterministically, then
    generates a human-readable reasoning chain using the LLM.
    """

    def __init__(self, llm: OllamaHandler):
        self.llm = llm
        self.model = cfg.models.reasoning_model

    def adjudicate(
        self,
        grid: str,
        verified_signals: List[NoteSignals],
        lab_summary: Optional[LabSummary] = None,
        keyword_decision: str = "Negative",
    ) -> FinalDiagnosis:
        """
        Produce the final diagnosis for a patient.

        Parameters
        ----------
        grid : str
            Patient identifier.
        verified_signals : list[NoteSignals]
            Critic-verified signals.
        lab_summary : LabSummary, optional
            Lab summary (not needed for stuttering, ignored).
        keyword_decision : str
            Aggregated keyword pre-screen decision.

        Returns
        -------
        FinalDiagnosis
            Complete diagnosis with reasoning chain.
        """
        result = FinalDiagnosis(grid=grid)
        result.lab_decision = "not_applicable"

        # Step 1: Lab Override Check (only if phenotype explicitly uses labs)
        if cfg.use_labs and lab_summary and lab_summary.lab_decision == "case":
            result.diagnosis = "Positive"
            result.confidence = 1.0
            result.decision_path = "Serological lab override"
            result.reasoning = "Serological lab decision indicates confirmed case."
            result.evidence = [lab_summary.summary_text]
            logger.info("[Adjudicator] %s → Positive (Lab override)", grid)
            return result

        # Step 2: Apply decision table per note
        note_decisions = []
        all_quotes = []
        for sig in verified_signals:
            nd = apply_decision_table(sig)
            note_decisions.append(nd)
            all_quotes.extend(sig.supporting_quotes)

        result.note_decisions = note_decisions

        # Step 3: Aggregate across notes (Longitudinal Synthesis)
        note_dx = [nd.decision for nd in note_decisions]
        llm_agg = aggregate_decisions(note_dx)

        final = llm_agg
        result.diagnosis = final
        result.evidence = all_quotes[:10]

        # Confidence based on agreement
        if llm_agg == keyword_decision:
            result.confidence = 0.95
        elif final == "Positive":
            result.confidence = 0.90
        elif final == "Excluded":
            result.confidence = 0.85
        elif final == "Negative":
            result.confidence = 0.80
        else:
            result.confidence = 0.65

        # Build decision path
        note_path_parts = [
            f"{nd.note_label}({nd.note_date}): {nd.decision} [{nd.rule}]"
            for nd in note_decisions
        ]
        result.decision_path = (
            f"Per-note: {'; '.join(note_path_parts) if note_path_parts else 'None'}. "
            f"LLM aggregated: {llm_agg}. Keyword: {keyword_decision}. "
            f"Final: {final}."
        )

        # Step 4: Generate reasoning chain (LLM)
        logger.info("[Adjudicator] Generating reasoning for %s …", grid)
        result.reasoning = self._generate_reasoning(result)

        logger.info("[Adjudicator] %s → %s (confidence=%.2f)", grid, final, result.confidence)
        return result

    def _generate_reasoning(
        self,
        result: FinalDiagnosis,
    ) -> str:
        """Use LLM to generate a human-readable reasoning chain."""
        diagnosis_logic = _load_diagnosis_logic()

        evidence_text = "\n".join(f"- {q}" for q in result.evidence) or "No supporting quotes."
        decisions_text = "\n".join(
            f"- {nd.note_label} ({nd.note_date}): {nd.decision} — Rule: {nd.rule}"
            for nd in result.note_decisions
        ) or "No per-note decisions."

        prompt = f"""Based on the following clinical analysis, write a clear, concise reasoning
chain explaining why this patient received a **{result.diagnosis}** stuttering phenotype.

## Clinical Phenotyping Rules
{diagnosis_logic}

## Per-Note Decisions (from decision table)
{decisions_text}

## Supporting Evidence (quotes from notes)
{evidence_text}

## Decision Path
{result.decision_path}

## Instructions
- Write 2–4 sentences explaining the phenotype decision step by step.
- Reference specific evidence (note dates, quotes, speech therapy/SLP mentions, family history, or negation).
- Reference which decision rule and longitudinal synthesis rule was triggered.
- If the diagnosis is Excluded, explain whether it was due to non-speech jargon (gait/angina/priapism/stroke), family history only, or competing psychiatric conditions.
- If the diagnosis is Negative, explain what was absent or explicitly negated.
- Be factual and concise. Do not speculate beyond the evidence."""

        system_prompt = (
            "You are a clinical reasoning assistant for developmental stuttering and speech disfluency. "
            "Write a clear, evidence-based reasoning chain for the phenotyping decision."
        )

        raw = self.llm.get_completion(system_prompt, prompt, model=self.model)
        return raw.strip() if raw else result.decision_path

