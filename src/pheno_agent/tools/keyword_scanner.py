"""
keyword_scanner.py — Keyword-based pre-screening tool for stuttering.

Scans note text for stuttering-related phrases defined in
stuttering_keywords.yaml and returns structured signals matching
the clinical phenotyping rules (stuttering_rules.md).
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from pheno_agent.config import cfg

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class KeywordSignals:
    """Keyword detection results for a single note."""
    has_primary: bool = False
    has_slp_or_formal: bool = False
    has_confirmatory: bool = False
    has_speech_context: bool = False
    is_negated: bool = False
    is_family_history_only: bool = False
    is_non_speech_exclusion: bool = False
    is_competing_condition: bool = False
    matched_terms: List[str] = field(default_factory=list)
    decision: str = "Negative"  # Positive / Negative / Indeterminate / Excluded


@dataclass
class PatientKeywordReport:
    """Aggregated keyword scan results across all notes."""
    grid: str = ""
    per_note: List[KeywordSignals] = field(default_factory=list)
    aggregated_decision: str = "Negative"
    summary_text: str = ""


# ---------------------------------------------------------------------------
# Keyword loader (cached)
# ---------------------------------------------------------------------------

_keywords: Optional[Dict[str, Any]] = None


def _load_keywords(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load stuttering keyword lists from YAML (cached after first call)."""
    global _keywords
    if _keywords is not None:
        return _keywords

    path = path or cfg.keywords_path
    if not path.exists():
        logger.warning("Keywords YAML not found at %s. Using empty dict.", path)
        return {}

    with open(path, "r", encoding="utf-8") as f:
        _keywords = yaml.safe_load(f) or {}
    logger.info("Loaded keyword dictionaries from %s", path)
    return _keywords


def _find_matches(text_lower: str, phrases: List[str]) -> List[str]:
    """Return all phrases found in text (case-insensitive word/subphrase matching)."""
    found = []
    for p in phrases:
        p_clean = str(p).strip().lower()
        if not p_clean:
            continue
        # Use regex boundary matching for short terms to avoid partial-word false positives
        if len(p_clean) <= 4 and p_clean.isalnum():
            pattern = rf"\b{re.escape(p_clean)}\b"
            if re.search(pattern, text_lower):
                found.append(p_clean)
        else:
            if p_clean in text_lower:
                found.append(p_clean)
    return found


# ---------------------------------------------------------------------------
# Per-note scanning
# ---------------------------------------------------------------------------

def scan_note_for_keywords(
    note_text: str, keywords_path: Optional[Path] = None,
) -> KeywordSignals:
    """
    Run keyword-based stuttering signal detection on a single note.
    Follows stuttering_rules.md phrase dictionaries and precedence.
    """
    kw = _load_keywords(keywords_path)
    text_lower = note_text.lower()

    # Match across categories
    primary_matches = _find_matches(text_lower, kw.get("primary_keywords", []))
    formal_eval_matches = _find_matches(text_lower, kw.get("diagnostic_tests_and_assessments", [])) + \
                          _find_matches(text_lower, kw.get("slp_clinical_context", []))
    confirmatory_matches = _find_matches(text_lower, kw.get("confirmatory_keywords", []))
    speech_matches = _find_matches(text_lower, kw.get("speech_context_indicators", []))
    negation_matches = _find_matches(text_lower, kw.get("negation_phrases", []))
    negation_regex = re.compile(
        r'\b(no|denies|denied|without|negative for|free of|not|rules? out|ruled out)\b[^\.\;\n]{0,80}\b(stutter\w*|stammer\w*|studder\w*|disfluen\w*|dysfluen\w*)',
        re.IGNORECASE,
    )
    regex_neg_matches = [m.group(0) for m in negation_regex.finditer(text_lower)]
    all_neg_phrases = list(set(negation_matches + regex_neg_matches))

    fh_matches = _find_matches(text_lower, kw.get("family_history_phrases", []))
    non_speech_matches = _find_matches(text_lower, kw.get("non_speech_exclusions", []))
    competing_matches = _find_matches(text_lower, kw.get("competing_conditions", []))

    all_matched = sorted(list(set(primary_matches + formal_eval_matches + speech_matches)))

    has_primary = len(primary_matches) > 0
    has_slp = len(formal_eval_matches) > 0
    has_conf = len(confirmatory_matches) > 0
    has_speech = len(speech_matches) > 0

    # Disambiguation: check if primary keywords exist outside of exclusions / negations
    primary_outside_fh = False
    if has_primary and fh_matches:
        text_without_fh = text_lower
        for fhm in sorted(fh_matches, key=len, reverse=True):
            text_without_fh = text_without_fh.replace(fhm, " ")
        primary_outside_fh = len(_find_matches(text_without_fh, kw.get("primary_keywords", []))) > 0

    primary_outside_non_speech = False
    if has_primary and non_speech_matches:
        text_without_ns = text_lower
        for nsm in sorted(non_speech_matches, key=len, reverse=True):
            text_without_ns = text_without_ns.replace(nsm, " ")
        primary_outside_non_speech = len(_find_matches(text_without_ns, kw.get("primary_keywords", []))) > 0

    primary_outside_negation = False
    if has_primary and all_neg_phrases:
        text_without_neg = text_lower
        for nm in sorted(all_neg_phrases, key=len, reverse=True):
            text_without_neg = text_without_neg.replace(nm, " ")
        primary_outside_negation = len(_find_matches(text_without_neg, kw.get("primary_keywords", []))) > 0

    is_fh = len(fh_matches) > 0 and not primary_outside_fh and not has_slp
    is_non_speech = len(non_speech_matches) > 0 and not primary_outside_non_speech and not has_slp
    is_competing = len(competing_matches) > 0 and not has_slp and not has_conf
    is_negated = len(all_neg_phrases) > 0 and not primary_outside_negation and not has_slp

    signals = KeywordSignals(
        has_primary=has_primary,
        has_slp_or_formal=has_slp,
        has_confirmatory=has_conf,
        has_speech_context=has_speech,
        is_negated=is_negated,
        is_family_history_only=is_fh,
        is_non_speech_exclusion=is_non_speech,
        is_competing_condition=is_competing,
        matched_terms=all_matched,
    )

    # Derive decision according to stuttering_rules.md Decision Matrix
    if signals.is_non_speech_exclusion or signals.is_family_history_only or signals.is_competing_condition:
        signals.decision = "Excluded"
    elif signals.has_slp_or_formal:
        signals.decision = "Positive"
    elif signals.is_negated:
        signals.decision = "Negative"
    elif signals.has_primary:
        if signals.has_confirmatory or signals.has_speech_context:
            signals.decision = "Positive"
        else:
            signals.decision = "Indeterminate"
    else:
        signals.decision = "Negative"

    return signals


# ---------------------------------------------------------------------------
# Patient-level scanning
# ---------------------------------------------------------------------------

def _aggregate_decisions(decisions: List[str]) -> str:
    """
    Aggregate note-level decisions across patient history.
    Priority: Positive > Indeterminate > Excluded > Negative
    """
    if "Positive" in decisions:
        return "Positive"
    if "Indeterminate" in decisions:
        return "Indeterminate"
    if "Excluded" in decisions:
        return "Excluded"
    return "Negative"


def scan_patient_notes(
    notes_texts: List[str],
    grid: str = "",
    keywords_path: Optional[Path] = None,
) -> PatientKeywordReport:
    """
    Run keyword pre-screen on all notes for a patient.
    """
    report = PatientKeywordReport(grid=grid)

    for text in notes_texts:
        sig = scan_note_for_keywords(text, keywords_path)
        report.per_note.append(sig)

    decisions = [s.decision for s in report.per_note]
    report.aggregated_decision = _aggregate_decisions(decisions)

    # Build summary text
    lines = [f"Keyword pre-screen for {grid}: {report.aggregated_decision}"]
    for i, sig in enumerate(report.per_note):
        features = []
        if sig.has_primary:
            features.append("primary_kw")
        if sig.has_slp_or_formal:
            features.append("slp/assessment")
        if sig.has_confirmatory:
            features.append("developmental_context")
        if sig.is_negated:
            features.append("negated")
        if sig.is_family_history_only:
            features.append("family_history_only")
        if sig.is_non_speech_exclusion:
            features.append("non_speech_exclusion")

        if features:
            lines.append(f"  Note {i}: [{', '.join(features)}] → {sig.decision} ({', '.join(sig.matched_terms[:5])})")

    report.summary_text = "\n".join(lines)
    return report
