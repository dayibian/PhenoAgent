# Manuscript Structure & Paragraph-by-Paragraph Outline

**Working Title:**  
*PhenoAgent: A Disease-Agnostic, Reflective Multi-Agent Framework for Interpretable Clinical Phenotyping from Electronic Health Records Across Histopathologic and Behavioral Cohorts*

**Alternative Title:**  
*Automated Clinical Phenotyping via Reflective Multi-Agent LLMs: Validation Across Celiac Disease and Childhood-Onset Stuttering in Electronic Health Records*

---

## Target Journals Under Consideration
- **Primary Informatics Targets:**
  - *Journal of the American Medical Informatics Association (JAMIA)*
  - *Journal of Biomedical Informatics (JBI)*
  - *npj Digital Medicine*
  - *IEEE Journal of Biomedical and Health Informatics (JBHI)*
- **Broad Biomedical & Clinical AI Targets:**
  - *The Lancet Digital Health*
  - *PLOS Digital Health*
  - *Computers in Biology and Medicine*

---

## Manuscript Overview & Structural Blueprint

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  TITLE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                 ABSTRACT                                    │
│   (Background, Objective, Methods, Results, Discussion, Conclusion)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. INTRODUCTION                                                             │
│   1.1 The Centrality and Challenges of EHR Phenotyping                      │
│   1.2 Limitations of Existing Rule-Based and Machine Learning Approaches    │
│   1.3 The Promise and Pitfalls of LLMs in Clinical Decision Support         │
│   1.4 The Multi-Agent and Reflective Synergy: Rationale for PhenoAgent      │
│   1.5 Dual-Cohort Evaluation Strategy & Study Objectives                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. METHODS                                                                  │
│   2.1 Overall System Architecture and Design Principles                     │
│   2.2 Multi-Agent Personas and Reflection Workflow                          │
│   2.3 Tool Subsystem: Ingestion, Date-Aware Labs, & Negation Screening      │
│   2.4 Disease-Agnostic Configuration & Extensibility Paradigm               │
│   2.5 Cohort Selection & Phenotype Definitions (Celiac & Stuttering)        │
│   2.6 Baseline Comparators, Experimental Protocol, & Evaluation Metrics     │
│   2.7 Privacy-Preserving Local Inference & Computational Infrastructure     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. RESULTS                                                                  │
│   3.1 Celiac Disease Phenotyping: Histopathology, Labs, & Legacy Challenges │
│   3.2 Stuttering Phenotyping: Clinical Yield & Standardized Evidence        │
│   3.3 Discordance Analysis & Error Corrections vs. Heuristic Baselines      │
│   3.4 Ablation Studies: Impact of Critic Verification & Reflection Loops    │
│   3.5 Computational Scalability, Latency, & Local Model Feasibility         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. DISCUSSION                                                               │
│   4.1 Principal Findings and Methodological Advances                        │
│   4.2 Cross-Domain Generalizability: Pathology vs. Behavioral Phenotyping   │
│   4.3 Transparency, Auditability, and Neuro-Symbolic Governance             │
│   4.4 Privacy-First Local Deployment in Clinical Environments               │
│   4.5 Limitations & Practical Implementation Barriers                       │
│   4.6 Future Research Directions                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. CONCLUSION                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ DECLARATIONS & SUPPLEMENTARY MATERIAL                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Section-by-Section and Paragraph-by-Paragraph Summaries

### Abstract
*(Structured format: ~250–300 words)*
- **Paragraph 1 (Background & Objective):** State the vital importance of clinical phenotyping from Electronic Health Records (EHRs) for precision medicine, observational research, and clinical trials. Frame the central dilemma: manual chart review is cost-prohibitive and unscalable, while conventional rule-based or black-box NLP approaches suffer from fragility, poor generalizability, or unacceptable hallucination rates. Introduce PhenoAgent as an open-source, reflective multi-agent system executing locally offline.
- **Paragraph 2 (Methods):** Summarize the four-agent architecture (DataGatherer, SignalExtractor, Critic, Adjudicator) featuring a closed-loop corrective reflection cycle and deterministic clinical decision tables. Explain the dual-cohort validation across two distinct clinical phenotypes: (1) Celiac Disease (a multi-modal histopathologic and serologic phenotype with date-aware lab cutoffs and Marsh scoring) and (2) Stuttering / Fluency Disorder (a longitudinal neurodevelopmental behavioral phenotype reliant on free-text narratives, psychometric instruments, and family-history disambiguation). Mention local open-weight LLM execution (Qwen series via Ollama).
- **Paragraph 3 (Results):** Present key quantitative findings across both cohorts. Highlight the high precision and resolution in the stuttering cohort (363 patients evaluated: 97.5% positive, 1.7% negative, 0.8% excluded, 0.0% indeterminate), with >85% of positive cases backed by formal SLP documentation or standardized metrics (SSI-3/4, OASES, %SS), and 10 cases (2.75%) rescued from heuristic misclassification. Detail celiac evaluation results against clinician-verified ground truth, illustrating how multi-agent reflection isolates biopsy-confirmed pathology from legacy problem list noise.
- **Paragraph 4 (Conclusion):** Conclude that PhenoAgent achieves high diagnostic fidelity, explainability, and full HIPAA compliance by combining probabilistic LLM extraction with deterministic rule governance and local inference. Emphasize its disease-agnostic extensibility across disparate clinical disciplines without model retraining.

---

### 1. Introduction

#### 1.1 The Centrality and Challenges of EHR Phenotyping
- **Paragraph 1:** *The Foundational Role of Clinical Phenotyping.*  
  Establish the critical function of EHR-based phenotyping in modern biomedicine—serving as the cornerstone for genome-wide association studies (GWAS), phenome-wide association studies (PheWAS), pragmatic clinical trial recruitment, and longitudinal epidemiological tracking. Discuss how high-throughput, accurate cohort identification directly impacts downstream translational discoveries.
- **Paragraph 2:** *The Structured vs. Unstructured Data Divide.*  
  Elaborate on the persistent bottleneck in clinical data: structured billing codes (ICD-9/10, CPT) exhibit low sensitivity, variable specificity, and substantial administrative billing bias. The rich, definitive clinical evidence—such as histopathologic interpretations, physical exam findings, family history nuances, and behavioral assessments—remains locked within unstructured narrative progress notes and consultation reports.

#### 1.2 Limitations of Existing Phenotyping Methodologies
- **Paragraph 3:** *Brittleness of Handcrafted Rule-Based Systems.*  
  Analyze traditional rule-based algorithms (e.g., PheKB, eMERGE). While highly specific and transparent, they require extensive multi-site manual engineering, depend on rigid regular expressions, and systematically fail when encountering complex clinical linguistics, typographical variants, subtle negations, or cross-specialty syntactic variation.
- **Paragraph 4:** *Opacity and Resource Demands of Supervised Machine Learning.*  
  Examine supervised deep learning and specialized biomedical transformer models (e.g., BioBERT, ClinicalBERT). Detail their dependence on massive, labor-intensive expert-annotated training sets, their susceptibility to distribution shifts between health systems, and their fundamental "black-box" opacity that limits clinical trust and regulatory auditability.

#### 1.3 Large Language Models in Clinical NLP: Potential and Perils
- **Paragraph 5:** *Zero-Shot Reasoning vs. Clinical Hallucination.*  
  Acknowledge the transformative linguistic comprehension of modern LLMs. Discuss how zero-shot or single-prompt LLMs can parse complex clinical narratives, yet present major clinical hazards: hallucinations, fabrication of clinical evidence ("phantom quotes"), inconsistent diagnostic boundaries, and vulnerability to context window saturation across long longitudinal records.
- **Paragraph 6:** *The Institutional Privacy and Deployment Barrier.*  
  Highlight the governance, legal, and ethical roadblocks of transmitting sensitive Protected Health Information (PHI) to commercial cloud-based LLM APIs (e.g., OpenAI, Anthropic). Emphasize the acute necessity for high-performing, open-weight models that execute entirely on-premise within hospital firewalls.

#### 1.4 The Multi-Agent and Reflective Synergy
- **Paragraph 7:** *Agentic Decomposition as a Clinical Consensus Paradigm.*  
  Introduce the conceptual foundation of multi-agent architectures in healthcare: decomposing a complex clinical evaluation into specialized, role-governed personas (data aggregation, signal extraction, peer critique, and diagnostic adjudication), mimicking real-world clinical consensus panels and multidisciplinary tumor boards.
- **Paragraph 8:** *Corrective Reflection as a Safeguard Against Hallucination.*  
  Explain the mechanism of reflection loops between extractor and critic agents. By combining deterministic string verification (ground-truth quote matching against source notes) with targeted LLM reasoning, the system establishes a self-correcting verification cycle that filters errors prior to final clinical decision-making.

#### 1.5 Study Objectives and the Dual-Cohort Evaluation Strategy
- **Paragraph 9:** *PhenoAgent: Design Principles and Innovation.*  
  Introduce PhenoAgent: an open-source, disease-agnostic, reflective multi-agent system designed for automated clinical phenotyping. State its core pillars: privacy-first on-premise inference, externalized clinician-authored rules, neuro-symbolic governance, and full evidentiary auditability.
- **Paragraph 10:** *Rationale for the Celiac and Stuttering Cohort Selection.*  
  Articulate the deliberate selection of two contrasting clinical domains to rigorously test generalizability:  
  1. *Celiac Disease*: A multi-modal, laboratory- and histopathology-driven internal medicine condition requiring integration of date-aware serological thresholds (TTG-IgA), microscopic biopsy grades (Marsh stages, villous atrophy, IEL proliferation), and management of confounding therapy-induced remission (mucosal healing on a gluten-free diet).  
  2. *Stuttering (Childhood-Onset Fluency Disorder)*: A longitudinal behavioral and neurodevelopmental condition documented primarily in unstructured speech-language pathology (SLP) notes, requiring extraction of psychometric scores (SSI-3/4, OASES, %SS), disambiguation of family-member attributions, and separation of true disfluency from administrative referral noise and non-speech homonyms.  
  Conclude with a clear statement of the paper's specific contributions.

---

### 2. Methods

#### 2.1 Overall System Architecture & Design Principles
- **Paragraph 11:** *End-to-End Orchestrated Pipeline.*  
  Provide a comprehensive architectural walkthrough (referencing Figure 1). Describe how a central, non-LLM Orchestrator coordinates the pipeline flow per patient: starting with structured data and narrative compilation, moving through extraction, entering an iterative reflection loop, and concluding with deterministic adjudication and narrative clinical justification.
- **Paragraph 12:** *Neuro-Symbolic Design Philosophy.*  
  Detail the conceptual coupling of probabilistic deep learning (LLMs) with deterministic symbolic logic (rule tables, regex pre-screening, fuzzy quote matching). Emphasize how this separation ensures that probabilistic models are restricted to language comprehension and signal extraction, while diagnostic governance remains strictly deterministic and clinician-defined.

#### 2.2 Multi-Agent Personas and Reflection Workflow
- **Paragraph 13:** *Agent 1: DataGatherer.*  
  Detail the operations of the deterministic DataGatherer agent. Explain its role in parsing patient EHR records into structured entries, querying date-aware laboratory databases, executing negation-aware keyword pre-screening, and filtering high-yield notes to maximize LLM context efficiency without omitting diagnostic signals.
- **Paragraph 14:** *Agent 2: SignalExtractor.*  
  Describe the LLM-powered SignalExtractor. Explain the injection of in-context clinician guidance (disease definitions, scoring rubrics, negation rules) into structured prompts. Describe the enforcement of strict JSON schemas via Pydantic and Outlines, note-batching strategies, and the mandatory extraction of verbatim supporting quotes from source notes.
- **Paragraph 15:** *Agent 3: Critic (Hybrid Verification & Reflection Loop).*  
  Describe the two-phase Critic agent:  
  - *Phase 1 (Deterministic)*: Sliding-window fuzzy string matching (`SequenceMatcher`, threshold ≥ 0.75) against source text to flag and discard "phantom quotes" and ungrounded claims.  
  - *Phase 2 (Reasoning LLM)*: Contextual conflict resolution (resolving keyword vs. LLM discordance, checking negation status, and verifying past-diagnosis claims).  
  Explain the reflection loop triggering condition (`needs_re_extraction = True`) and targeted re-prompting of the extractor up to a configured limit.
- **Paragraph 16:** *Agent 4: Adjudicator (Deterministic Decision Tables & Clinical Rationale).*  
  Detail the Adjudicator’s dual-phase workflow. Phase 1 applies a priority-ordered, clinician-authored decision table to map verified signals to per-note and patient-level classifications (Dominance: Positive > Excluded > Indeterminate > Negative). Phase 2 invokes the reasoning LLM to synthesize an audit-ready, citation-grounded clinical narrative detailing the exact decision path.

#### 2.3 Supporting Tool Subsystem
- **Paragraph 17:** *EHR Reader and Markdown Parser.*  
  Describe the parsing engine that processes longitudinal EHR files containing dated clinical encounters, specialty consultation notes, and laboratory logs into strongly typed data models (`NoteEntry`, `LabEntry`, `ParsedEHR`).
- **Paragraph 18:** *Lab Lookup with Date-Aware Clinical Thresholds.*  
  Explain the laboratory lookup tool designed for serological assays. Emphasize its date-segmented logic, which handles historical assay platform upgrades and reference range shifts over multi-decade EHR records (exemplified by TTG-IgA cutoffs in celiac diagnosis).
- **Paragraph 19:** *Negation-Aware Keyword Pre-Screener.*  
  Detail the algorithm of the high-speed regex pre-screener: explain the critical pre-processing step where negative/normal syntactic patterns are excised from text before positive matching to eliminate false positives in negated contexts (e.g., "no evidence of villous blunting").
- **Paragraph 20:** *Optional Semantic Vector Retrieval (ChromaDB).*  
  Briefly outline the optional vector retrieval module utilizing BioClinicalBERT embeddings within ChromaDB, explaining the multi-query retrieval strategy and the framework's graceful degradation to direct file reading when embeddings are unindexed.

#### 2.4 Disease-Agnostic Extensibility Paradigm
- **Paragraph 21:** *Externalized Clinical Configuration.*  
  Highlight how PhenoAgent completely separates software architecture from medical domain knowledge. Detail the five external configuration artifacts: (1) YAML keyword dictionaries, (2) Markdown clinical guidance documents, (3) Pydantic extraction schemas, (4) Python decision tables, and (5) structured lab cutoffs. Explain how switching phenotypes requires zero modifications to core agent orchestration code.

#### 2.5 Clinical Cohorts and Phenotype Definitions
- **Paragraph 22:** *Institutional Data Source (BioVU).*  
  Describe the institutional setting and data provenance: longitudinal records from Vanderbilt University Medical Center’s synthetic/de-identified BioVU repository, detailing record spans (over 20+ years), note formats, and privacy protections.
- **Paragraph 23:** *Cohort 1: Celiac Disease Cohort Design.*  
  Define the clinical phenotyping rules for Celiac Disease: serological criteria (TTG-IgA positive override), histopathological biopsy requirements (Marsh III lesions, intraepithelial lymphocytosis, villous atrophy), and the handling of dietary remission (normal biopsies in patients established on a gluten-free diet). Describe the evaluation set (N=151 control cohort with N=99 clinician-annotated ground-truth labels).
- **Paragraph 24:** *Cohort 2: Stuttering (Fluency Disorder) Cohort Design.*  
  Define the clinical phenotyping rules for Stuttering based on Pruett et al. (2021) and Shaw et al. (2021): positive criteria (physician/SLP formal diagnosis, standardized scoring with SSI-3, SSI-4, OASES, or elevated %SS, affirmative pediatric well-child observations); negative criteria (explicit clinical rule-out, <3% disfluency, complete absence of signal); and explicit exclusion criteria (family-history-only attribution, non-speech homonyms such as stuttering angina/priapism, and colloquial psychotic speech). Describe the cohort size (N=363 evaluated / 1,132 total cohort).

#### 2.6 Comparative Baselines and Evaluation Protocol
- **Paragraph 25:** *Baseline Comparators.*  
  Define the comparative baselines: (1) Rule-based / Regex Keyword Scanner, (2) Monolithic Zero-Shot LLM (single prompt asking for diagnosis and reasoning without agent decomposition or reflection), and (3) Expert Clinician Chart Review (gold standard ground truth).
- **Paragraph 26:** *Quantitative Performance Metrics & Statistical Evaluation.*  
  Enumerate evaluation metrics: Sensitivity (Recall), Specificity, Positive Predictive Value (Precision), Negative Predictive Value, Overall Accuracy, F1-Score (macro and weighted), Indeterminate Rate, and Quote Hallucination Rate (percentage of phantom quotes detected). Detail 95% confidence intervals and inter-annotator agreement metrics where applicable.

#### 2.7 Computational Infrastructure and Privacy-Preserving Deployment
- **Paragraph 27:** *Local LLM Orchestration via Ollama.*  
  Describe the local software and hardware deployment: local GPU workstations running Ollama, model role assignments (e.g., Qwen 2.5/3.6/3.8 series for extraction and reasoning), multi-instance load balancing via SSH-tunneled Ollama instances, parallel patient-level sharding, and checkpoint resumption.

---

### 3. Results

#### 3.1 Celiac Disease Phenotyping: Histopathology, Labs, & Legacy Challenges
- **Paragraph 28:** *Overall Benchmark Performance on Celiac Controls.*  
  Present diagnostic performance across the N=99 ground-truth celiac control sample. Report sensitivity, specificity, precision, recall, and overall accuracy. Highlight that the agent achieved 100% precision for true negative rule-outs when pathology and serology were concordant.
- **Paragraph 29:** *Multimodal Integration of Date-Aware Labs and Biopsies.*  
  Demonstrate the efficacy of the date-aware TTG-IgA lab lookup tool in concert with biopsy parsing. Show how cases with definitive high-titer serology were accurately triaged without unnecessary narrative computation, while borderline titers were correctly routed to narrative histopathologic extraction.
- **Paragraph 30:** *Detailed Error Analysis & The Problem of Legacy Diagnoses.*  
  Examine the 38 false-positive cases identified in the control evaluation. Provide a deep dive into EHR epidemiology: explain how patients carried unverified legacy ICD codes ("Celiac sprue", 579.0) or self-reported gluten avoidance in problem lists despite negative serology and normal duodenal histology. Show how PhenoAgent's transparent reasoning trace enabled rapid clinical auditing and subsequent refinement of legacy past-diagnosis override rules.

#### 3.2 Stuttering Phenotyping: High Yield and Standardized Clinical Evidence
- **Paragraph 31:** *Phenotype Distribution and Confidence Metrics.*  
  Present the comprehensive evaluation of the 363-patient stuttering cohort (354 Positive [97.5%], 6 Negative [1.7%], 3 Excluded [0.8%], 0 Indeterminate [0.0%]). Highlight that 100% of cases were resolved with high mean diagnostic confidence (Positive: 0.95, Excluded: 0.85, Negative: 0.80).
- **Paragraph 32:** *Standardized Diagnostic Instrument Capture.*  
  Quantify the clinical evidence supporting positive stuttering cases. Report that >85% of positive adjudications were substantiated by formal Speech-Language Pathologist (CCC-SLP) notes, standardized instrument scores (SSI-3, SSI-4, OASES), percent syllables stuttered (%SS), or enrollment in structured speech therapy programs (e.g., Parent-Child Stuttering Group).
- **Paragraph 33:** *Preservation of Longitudinal Diagnostic History.*  
  Demonstrate PhenoAgent’s ability to synthesize multi-decade longitudinal records: showing how early childhood-onset disfluencies were appropriately preserved as Positive lifetime phenotypes even when late-adolescent or adult progress notes documented normal, fluent speech.

#### 3.3 Discordance Analysis: PhenoAgent Corrections Over Heuristic Baselines
- **Paragraph 34:** *Summary of Heuristic Discrepancies.*  
  Present the comparative discordance analysis between the baseline keyword scanner and PhenoAgent. Highlight that PhenoAgent corrected 10 out of 363 patients (2.75%), preventing significant cohort contamination and misclassification that would occur under naive keyword/regex phenotyping (referencing Table 3).
- **Paragraph 35:** *Disambiguation of Familial Contexts (Exclusions).*  
  Examine the 3 Excluded patients (e.g., `R249876813`, `R212618220`, `R257016144`). Detail how PhenoAgent recognized that stuttering keywords across longitudinal records referred exclusively to parents or relatives (e.g., father required speech therapy, mother has language barrier due to stuttering), while the patients themselves were documented as fluent—saving 3 false positives.
- **Paragraph 36:** *Correction of Administrative and Referral False Positives (Negatives).*  
  Examine the 6 Negative classifications. Detail how PhenoAgent correctly parsed formal clinical rule-outs (<3% disfluency within normal developmental limits, e.g., `R250115464`), and separated general SLP orders for articulation delay (DX 315.39) or audiology CPT billing codes from genuine stuttering cases (e.g., `R260607966`, `R260516492`).
- **Paragraph 37:** *Affirmative Pediatric Case Rescue.*  
  Examine case `R249838817`, where a patient who stuttered was misclassified as Negative by regex heuristics due to co-occurring family mentions and maternal non-concern. Detail how the LLM extractor and critic accurately parsed the pediatric developmental context to rescue the true positive case.

#### 3.4 Ablation Studies: Value of the Critic and Reflection Loop
- **Paragraph 38:** *Suppression of Hallucinated and Phantom Quotes.*  
  Present ablation results comparing PhenoAgent with and without the Critic's deterministic sliding-window quote verification. Show the rate of phantom quotes in raw LLM extraction and demonstrate its reduction to 0% after Critic verification.
- **Paragraph 39:** *Resolution of Negation and Signal Contradictions.*  
  Quantify the frequency and convergence of the reflection loop. Report the percentage of cases requiring a second round of extraction (typically ~5–12%), and demonstrate that iterative reflection successfully resolved signal discrepancies between keywords and LLMs.

#### 3.5 Computational Feasibility and Latency Profiling
- **Paragraph 40:** *Inference Speed and Hardware Scalability.*  
  Report end-to-end runtime benchmarks: average processing time per patient across note volume distributions, GPU memory utilization under Ollama, and parallel throughput achieved across multi-GPU sharding configurations.

---

### 4. Discussion

#### 4.1 Principal Findings and Methodological Significance
- **Paragraph 41:** *Summary of Core Scientific Breakthrough.*  
  Reiterate that PhenoAgent successfully resolves the long-standing trade-off between semantic flexibility and rigorous clinical validity in EHR phenotyping. Emphasize that decomposing phenotyping into specialized, reflective agentic roles achieves expert-level accuracy without requiring task-specific fine-tuning or proprietary cloud APIs.
- **Paragraph 42:** *The Superiority of Neuro-Symbolic Governance.*  
  Contrast PhenoAgent's hybrid neuro-symbolic framework with end-to-end black-box LLM classifiers. Discuss why deterministic decision tables—grounded on verified, quoted textual evidence—provide the level of consistency, explainability, and regulatory reproducibility mandatory for clinical applications.

#### 4.2 Cross-Domain Generalizability: Lessons from Celiac and Stuttering
- **Paragraph 43:** *Navigating Multimodal Histopathologic Phenotypes (Celiac).*  
  Reflect on the complexities specific to celiac disease: managing multimodal data (serology + histology), resolving temporal changes due to therapeutic intervention (mucosal recovery on a gluten-free diet), and navigating administrative EHR artifacts such as unverified problem list carryover. Discuss the implications for phenotyping other autoimmune and gastrointestinal disorders (e.g., Crohn's disease, ulcerative colitis).
- **Paragraph 44:** *Navigating Narrative Behavioral and Neurodevelopmental Phenotypes (Stuttering).*  
  Reflect on the challenges unique to stuttering: the complete absence of laboratory biomarkers, heavy reliance on specialized clinical notes (SLP consultations), linguistic homonyms in non-speech domains, and the pervasive hazard of confusing familial risk factors with active patient diagnoses. Discuss how these insights generalize to autism spectrum disorder, ADHD, and psychiatric phenotypes.

#### 4.3 Auditability, Explainability, and Clinical Trust
- **Paragraph 45:** *The Role of Verbatim Quotes and Decision Traces.*  
  Argue that automated phenotyping tools must be audit-ready. Discuss how PhenoAgent's automated generation of comprehensive reasoning traces—linking every diagnostic label directly to timestamped, verified quotes from the source chart—dramatically accelerates secondary chart review and establishes trust among clinical investigators.
- **Paragraph 46:** *Automated Generation of Clinician Review Packets.*  
  Describe the practical utility of PhenoAgent's automated disagreement reporting (e.g., automated DOCX review packet generation). Show how targeting human clinical review specifically to low-confidence or discordant cases creates an efficient human-in-the-loop workflow.

#### 4.4 Privacy-Preserving On-Premise Clinical AI
- **Paragraph 47:** *The Imperative of Local Open-Weight Models in Healthcare.*  
  Contextualize PhenoAgent within the broader landscape of healthcare AI ethics and privacy. Emphasize that running modern open-weight LLMs locally via Ollama eliminates PHI leakage risks, complies with stringent HIPAA/GDPR constraints, and frees research institutions from prohibitive recurring API subscription costs.

#### 4.5 Limitations
- **Paragraph 48:** *Current Architectural and Data Limitations.*  
  Address the study’s limitations: (1) Dependence on pre-formatted markdown EHR text rather than native HL7/FHIR streaming protocols; (2) Latency overhead of multi-stage sequential agent LLM calls compared to simple regex; (3) Single-institution data source (BioVU); and (4) The persistent clinical challenge of adjudicating historical problem-list entries when primary diagnostic encounters occurred at outside hospital facilities.

#### 4.6 Future Directions
- **Paragraph 49:** *Multi-Phenotype Pipelines, FHIR Native Ingestion, and Active Learning.*  
  Outline future enhancements: extending the Orchestrator to phenotype dozens of co-morbid conditions simultaneously in a single pass over a patient's dossier; implementing native FHIR interoperability; integrating interactive active-learning interfaces where clinician feedback continuously updates domain keyword dictionaries and diagnostic rules; and incorporating temporal knowledge graphs.

---

### 5. Conclusion
- **Paragraph 50:** *Concluding Synthesis.*  
  Deliver a concise concluding statement affirming that PhenoAgent provides an open-source, disease-agnostic, and privacy-compliant paradigm for scalable, auditable EHR phenotyping. Reiterate that combining reflective agent verification with deterministic clinical logic paves the way for reliable, automated cohort identification across the spectrum of human disease.

---

## Declarations & Supplementary Material

- **Ethics Approval and Consent to Participate:** IRB compliance, de-identified/synthetic EHR governance (BioVU protocols).
- **Consent for Publication:** Not applicable (de-identified research dataset).
- **Availability of Data and Materials:** Code availability on GitHub; instructions for running PhenoAgent with Ollama; data access procedures for BioVU.
- **Competing Interests:** Disclosure of any financial or non-financial conflicts.
- **Funding:** Funding sources supporting computational infrastructure, trainees, or research grants.
- **Authors' Contributions:** CRediT taxonomy roles (Conceptualization, Methodology, Software, Validation, Formal Analysis, Investigation, Writing – Original Draft, Writing – Review & Editing, Supervision).
- **Acknowledgements:** Recognition of clinical collaborators, speech-language pathologists, and computing facilities.

---

## Planned Tables and Figures

### Figures
1. **Figure 1: End-to-End System Architecture of PhenoAgent.**  
   *Multi-agent workflow diagram illustrating DataGatherer, SignalExtractor, Critic reflection loop, and Adjudicator, highlighting local Ollama inference and external rule injection.*
2. **Figure 2: Deterministic Quote Verification and Hallucination Suppression.**  
   *Flowchart of the sliding-window fuzzy string matching algorithm (`SequenceMatcher`) differentiating verified vs. phantom quotes.*
3. **Figure 3: Dual-Cohort Phenotyping Logic and Signal Extraction Schemas.**  
   *Comparative schematic contrasting the multimodal histopathologic/serologic pipeline (Celiac) with the behavioral/SLP narrative pipeline (Stuttering).*
4. **Figure 4: Phenotype Distribution and Confidence Landscape in the Stuttering Cohort.**  
   *Distribution chart showing Positive (97.5%), Negative (1.7%), Excluded (0.8%), and Indeterminate (0.0%), broken down by mean confidence levels.*
5. **Figure 5: Heuristic Discrepancy Case Studies.**  
   *Visual decision-path walkthrough of representative corrected cases (e.g., family history exclusion vs. affirmative pediatric rescue).*

### Tables
1. **Table 1: System Comparison Across Clinical Phenotyping Paradigms.**  
   *Comparative matrix benchmarking PhenoAgent against Rule-based algorithms (PheKB), Supervised NLP (BERT), and Monolithic Zero-Shot LLMs (GPT-4) across interpretability, linguistic flexibility, privacy, and reflection.*
2. **Table 2: Celiac Disease Phenotyping Performance and Diagnostic Metrics.**  
   *Detailed performance metrics (Sensitivity, Specificity, Precision, Recall, Accuracy, F1) on the ground-truth control and case subsets.*
3. **Table 3: Discordance Analysis Between Keyword Pre-Screening and PhenoAgent in Stuttering.**  
   *Cross-tabulation of the 10 corrected discrepancy cases categorized by clinical mechanism (Family History, Formal Rule-Out, Administrative SLP billing, Pediatric Rescue).*
4. **Table 4: Ablation Analysis of the Critic Reflection Loop.**  
   *Quantitative impact of reflection cycles on phantom quote rates, signal consistency, and diagnostic flips.*
5. **Table 5: Computational Latency and Resource Utilization Benchmarks.**  
   *Per-patient runtime, GPU memory consumption, and parallel scaling metrics across local Ollama instances.*
