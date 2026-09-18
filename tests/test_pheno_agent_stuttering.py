"""
test_pheno_agent_stuttering.py
-------------------------------
Unit and integration tests for PhenoAgent configured for Stuttering phenotyping
(developmental & persistent speech disfluency), ensuring lab values are disabled
and all clinical rules from stuttering_rules.md and stuttering_keywords.yaml
are properly enforced across all agents.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure src/ is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pheno_agent.config import cfg
from pheno_agent.tools.keyword_scanner import (
    KeywordSignals,
    _aggregate_decisions as kw_aggregate_decisions,
    scan_note_for_keywords,
    scan_patient_notes,
)
from pheno_agent.agents.signal_extractor import (
    CriticFeedback,
    NoteSignals,
    NoteSignalSchema,
)
from pheno_agent.agents.critic import (
    Critic,
    VerificationSchema,
    _find_signal_mismatches,
    _fuzzy_contains,
    _verify_quotes,
)
from pheno_agent.agents.adjudicator import (
    Adjudicator,
    FinalDiagnosis,
    NoteDecision,
    apply_decision_table,
    aggregate_decisions,
)
from pheno_agent.agents.data_gatherer import DataGatherer, PatientDossier
from pheno_agent.orchestrator import Orchestrator
from pheno_agent.tools.ehr_reader import NoteEntry, ParsedEHR


class TestConfigForStuttering(unittest.TestCase):
    """Verify PhenoAgent config is properly set for stuttering without labs."""

    def test_phenotype_and_labs_settings(self):
        self.assertEqual(cfg.phenotype, "stuttering")
        self.assertFalse(cfg.use_labs, "use_labs must be False for stuttering")
        self.assertIsNone(cfg.lab_csv_path, "lab_csv_path must be None for stuttering")

    def test_paths_exist(self):
        self.assertTrue(cfg.keywords_path.exists(), f"Missing: {cfg.keywords_path}")
        self.assertTrue(cfg.diagnosis_logic_path.exists(), f"Missing: {cfg.diagnosis_logic_path}")


class TestKeywordScannerStuttering(unittest.TestCase):
    """Verify keyword scanning matches the stuttering clinical rules."""

    def test_positive_affirmative_speech(self):
        note = "4-year-old child presents with frequent stuttering during conversation with mother."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.has_primary)
        self.assertTrue(sig.has_speech_context or sig.has_confirmatory)
        self.assertFalse(sig.is_negated)
        self.assertFalse(sig.is_family_history_only)
        self.assertEqual(sig.decision, "Positive")

    def test_positive_formal_assessment_slp(self):
        note = "Patient referred to speech-language pathologist for formal fluency evaluation. SSI-4 score was elevated."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.has_slp_or_formal)
        self.assertEqual(sig.decision, "Positive")

    def test_negative_explicit_negation(self):
        note = "Speech is fluent without stutter. Mother denies stuttering or speech disfluency."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.is_negated)
        self.assertEqual(sig.decision, "Negative")

    def test_excluded_non_speech_jargon(self):
        note = "Neurological exam: patient demonstrated a stuttering gait after the stroke."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.is_non_speech_exclusion)
        self.assertEqual(sig.decision, "Excluded")

    def test_excluded_family_history_only(self):
        note = "Family history: father stutters. Patient has normal speech milestones."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.is_family_history_only)
        self.assertEqual(sig.decision, "Excluded")

    def test_excluded_competing_condition(self):
        note = "Patient with acute psychosis and schizophrenia showing severe formal thought disorder and clanging speech."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.is_competing_condition)
        self.assertEqual(sig.decision, "Excluded")

    def test_indeterminate_ambiguous_mention(self):
        note = "Review of systems: stutter noted."
        sig = scan_note_for_keywords(note)
        self.assertTrue(sig.has_primary)
        self.assertEqual(sig.decision, "Indeterminate")

    def test_patient_level_aggregation(self):
        notes = [
            "Neurological exam showed stuttering gait.",  # Excluded
            "Father stutters. Child was seen for checkup.", # Excluded
            "Speech therapy referral for persistent developmental stuttering.", # Positive
        ]
        report = scan_patient_notes(notes, grid="TEST_PATIENT_01")
        self.assertEqual(report.aggregated_decision, "Positive")
        self.assertEqual(len(report.per_note), 3)


class TestAdjudicatorDecisionTable(unittest.TestCase):
    """Verify Section 3 decision table and longitudinal synthesis."""

    def test_decision_table_exclusions(self):
        # 1. Non-speech
        sig_non_speech = NoteSignals(
            note_label="Note_1", note_date="2020-01-01",
            speech_context="non_speech", assertion="affirmative",
        )
        nd = apply_decision_table(sig_non_speech)
        self.assertEqual(nd.decision, "Excluded")
        self.assertIn("Non-speech", nd.rule)

        # 2. Family history only
        sig_fh = NoteSignals(
            note_label="Note_2", note_date="2020-01-02",
            speech_context="speech", subject_attribution="family_only", assertion="affirmative",
        )
        nd = apply_decision_table(sig_fh)
        self.assertEqual(nd.decision, "Excluded")
        self.assertIn("Family history", nd.rule)

        # 3. Competing condition
        sig_competing = NoteSignals(
            note_label="Note_3", note_date="2020-01-03",
            speech_context="speech", subject_attribution="patient",
            assertion="affirmative", competing_condition=True,
        )
        nd = apply_decision_table(sig_competing)
        self.assertEqual(nd.decision, "Excluded")
        self.assertIn("psychosis", nd.rule)

    def test_decision_table_negations(self):
        sig_neg = NoteSignals(
            note_label="Note_1", note_date="2020-01-01",
            speech_context="speech", subject_attribution="patient",
            assertion="negated",
        )
        nd = apply_decision_table(sig_neg)
        self.assertEqual(nd.decision, "Negative")

        sig_ruled_out = NoteSignals(
            note_label="Note_2", note_date="2020-01-02",
            speech_context="speech", subject_attribution="patient",
            assertion="ruled_out",
        )
        nd = apply_decision_table(sig_ruled_out)
        self.assertEqual(nd.decision, "Negative")

    def test_decision_table_positives(self):
        # SLP assessment
        sig_slp = NoteSignals(
            note_label="Note_1", note_date="2020-01-01",
            speech_context="speech", subject_attribution="patient",
            assertion="affirmative", slp_or_formal_assessment=True,
        )
        nd = apply_decision_table(sig_slp)
        self.assertEqual(nd.decision, "Positive")
        self.assertIn("SLP", nd.rule)

        # Clinical documentation
        sig_clin = NoteSignals(
            note_label="Note_2", note_date="2020-01-02",
            speech_context="speech", subject_attribution="patient",
            assertion="affirmative", slp_or_formal_assessment=False,
        )
        nd = apply_decision_table(sig_clin)
        self.assertEqual(nd.decision, "Positive")

    def test_decision_table_indeterminate_and_negative(self):
        sig_ind = NoteSignals(
            note_label="Note_1", note_date="2020-01-01",
            stuttering_mentioned=True, speech_context="not_found", assertion="ambiguous",
        )
        nd = apply_decision_table(sig_ind)
        self.assertEqual(nd.decision, "Indeterminate")

        sig_none = NoteSignals(note_label="Note_2", note_date="2020-01-02")
        nd = apply_decision_table(sig_none)
        self.assertEqual(nd.decision, "Negative")

    def test_longitudinal_synthesis(self):
        # Positive persists even if later notes are fluent/negative
        self.assertEqual(aggregate_decisions(["Positive", "Negative", "Negative"]), "Positive")
        # Indeterminate over negative
        self.assertEqual(aggregate_decisions(["Indeterminate", "Negative"]), "Indeterminate")
        # Excluded over negative when no positive/indeterminate
        self.assertEqual(aggregate_decisions(["Excluded", "Negative"]), "Excluded")
        # All negative
        self.assertEqual(aggregate_decisions(["Negative", "Negative"]), "Negative")

    def test_adjudicator_bypasses_labs(self):
        mock_llm = MagicMock()
        mock_llm.get_completion.return_value = "Patient has confirmed developmental stuttering."
        adjudicator = Adjudicator(llm=mock_llm)

        signals = [
            NoteSignals(
                note_label="Note_1", note_date="2018-05-10",
                stuttering_mentioned=True, speech_context="speech",
                subject_attribution="patient", assertion="affirmative",
                slp_or_formal_assessment=True, supporting_quotes=["severe stuttering"],
            )
        ]
        diagnosis = adjudicator.adjudicate(
            grid="R12345",
            verified_signals=signals,
            lab_summary=None,
            keyword_decision="Positive",
        )
        self.assertEqual(diagnosis.diagnosis, "Positive")
        self.assertEqual(diagnosis.lab_decision, "not_applicable")
        self.assertGreater(diagnosis.confidence, 0.90)


class TestCriticVerification(unittest.TestCase):
    """Verify quote checking and stuttering mismatch detection in Critic."""

    def test_quote_verification(self):
        note_text = "Patient was observed with part-word repetitions and stuttering during speech evaluation."
        real_sig = NoteSignals(
            note_label="Note_1",
            supporting_quotes=["part-word repetitions and stuttering"],
        )
        phantom_sig = NoteSignals(
            note_label="Note_2",
            supporting_quotes=["severe villous blunting and IEL elevation"],
        )

        issues = _verify_quotes([real_sig], [note_text])
        self.assertEqual(len(issues), 0)

        issues = _verify_quotes([phantom_sig], [note_text])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].issue_type, "phantom_quote")

    def test_find_signal_mismatches(self):
        # 1. Non-speech exclusion mismatch
        kw_exclusion = KeywordSignals(is_non_speech_exclusion=True)
        llm_signal_missed = NoteSignals(note_label="Note_1", speech_context="speech")
        mismatches = _find_signal_mismatches([llm_signal_missed], [kw_exclusion])
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["field"], "speech_context")

        # 2. Family history mismatch
        kw_fh = KeywordSignals(is_family_history_only=True)
        llm_fh_missed = NoteSignals(note_label="Note_2", subject_attribution="patient")
        mismatches = _find_signal_mismatches([llm_fh_missed], [kw_fh])
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["field"], "subject_attribution")

        # 3. Negation mismatch
        kw_neg = KeywordSignals(is_negated=True)
        llm_affirmative = NoteSignals(note_label="Note_3", assertion="affirmative")
        mismatches = _find_signal_mismatches([llm_affirmative], [kw_neg])
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["field"], "assertion")

    def test_critic_apply_corrections(self):
        mock_llm = MagicMock()
        critic = Critic(llm=mock_llm)

        sig = NoteSignals(
            note_label="Note_1",
            speech_context="speech",
            subject_attribution="patient",
            assertion="affirmative",
            slp_or_formal_assessment=False,
            competing_condition=False,
        )

        corrections = [
            VerificationSchema(
                note_label="Note_1",
                field="speech_context",
                correct_value="non_speech",
                reasoning="Note describes stuttering angina, not speech.",
            ),
            VerificationSchema(
                note_label="Note_1",
                field="subject_attribution",
                correct_value="family_only",
                reasoning="Mentions father has stuttering history.",
            ),
        ]

        issues = []
        critic._apply_corrections([sig], corrections, issues)

        self.assertEqual(sig.speech_context, "non_speech")
        self.assertEqual(sig.subject_attribution, "family_only")
        self.assertEqual(len(issues), 2)


class TestDataGathererWithoutLabs(unittest.TestCase):
    """Verify DataGatherer does not invoke labs when use_labs is False."""

    def test_gather_skips_labs(self):
        gatherer = DataGatherer(use_chroma=False)
        fake_parsed = ParsedEHR(
            grid="R99999",
            notes=[
                NoteEntry(
                    date="2021-03-15",
                    title="Pediatric Encounter",
                    source="Pediatrics",
                    text="Child presents with stuttering since age 3.",
                )
            ]
        )
        with patch("pheno_agent.agents.data_gatherer.read_patient_ehr", return_value="raw markdown"), \
             patch("pheno_agent.agents.data_gatherer.parse_ehr_sections", return_value=fake_parsed):
            dossier = gatherer.gather("R99999")

            self.assertIsNone(dossier.lab_summary, "lab_summary must be None when use_labs=False")
            self.assertEqual(len(dossier.relevant_notes), 1)
            self.assertIsNotNone(dossier.keyword_report)


class TestOrchestratorIntegration(unittest.TestCase):
    """Verify Orchestrator runs full stuttering diagnostic flow without lab dependency."""

    def test_signal_to_dict_stuttering_schema(self):
        mock_llm = MagicMock()
        orchestrator = Orchestrator(use_chroma=False)

        sig = NoteSignals(
            note_label="Note_1",
            note_date="2020-04-01",
            note_type="Clinic Note",
            stuttering_mentioned=True,
            speech_context="speech",
            subject_attribution="patient",
            assertion="affirmative",
            slp_or_formal_assessment=True,
            competing_condition=False,
            supporting_quotes=["referred for speech therapy"],
        )

        d = orchestrator._signal_to_dict(sig)
        self.assertEqual(d["note_label"], "Note_1")
        self.assertTrue(d["stuttering_mentioned"])
        self.assertEqual(d["speech_context"], "speech")
        self.assertEqual(d["subject_attribution"], "patient")
        self.assertEqual(d["assertion"], "affirmative")
        self.assertTrue(d["slp_or_formal_assessment"])
        self.assertFalse(d["competing_condition"])
        self.assertEqual(d["supporting_quotes"], ["referred for speech therapy"])

    def test_diagnose_patient_flow(self):
        orchestrator = Orchestrator(use_chroma=False)

        # Mock DataGatherer
        fake_note = NoteEntry(
            date="2019-09-20",
            title="Speech Evaluation",
            source="ENT / Speech",
            text="Patient presents for speech disfluency. Evaluated with SSI-4 showing moderate stuttering.",
        )
        mock_dossier = PatientDossier(
            grid="RTEST123",
            parsed_ehr=ParsedEHR(
                grid="RTEST123",
                notes=[fake_note]
            ),
            relevant_notes=[fake_note],
            lab_summary=None,
        )

        # Mock SignalExtractor to return affirmative stuttering signal
        extracted_signals = [
            NoteSignals(
                note_label="Note_1",
                note_date="2019-09-20",
                note_type="ENT / Speech",
                stuttering_mentioned=True,
                speech_context="speech",
                subject_attribution="patient",
                assertion="affirmative",
                slp_or_formal_assessment=True,
                competing_condition=False,
                supporting_quotes=["Evaluated with SSI-4 showing moderate stuttering"],
            )
        ]

        from pheno_agent.agents.critic import VerificationResult

        with patch.object(orchestrator.data_gatherer, "gather", return_value=mock_dossier), \
             patch.object(orchestrator.signal_extractor, "extract", return_value=extracted_signals), \
             patch.object(orchestrator.critic, "verify", return_value=VerificationResult(verified_signals=extracted_signals)), \
             patch.object(orchestrator.adjudicator, "_generate_reasoning", return_value="Confirmed stuttering by SLP evaluation."):

            result = orchestrator.diagnose_patient("RTEST123")

            self.assertEqual(result["grid"], "RTEST123")
            self.assertEqual(result["diagnosis"], "Positive")
            self.assertEqual(result["lab_decision"], "not_applicable")
            self.assertGreater(result["confidence"], 0.8)
            self.assertIn("Confirmed stuttering", result["reasoning"])


if __name__ == "__main__":
    unittest.main()
