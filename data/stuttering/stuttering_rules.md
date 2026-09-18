# Clinical Phenotyping Rules: Stuttering (Developmental & Persistent Disfluency)

## 1. Core Decision Logic

Assign a patient phenotype outcome (`Positive`, `Negative`, `Indeterminate`, or `Excluded`) from EHR clinical notes using the following hierarchical criteria:

### **Positive** if any of the following are satisfied:
1. **Confirmed Clinical Diagnosis / Evaluation**:
   - Explicit clinical diagnosis of stuttering, stammering, or developmental speech disfluency documented by a physician, pediatrician, pediatric neurologist, otolaryngologist (ENT), or Speech-Language Pathologist (SLP).
   - Documented plan, encounter, or referral for Speech-Language Pathology (SLP) / speech therapy specifically for stuttering or speech disfluency.
2. **Standardized Diagnostic / Assessment Test**:
   - Documented score or assessment using standardized instruments for stuttering, including:
     - **Stuttering Severity Instrument** (SSI, SSI-3, SSI-4).
     - **Overall Assessment of the Speaker's Experience of Stuttering** (OASES).
     - Formal fluency evaluation noting elevated percent syllables stuttered (`%SS`) or clinically significant sound prolongations, part-word repetitions, or articulatory speech blocks.
3. **Affirmative Pediatric / Developmental Speech Symptom Documentation**:
   - Clear, affirmative documentation that the patient exhibits stuttering/stammering/disfluent speech, especially in a pediatric, well-child, or developmental screening context (e.g., accompanied by confirmatory keywords such as *mom*, *father*, *school*, *preschool*, *birth*, *child* within surrounding text).

---

### **Negative** if:
1. **Absence of Signal**:
   - No stuttering, stammering, or speech disfluency keywords are present anywhere in the patient's longitudinal EHR records.
2. **Explicit Negation**:
   - All mentions of stuttering keywords in the patient's record are clearly negated (e.g., *"denies stuttering"*, *"no stuttering noted"*, *"speech is fluent without stutter or stammer"*).
3. **Formal Rule-Out / Reversal**:
   - Clinical evaluation explicitly ruled out stuttering (e.g., *"evaluated for stuttering, speech fluency within normal limits, rule-out stuttering"*).

---

### **Excluded** if:
1. **Non-Speech Context Exclusively**:
   - All occurrences of keywords describe non-speech medical phenomena (e.g., *"stuttering gait"*, *"stuttering angina"*, *"stuttering priapism"*, *"stuttering myocardial ischemia"*, *"stuttering stroke/infarct"*).
2. **Family History Only**:
   - Keywords appear solely in the Family History (FH) section or refer only to relatives (e.g., *"father stutters"*, *"positive family history of stuttering on paternal side"*) with no personal history or symptoms documented for the patient.
3. **Competing Non-Stuttering Conditions (Colloquial Misattribution)**:
   - Speech irregularity is described colloquially as "stuttering" or "halting" solely in the context of active psychosis, schizophrenia, severe formal thought disorder, mania/pressured speech, or clanging, without independent evidence or evaluation of true stuttering.

---

### **Indeterminate** if:
1. **Ambiguous Context**:
   - Stuttering keyword appears in an affirmative sentence, but speech context cannot be determined from the sentence or broader clinical note.
2. **Conflicting Documentation**:
   - Conflicting statements across providers or notes without clear temporal progression (e.g., single isolated mention of "stuttering" in an unrelated adult clinic note followed by repeated documentation of normal speech fluency).
3. **Uncertainty / Query Only**:
   - Mentioned purely as a differential diagnosis or parental concern that was investigated but never confirmed or followed up (e.g., *"parent asks about stuttering?"* with no clinical evaluation or subsequent mention).

---

## 2. Phrase Dictionaries

### A. Primary Exploratory Keywords
Match any of the following primary search stems (case-insensitive, including inflections and common spelling variations from Pruett et al. 2021 & Shaw et al. 2021):
- **Stutter**: `stutter`, `stuttering`, `stuttered`, `stutters`
- **Stammer (UK variant)**: `stammer`, `stammering`, `stammered`, `stammers`
- **Studder (Common misspelling)**: `studder`, `studdering`, `studdered`, `studders`
- **Disfluency**: `disfluency`, `disfluencies`, `disfluent`
- **Dysfluency (UK/alternate spelling)**: `dysfluency`, `dysfluencies`, `dysfluent`

### B. Confirmatory Context Keywords
Words significantly enriched within 10 words of an exploratory keyword in confirmed developmental stuttering cases:
- **Caregivers & Relatives**: `mom`, `mother`, `mom's`, `dad`, `father`, `dad's`, `father's`, `parent`, `parents`
- **Pediatric & Developmental**: `child`, `children`, `birth`, `school`, `preschool`, `pre-school`
- **Instrument abbreviations**: `SSI`, `SSI-3`, `SSI-4`

### C. Standardized Diagnostic Instruments & Scores
High-value evidence establishing formal assessment:
- **SSI**: `SSI`, `SSI-3`, `SSI-4`, `Stuttering Severity Instrument`, `Stuttering Severity Instrument-3`, `Stuttering Severity Instrument-4`
- **OASES**: `OASES`, `Overall Assessment of the Speaker's Experience of Stuttering`
- **Fluency Metrics**: `percent syllables stuttered`, `% syllables stuttered`, `%SS`, `sound prolongations`, `part-word repetitions`, `blocking on initial consonants`
- **Clinical Evaluations**: `formal speech fluency evaluation`, `stuttering evaluation`, `speech fluency assessment`

### D. Speech-Language Pathology (SLP) Clinical Context
- `speech-language pathologist`, `speech language pathologist`, `speech-language pathology`
- `speech therapist`, `speech therapy`, `speech pathology`
- `SLP`, `CCC-SLP`, `ST`
- `speech consult`, `speech consultation`, `referral to speech therapy`, `speech evaluation`

### E. Speech Context Indicators
Affirmative descriptors confirming the keyword applies to spoken language:
- `speech`, `voice`, `spoken language`, `fluency`, `stuttered speech`, `disfluent speech`
- `conversation`, `verbal expression`, `talking`, `syllables`, `words`, `phonation`
- `sound prolongations`, `part-word repetitions`, `whole-word repetitions`, `audible blocks`, `silent blocks`, `secondary struggle behaviors`

### F. Negation Phrases
Explicit negative contexts that rule out active patient symptoms:
- `no stuttering`, `denies stuttering`, `denied stuttering`, `without stuttering`, `negative for stuttering`, `not stuttering`, `does not stutter`, `no stutter`
- `no stammering`, `denies stammering`, `without stammering`, `negative for stammering`, `does not stammer`
- `no speech disfluency`, `no disfluency`, `denies disfluency`, `negative for disfluencies`
- `speech is fluent without stutter`, `fluent speech without stuttering`, `normal speech fluency`, `fluent without disfluencies`, `speech fluent and articulate`

### G. Family History Indicators
Phrases indicating family member attribution rather than patient symptoms:
- `family history of stuttering`, `FH of stuttering`, `FHx stuttering`, `positive family history of stuttering`
- `father stutters`, `father had a stutter`, `dad stutters`, `mother stutters`, `mom stutters`
- `brother stutters`, `sister stutters`, `sibling stutters`, `cousin stutters`, `uncle stutters`
- `paternal history of stuttering`, `maternal history of stuttering`, `history of stuttering on father's side`

### H. Non-Speech Exclusions
Common clinical jargon where "stuttering" describes non-speech phenomena:
- **Gait / Motor**: `stuttering gait`, `stuttered gait`, `stuttering walk`, `stuttering steps`
- **Cardiovascular / Ischemia**: `stuttering angina`, `stuttering chest pain`, `stuttering ischemia`, `stuttering myocardial ischemia`, `stuttering infarct`, `stuttering infarction`
- **Neurological / Cerebrovascular**: `stuttering stroke`, `stuttering TIA`, `stuttering transient ischemic attack`, `stuttering course of infarction`
- **Urological**: `stuttering priapism`, `stuttering priapisms`
- **Temporal course jargon**: `stuttering course`, `stuttering onset`, `stuttering symptoms` (when referring to non-speech diseases)

### I. Competing Conditions (False Positives)
Conditions where speech abnormalities may be colloquially mislabeled as stuttering:
- `schizophrenia`, `schizoaffective disorder`, `psychosis`, `acute psychosis`
- `formal thought disorder`, `loose associations`, `flight of ideas`, `clanging`, `clang associations`
- `pressured speech`, `halting speech in psychosis`, `poverty of content`
- `palilalia`, `echolalia`, `coprolalia`
- `apraxia of speech`, `expressive aphasia`, `wernicke's aphasia`, `broca's aphasia`

---

## 3. Decision Matrix (for LLM Retrieval & Rule Matching)

| Primary Keyword Present | Negated? | Subject Attribution | Context | High-Value Evidence (SLP / SSI / OASES) | Competing Exclusions | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Yes** | No | Patient | Speech | Confirmed (SLP dx / SSI / OASES) | None | **Positive** |
| **Yes** | No | Patient | Speech | Affirmative clinical mention / pediatric context | None | **Positive** |
| **Yes** | No | Patient | Speech | Present | Attributed solely to psychosis / clanging | **Excluded** |
| **Yes** | No | Patient | Non-speech (gait, angina, priapism) | Any | N/A | **Excluded** |
| **Yes** | Any | Family member only | Any | None for patient | N/A | **Excluded** |
| **Yes** | Yes | Patient | Speech | None | None | **Negative** |
| **Yes** | Ambiguous | Patient | Ambiguous | None | None | **Indeterminate** |
| **No** | N/A | None | N/A | None | None | **Negative** |

---

## 4. Extraction & Tie-Breaking Guidance

### Step 1: Keyword Presence & Spelling Robustness
- Match all spelling variants: `stutter*`, `stammer*`, `studder*` (common spelling error in clinical notes), `disfluen*`, and `dysfluen*`.
- Both noun and verb forms (`stuttering`, `stutters`, `stuttered`) count as hits.

### Step 2: Affirmative vs. Negative Assertion
- Distinguish affirmative statements (*"patient is stuttering per mother"*) from explicit negations (*"denies stuttering"*, *"speech normal without stuttering"*).
- If a note contains both negated review of systems and an affirmative diagnosis in the impression or plan, prioritize the physician's clinical impression/plan.

### Step 3: Attribution Disambiguation (Patient vs. Family History)
- **CRITICAL**: Stuttering has high familial aggregation. Many pediatric notes record family history (*"Positive family history of stuttering on father's side"*).
- Ensure the keyword is attributed directly to the **patient**. Mentions restricted to parents, siblings, or extended relatives must be classified as **Excluded (Family History Only)** unless the patient themselves also has documented stuttering.

### Step 4: Speech Context Verification (Exclusion of Non-Speech Medical Jargon)
- Verify that the keyword describes **speech/communication**.
- Exclude medical jargon where "stuttering" denotes intermittent or waxing/waning physical symptoms:
  - *Stuttering gait*: Ataxia or hesitation in walking.
  - *Stuttering angina / ischemia*: Intermittent coronary chest pain.
  - *Stuttering priapism*: Recurrent ischemic urological episodes.
  - *Stuttering stroke*: Fluctuating or progressive focal neurological deficits.

### Step 5: Clinical Setting & Broader Context Weighting
- When a sentence lacks an explicit speech indicator (e.g., *"mother notes intermittent stuttering"*), evaluate the broader clinic setting:
  - **High Prior**: Pediatric checkups, well-child visits, child development clinics, otolaryngology (ENT), and speech-language clinics strongly imply speech.
  - **Low Prior**: Adult cardiology, vascular surgery, or orthopedic encounters require explicit confirmation that speech is being described.

### Step 6: High-Value Confirmatory Evidence
- Prioritize notes written by or referring to a **Speech-Language Pathologist (SLP)**.
- Standardized test scores (**SSI**, **SSI-3**, **SSI-4**, **OASES**) represent near-definitive clinical confirmation.
- Documented secondary behaviors (e.g., facial grimacing, eye blinking during speech blocks) strongly support developmental stuttering.

### Step 7: Competing Psychiatric & Neurological Presentations
- Severe psychiatric disorders (e.g., schizophrenia, acute psychosis) may cause halting, disorganized, or perseverative speech that clinicians or families colloquially label as "stuttering".
- If the patient's speech difficulty is described exclusively within a psychotic episode or psychiatric exacerbation without speech therapy evaluation or childhood history, classify with caution or mark as **Excluded** / **Indeterminate**.

### Step 8: Reversal Recognition & Formal Rule-Out
- If an evaluation note explicitly states that stuttering was suspected but ruled out upon formal evaluation (e.g., *"Speech evaluation completed: disfluencies are typical developmental non-fluencies, does not meet criteria for stuttering"*), mark the patient as **Negative**.

### Step 9: Multi-Note Longitudinal Synthesis
- Developmental stuttering onset is typically in early childhood (ages 2–6). A single confirmed pediatric diagnosis or course of speech therapy establishes a **Positive** phenotype across the longitudinal record.
- Because stuttering can improve or remit in adolescence/adulthood, later notes stating *"speech fluent"* do not invalidate a validated childhood diagnosis of developmental stuttering, provided childhood diagnosis was affirmative.
