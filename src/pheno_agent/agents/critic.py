"""
critic.py — Critic / Verification Agent for Stuttering.

Verifies extracted signals against the raw note text, inspired by
DeepRare's Check_Agent. Performs two stages:

1. **Quote verification** — checks that supporting quotes actually
   appear in the note (fuzzy match).
2. **Signal consistency** — uses the reasoning LLM to verify cases
   where keyword scanner and LLM extractor disagree on speech context,
   subject attribution (patient vs family history), negation, or
   competing conditions (psychosis/clanging).

The clinician's phenotyping and verification rules (from
``stuttering_rules.md``) are included in the LLM prompt.
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from pheno_agent.agents.signal_extractor import CriticFeedback, NoteSignals
from pheno_agent.config import cfg
from pheno_agent.llm import OllamaHandler, parse_json_response
from pheno_agent.tools.keyword_scanner import KeywordSignals

class VerificationSchema(BaseModel):
    note_label: str
    field: Literal[
        "speech_context",
        "subject_attribution",
        "assertion",
        "slp_or_formal_assessment",
        "competing_condition",
    ]
    correct_value: str
    reasoning: str

class VerificationResponseSchema(BaseModel):
    verifications: List[VerificationSchema]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    """Output of the Critic agent."""
    verified_signals: List[NoteSignals] = field(default_factory=list)
    issues: List[CriticFeedback] = field(default_factory=list)
    needs_re_extraction: bool = False


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
# Quote verification (deterministic)
# ---------------------------------------------------------------------------

def _fuzzy_contains(haystack: str, needle: str, threshold: float = 0.75) -> bool:
    """
    Check if ``needle`` appears in ``haystack`` with fuzzy matching.

    Uses SequenceMatcher ratio on a sliding window for efficiency.
    """
    if not needle or not haystack:
        return False

    needle_lower = needle.lower().strip()
    haystack_lower = haystack.lower()

    # Exact substring check first
    if needle_lower in haystack_lower:
        return True

    # Sliding window fuzzy match for short phrases
    if len(needle_lower) > 200:
        # For very long quotes, just check a substring
        return needle_lower[:100] in haystack_lower

    window_size = len(needle_lower)
    for i in range(0, max(1, len(haystack_lower) - window_size + 1), window_size // 4 or 1):
        window = haystack_lower[i:i + window_size + 20]
        ratio = SequenceMatcher(None, needle_lower, window).ratio()
        if ratio >= threshold:
            return True

    return False


def _verify_quotes(
    signals: List[NoteSignals],
    note_texts: List[str],
) -> List[CriticFeedback]:
    """
    Verify that supporting quotes actually appear in the note text.

    Returns a list of CriticFeedback for phantom (fabricated) quotes.
    """
    issues = []
    for sig, text in zip(signals, note_texts):
        for quote in sig.supporting_quotes:
            if not _fuzzy_contains(text, quote):
                issues.append(CriticFeedback(
                    note_label=sig.note_label,
                    issue_type="phantom_quote",
                    description=(
                        f'Quote not found in note text: "{quote[:100]}…"'
                        if len(quote) > 100 else
                        f'Quote not found in note text: "{quote}"'
                    ),
                ))
    return issues


# ---------------------------------------------------------------------------
# Signal consistency check (LLM-based)
# ---------------------------------------------------------------------------

def _find_signal_mismatches(
    signals: List[NoteSignals],
    keyword_signals: List[KeywordSignals],
) -> List[dict]:
    """
    Identify cases where keyword scanner and LLM extractor disagree.

    Returns a list of mismatch descriptions for the LLM to review.
    """
    mismatches = []
    for sig, kw in zip(signals, keyword_signals):
        # 1. Non-speech exclusion mismatch
        if kw.is_non_speech_exclusion and sig.speech_context != "non_speech":
            mismatches.append({
                "note_label": sig.note_label,
                "field": "speech_context",
                "keyword_says": "non_speech (exclusion keyword hit: gait/angina/priapism/stroke)",
                "llm_says": sig.speech_context,
            })
        elif kw.has_speech_context and sig.speech_context == "non_speech":
            mismatches.append({
                "note_label": sig.note_label,
                "field": "speech_context",
                "keyword_says": "speech (speech context keywords hit)",
                "llm_says": "non_speech",
            })

        # 2. Subject attribution mismatch (Family History vs Patient)
        if kw.is_family_history_only and sig.subject_attribution == "patient":
            mismatches.append({
                "note_label": sig.note_label,
                "field": "subject_attribution",
                "keyword_says": "family_only (family history keywords hit)",
                "llm_says": "patient",
            })

        # 3. Negation / assertion mismatch
        if kw.is_negated and sig.assertion == "affirmative":
            mismatches.append({
                "note_label": sig.note_label,
                "field": "assertion",
                "keyword_says": "negated (negation keywords hit)",
                "llm_says": "affirmative",
            })
        elif not kw.is_negated and sig.assertion in ("negated", "ruled_out") and sig.stuttering_mentioned:
            mismatches.append({
                "note_label": sig.note_label,
                "field": "assertion",
                "keyword_says": "not negated by keyword",
                "llm_says": sig.assertion,
            })

        # 4. SLP or formal assessment mismatch
        if kw.has_slp_or_formal and not sig.slp_or_formal_assessment:
            mismatches.append({
                "note_label": sig.note_label,
                "field": "slp_or_formal_assessment",
                "keyword_says": "true (SLP/assessment keywords hit: SSI/OASES/SLP)",
                "llm_says": "false",
            })

        # 5. Competing condition mismatch
        if kw.is_competing_condition and not sig.competing_condition:
            mismatches.append({
                "note_label": sig.note_label,
                "field": "competing_condition",
                "keyword_says": "true (psychosis/thought disorder/clanging keywords hit)",
                "llm_says": "false",
            })

    return mismatches


def _build_consistency_prompt(
    mismatches: list,
    affirmative_claims: list,
    note_texts_by_label: dict,
) -> str:
    """Build the LLM prompt for stuttering signal consistency verification."""
    diagnosis_logic = _load_diagnosis_logic()

    sections = []

    if mismatches:
        mm_lines = []
        for mm in mismatches:
            note_text = note_texts_by_label.get(mm["note_label"], "(not available)")
            if len(note_text) > 3000:
                note_text = note_text[:3000] + "\n… [truncated]"
            mm_lines.append(
                f"### {mm['note_label']}: {mm['field']}\n"
                f"- Keyword scanner says: {mm['keyword_says']}\n"
                f"- LLM extractor says: {mm['llm_says']}\n"
                f"- Note text:\n{note_text}\n"
            )
        sections.append(
            "## Signal Mismatches to Verify\n" + "\n---\n".join(mm_lines)
        )

    if affirmative_claims:
        claim_lines = []
        for item in affirmative_claims:
            note_text = note_texts_by_label.get(item["note_label"], "(not available)")
            if len(note_text) > 3000:
                note_text = note_text[:3000] + "\n… [truncated]"
            claim_lines.append(
                f"### {item['note_label']}\n"
                f"- Claimed affirmative stuttering: True\n"
                f"- Supporting quote: \"{item['quote']}\"\n"
                f"- Note text:\n{note_text}\n"
            )
        sections.append(
            "## Affirmative Stuttering Claims to Verify\n" + "\n---\n".join(claim_lines)
        )

    if not sections:
        return ""

    prompt = f"""You are a clinical verification specialist for speech disfluency and developmental stuttering phenotyping.

## Clinician's Phenotyping & Verification Rules

{diagnosis_logic}

## Your Task

Review each case below and determine if the LLM extractor's signal is correct.

{chr(10).join(sections)}

Respond ONLY with valid JSON matching this schema:
{{
  "verifications": [
    {{
      "note_label": "Note_X",
      "field": "speech_context | subject_attribution | assertion | slp_or_formal_assessment | competing_condition",
      "correct_value": "<the correct value after your review: 'speech'/'non_speech'/'not_found' for speech_context; 'patient'/'family_only'/'unknown' for subject_attribution; 'affirmative'/'negated'/'ruled_out'/'ambiguous'/'not_found' for assertion; 'true'/'false' for slp_or_formal_assessment and competing_condition>",
      "reasoning": "<brief explanation citing clinical rule and note text>"
    }}
  ]
}}

Rules:
- If stuttering describes non-speech medical phenomena (gait, angina, priapism, stroke), speech_context MUST be 'non_speech'.
- If stuttering is mentioned ONLY for family members (e.g. father, mother, sibling stutters) and NOT the patient, subject_attribution MUST be 'family_only'.
- If stuttering is clearly negated (e.g. "denies stuttering", "speech fluent without stutter"), assertion MUST be 'negated' or 'ruled_out'.
- A query or rule-out without affirmative diagnosis (e.g. "mother asks about stuttering?", "rule out stuttering") is 'ambiguous'.
- If confirmed by SLP, speech therapy plan/consult, or formal test (SSI, OASES, %SS), slp_or_formal_assessment MUST be 'true'.
- If speech abnormality is described solely within active psychosis, schizophrenia, or clanging, competing_condition MUST be 'true'.
- Do not include text outside the JSON."""

    return prompt


# ---------------------------------------------------------------------------
# Critic Agent
# ---------------------------------------------------------------------------

class Critic:
    """
    Verification agent that checks extracted signals for accuracy.

    Performs quote verification (deterministic) and signal consistency
    checking (LLM-based) using the clinician's phenotyping rules.
    """

    def __init__(self, llm: OllamaHandler):
        self.llm = llm
        self.model = cfg.models.reasoning_model

    def verify(
        self,
        signals: List[NoteSignals],
        note_texts: List[str],
        keyword_signals: Optional[List[KeywordSignals]] = None,
    ) -> VerificationResult:
        """
        Verify extracted signals against note text and keyword results.

        Parameters
        ----------
        signals : list[NoteSignals]
            Signals from the Signal Extractor.
        note_texts : list[str]
            Corresponding note texts (same order as signals).
        keyword_signals : list[KeywordSignals], optional
            Keyword scan results (same order).

        Returns
        -------
        VerificationResult
            Verified signals, issues found, and re-extraction flag.
        """
        result = VerificationResult()
        all_issues: List[CriticFeedback] = []

        # Stage 1: Quote verification (deterministic)
        logger.info("[Critic] Stage 1: Quote verification …")
        quote_issues = _verify_quotes(signals, note_texts)
        all_issues.extend(quote_issues)
        if quote_issues:
            logger.info("[Critic] Found %d phantom quotes.", len(quote_issues))

        # Stage 2: Signal consistency (LLM-based, only if needed)
        needs_llm_check = False
        mismatches = []
        affirmative_claims = []

        if keyword_signals:
            mismatches = _find_signal_mismatches(signals, keyword_signals)
            if mismatches:
                needs_llm_check = True
                logger.info("[Critic] Found %d keyword/LLM mismatches.", len(mismatches))

        # Check affirmative stuttering claims where context or attribution could be uncertain
        for sig in signals:
            if sig.stuttering_mentioned and sig.assertion == "affirmative":
                if sig.speech_context != "speech" or sig.subject_attribution != "patient":
                    affirmative_claims.append({
                        "note_label": sig.note_label,
                        "quote": sig.supporting_quotes[0] if sig.supporting_quotes else "(no quote)",
                    })
                    needs_llm_check = True

        if needs_llm_check:
            logger.info("[Critic] Stage 2: LLM consistency check …")
            note_texts_by_label = {
                sig.note_label: text for sig, text in zip(signals, note_texts)
            }
            prompt = _build_consistency_prompt(
                mismatches, affirmative_claims, note_texts_by_label,
            )

            if prompt:
                system_prompt = (
                    "You are a clinical verification specialist for stuttering phenotyping. "
                    "Verify speech disfluency signal extractions according to clinical rules. "
                    "Respond only in valid JSON."
                )
                parsed_response = self.llm.get_structured(
                    system_prompt, prompt, VerificationResponseSchema, model=self.model,
                )
                self._apply_corrections(signals, parsed_response.verifications, all_issues)

        # Determine if re-extraction is needed
        significant_issues = [
            iss for iss in all_issues
            if iss.issue_type in (
                "signal_mismatch",
                "negation_error",
                "attribution_error",
                "non_speech_mismatch",
            )
        ]
        result.needs_re_extraction = len(significant_issues) > 0
        result.verified_signals = signals
        result.issues = all_issues

        logger.info(
            "[Critic] Verification complete: %d issues, re-extraction=%s",
            len(all_issues), result.needs_re_extraction,
        )
        return result

    def _apply_corrections(
        self,
        signals: List[NoteSignals],
        corrections: List[VerificationSchema],
        issues: List[CriticFeedback],
    ):
        """Apply LLM corrections to signals and log issues."""
        sig_by_label = {s.note_label: s for s in signals}

        for corr in corrections:
            label = corr.note_label
            field_name = corr.field
            correct_value = corr.correct_value
            reasoning = corr.reasoning

            sig = sig_by_label.get(label)
            if not sig:
                continue

            current_value = getattr(sig, field_name, None)
            if current_value is None:
                continue

            curr_str = str(current_value).lower()
            corr_str = str(correct_value).lower()

            # Check if correction differs from current value
            if curr_str != corr_str:
                logger.info(
                    "[Critic] Correcting %s.%s: %s → %s (%s)",
                    label, field_name, current_value, correct_value, reasoning,
                )
                # Apply correction
                if field_name in ("slp_or_formal_assessment", "competing_condition"):
                    new_val = corr_str in ("true", "1", "yes")
                    setattr(sig, field_name, new_val)
                else:
                    setattr(sig, field_name, corr_str)

                # Assign appropriate issue type
                if "negat" in reasoning.lower() or field_name == "assertion":
                    issue_type = "negation_error"
                elif field_name == "subject_attribution":
                    issue_type = "attribution_error"
                elif field_name == "speech_context":
                    issue_type = "non_speech_mismatch"
                else:
                    issue_type = "signal_mismatch"

                issues.append(CriticFeedback(
                    note_label=label,
                    issue_type=issue_type,
                    description=f"{field_name}: {current_value} → {correct_value}. {reasoning}",
                ))

