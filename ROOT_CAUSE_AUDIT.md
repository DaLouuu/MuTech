# Root-Cause Audit — Why the SLR Has the Errors It Has

Traced from the repository, not from the manuscript. Every claim below was re-verified
against the actual CSVs/notebooks during this pass. Ordered by how much of the paper each
defect contaminates.

**The short version:** almost none of these are writing mistakes. Nine of them are single
lines of upstream code whose output was later described in prose as if it were a finding.
The writing errors are downstream symptoms.

---

## Tier 1 — Defects that invalidate a stated finding

### 1. `General MIR` and `Audio` are fallback buckets, not categories

**Where it surfaces:** 3.1.2 ("General MIR is the largest domain, n = 170, 46.6%"),
3.1.3 ("Audio-only accounts for 71.0%"), Table 7, and reversal claim #1 in
`WHAT_CHANGED_AND_WHY.md`.

**Root cause:** `phase6_manuscript/domain_modality_tags.csv` — the `domain_evidence` and
`modality_evidence` columns.

| Label | Rows | Rows with evidence |
|---|---|---|
| Solo Singing | 52 | 52 |
| Instrumental | 133 | 133 |
| Ensemble | 10 | 10 |
| **General MIR** | **170** | **0** |
| Symbolic | 71 | 71 |
| Multimodal | 35 | 35 |
| **Audio** | **259** | **0** |

Every `General MIR` and every `Audio` label has an empty evidence cell. They are the
`else` branch of the tagger — "no domain keyword matched" and "no symbolic/multimodal
keyword matched." The paper reports the residual as the field's centre of gravity.

**Consequence:** "General MIR dominates at 47%" actually reads "47% of abstracts contained
none of our domain keywords." The same applies to the 71% audio figure, which then
underpins Table 10's headline negative result ("evaluation practice is
modality-independent") — a claim resting on a variable that is 71% default.

**Fix:** either add positive inclusion evidence for both fallback classes, or rename them
`Unclassified / general` and `Audio (default — no symbolic or multimodal marker)` and
retract the "dominates" framing.

---

### 2. Every Scopus record has one author. All citations are affected.

**Where it surfaces:** the entire reference list, every in-text citation in 4.1–4.4, the
co-authorship network in Phase 5 and `docs/index.html`, and every `et al.` in the drafts.

**Root cause:** `phase1_2/MuTech_Phase1_2_Collection_Screening.ipynb`, cell 0:

```python
df_scopus = df_scopus[['title','description','coverDate','doi','creator','authkeywords','subtypeDescription']]
df_scopus = df_scopus.rename(columns={..., 'creator': 'Authors', ...})
```

In `pybliometrics.ScopusSearch`, `creator` is the **first author only**, not the author
list. The full list is `author_names`, which was never pulled and cannot be recovered
without re-querying Scopus.

**Verified:** all 365 rows of `priority_records_from_rayyan.csv` parse to exactly one
author name. 320 rows are Scopus-style (`Krause M.`); 45 are IEEE-style
(`M. Krause and C. Weiß and M. Müller`) — the corpus mixes two incompatible author formats
in one column.

**Consequences, all of them citation-integrity issues an examiner will catch:**

- Every `et al.` in Parts 5–6 (`Mezza et al. 2024`, `Ríos-Vila et al. 2022`,
  `Dubey et al. 2023`, `Kostrzewa et al. 2026`, `Scarpiniti et al. 2023`,
  `Yamamoto et al. 2023`) is unsupported by the corpus — the records hold a single name.
  This directly contradicts the note "all citations are corpus papers verified 1:1 against
  `priority_records_from_rayyan.csv`."
- **18 of the 99 citations in `challenge_evidence.csv` are initials parsed as surnames:**
  `[X., 2023]`, `[M., 2026]`, `[Y., 2025]`, `[S., 2024]`, `[P., 2026]`, `[R., 2026]`,
  `[H., 2025]`, `[Z., 2025]`, `[E., 2025]`, `[T., 2024]`, `[L., 2026]`, `[A., 2026]`,
  `[C., 2022]` and others. These came from the IEEE-format rows, where splitting on the
  first token yields the initial.
- `[Chongyang, 2026]` keys a given name as a surname.
- `Marták L.` and `Marták L.S.` are the same author under two spellings, on two different
  2026 papers — `[Marták, 2026]` in 4.3 is ambiguous.
- Phase 5's README explains the sparse co-authorship graph as "a property of the upstream
  export." It isn't. It is this line. The co-authorship tab in `docs/index.html` is
  measuring first-author name collisions.

**Fix:** re-pull Scopus with `author_names`, or drop the co-authorship analysis and rebuild
the reference list from DOI via Crossref. Do not ship `et al.` that the data cannot support.

---

### 3. The clusters have a silhouette of 0.039

**Where it surfaces:** Table 3, Section 3.3, all of Section 4, and the entire RQ4 network
narrative.

**Root cause:** `phase4/phase4_output_detailed/comparison/FINAL_MODEL_SELECTION.txt`.

| Model | Silhouette |
|---|---|
| K-Means | 0.0389 |
| NMF | 0.0385 |
| Agglomerative | 0.0279 |
| LDA | 0.0220 |

Silhouette runs −1 to 1; ~0.04 means the seven clusters are barely separated in TF-IDF
space. The model-selection file is honest about the number, and Table 3 prints it — but the
surrounding prose treats the partition as a settled taxonomy ("seven data-driven topic
clusters," "genuine topical structure"). The number does not support that reading. This is
normal for short-text TF-IDF and is not a bug; the error is the confidence of the prose,
not the value.

**Fix:** state plainly that the partition is a weakly-separated but interpretable
convenience structure, and that cluster-level claims are exploratory.

---

### 4. The Phase 5 network is not an independent validation

**Where it surfaces:** 2.3 ("cross-validated externally... indicating that the seven
clusters reflect genuine topical structure rather than algorithmic artifact"), 4.4, and
`WHAT_CHANGED_AND_WHY.md` ("two new validation layers").

**Root cause:** `phase5/README.md`, step 2: edges are "top-8 nearest neighbors by TF-IDF
cosine similarity (**same TF-IDF settings as Phase 3/4**, refit deterministically)."

K-Means in Phase 4 partitions that same cosine geometry. Building a kNN graph from the
distance function the clustering already optimised and then reporting that the clustering
has high modularity on it is circular — modularity 0.53 is close to guaranteed by
construction. Louvain is "unsupervised" with respect to the labels but not with respect to
the representation, so ARI 0.53 measures representation agreement, not construct validity.

Supporting evidence that this is not a strong result anyway: Louvain finds **10**
communities, not 7, at higher modularity (0.6058) than the K-Means partition.

**Fix:** either drop the independence claim, or validate against something genuinely
external — citation/reference overlap, venue, or manual coding of a sample.

---

### 5. The tag-validation audit trail is an empty file

**Where it surfaces:** 2.3 and the Table 6 note ("validated against a stratified sample
manually reviewed by the authors; misclassifications identified in the sample were
corrected").

**Root cause:** `phase6_manuscript/validation_sample_30.xlsx` contains a header row and
**23 completely blank rows**. No titles, no abstracts, no `correct_domain` /
`correct_modality` verdicts. Nothing was recorded.

Three inconsistencies compound it: the filename says 30, the file holds 23 rows, and
`numbers_manifest.txt` describes a 23-paper sample. The "3 misclassifications found" figure
has no surviving receipt.

**Fix:** re-run the validation and save the completed sheet, or delete the validation
sentence from 2.3 and the Table 6 note. As written it is an unsupported methodological
claim, which is the most damaging category of SLR error.

---

## Tier 2 — Defects that weaken a finding

### 6. The quality scorer disagreed with the human reviewer on 47% of the spot-check

**Where it surfaces:** Tables 4–5, the "40% score below the 30/45 threshold" claim, and
reversal #5.

**Root cause:** `phase6_manuscript/quality_spotcheck_15.xlsx` — **7 of 15 rows flagged**
(`q_validation should be 3`, `q_data should be 5`, `q_methods should be 3`, …). The README
records the fix ("indicators fixed, corpus re-scored") but there is no post-fix
re-validation sheet, so the corrected error rate is unknown.

Two further artefacts in `quality_scores.csv`:

- **`quality_total` is always odd.** Nine criteria scored 1/3/5 can only sum to an odd
  number, so the "distribution of total quality scores" has a comb structure with 13
  attainable values. Table 5's bin labels (`0–20`, `20–25`, `25–30`…) also overlap at every
  boundary — 25 appears in two bins. They compute correctly only because no even score
  exists.
- **`q_alignment` is near-constant:** 345 of 365 papers score 5, 20 score 3. It contributes
  almost nothing to discrimination but 15% of the maximum score, inflating every total.
- **`q_reproducibility` averages 2.11** and 47.4% sit at the floor. But this is scored from
  abstracts by looking for code-availability language — which abstracts almost never carry.
  4.3 already concedes this ("just 7% of abstracts mention code or data availability"), then
  Gap 3 uses the same number as evidence that "reproducibility infrastructure is missing."
  The instrument cannot distinguish "no code released" from "code released, not mentioned in
  the abstract."

**Fix:** report quality scores as an abstract-reporting-practice measure, not a quality
measure. Drop `q_alignment` or justify it. Never state "40% fall below threshold" without
the 47% spot-check disagreement rate alongside it.

---

### 7. `ensemble` and `mir` are substring matches, so off-topic papers entered the corpus

**Where it surfaces:** the included corpus itself, and therefore every count in Section 3.

**Root cause:** `phase1_2/…Collection_Screening.ipynb`, cells 5–8:

```python
def contains_any(text, terms):
    return any(term in text for term in terms)     # substring, not word-boundary
```

`priority_terms` includes the bare tokens `"mir"`, `"omr"`, `"ensemble"`, `"instrumental"`.

| Term | Substring hits in final corpus | Word-boundary hits | Phantom |
|---|---|---|---|
| `mir` | 57 | 47 | 10 |
| `ensemble` | 37 | 32 | 5 |
| `instrumental` | 26 | 24 | 2 |
| `choral` | 8 | 7 | 1 |

Worse than the substring issue: **`ensemble` matches machine-learning ensembles.** 15 of the
37 `ensemble` hits use ML phrasing (`ensemble learning`, `stacking ensemble`,
`ensemble models`). `ensemble` is the *sole* qualifying music term for 17 included papers.

Concrete inclusion error, verified: **"Speech emotion recognition with light weight deep
neural ensemble model using hand crafted features"** is in the final 365. It is a speech
paper. It entered on `ensemble`, and `exclude_terms` never caught it because the list has
`"speech recognition"` but not `"speech emotion recognition"`.

Three papers qualified on `mir` alone, including an Indian-folk-genre paper and
`TMIR: Transient Length Extraction…`.

**Fix:** `re.search(rf"\b{term}\b", text)` and remove or qualify `ensemble`
(→ `musical ensemble`, `vocal ensemble`, `ensemble performance`).

---

### 8. The `exclude_terms` comma bug — 6 criteria never ran

**Root cause:** `phase1_2/…Collection_Screening.ipynb`, cell 5 — implicit string
concatenation from missing commas:

```python
"metadata tagging",
"artist tagging"          # ← no comma

"semantic tagging",
"genre tagging"           # ← no comma

"hearing aid",
...
"hearing impairment"      # ← no comma

"music generation",
```

Python silently joins these into `"artist tagging\n    semantic tagging"`,
`"genre tagging\n    hearing aid"`, `"hearing impairment\n    music generation"`. Those
three strings match nothing, so **`artist tagging`, `semantic tagging`, `genre tagging`,
`hearing aid`, `hearing impairment`, and `music generation` were never excluded.**

This is documented in `phase1_2/README.md` and in the notebook, which is good practice — but
Section 2.2 of the manuscript still describes the exclusion criteria as if all of them ran.
Either fix and re-run, or footnote it.

---

### 9. The 6.2× education growth compares a 3-year window to a 4-year window

**Where it surfaces:** 4.4 trend (2) and 4.5.

**Root cause:** the era split in the analysis is 2020–2022 (3 years, 123 papers) vs
2023–2026 (4 years, 242 papers, with 2026 partial). Recomputed:

| Cluster | 2020–22 | 2023–26 | Raw ratio | Per-year ratio |
|---|---|---|---|---|
| Music Education & Perf. Assessment | 11 | 68 | 6.18× | 4.64× |
| Multi-Pitch Estimation | 6 | 16 | 2.67× | 2.00× |
| Instrument Recognition | 15 | 32 | 2.13× | 1.60× |
| AMT | 28 | 46 | 1.64× | 1.23× |
| Singing Voice / Melody | 16 | 25 | 1.56× | 1.17× |
| OMR | 13 | 17 | 1.31× | 0.98× |
| Source Separation | 34 | 38 | 1.12× | 0.84× |
| **whole corpus** | **123** | **242** | **1.97×** | **1.48×** |

The *relative* ordering survives, so the finding holds. The headline number does not: 6.2×
becomes 4.6× per year, and 3.1× once you normalise against corpus growth. Table 9's
`2020–2022` / `2023–2026` percentage columns carry the same asymmetry.

**Fix:** report per-year rates or share-of-corpus, and say the eras are unequal.

---

### 10. "Ensemble is the real gap (2.7%)" is a definition, not a measurement

**Where it surfaces:** 3.1.2, Gap 1 in 4.4, and reversal #2 in `WHAT_CHANGED_AND_WHY.md`.

**Root cause:** the domain tagger operationalises `Ensemble` as **vocal ensemble only**.
Every one of the 10 Ensemble papers matched on `choral`, `choir`, `chorus`, `a cappella`,
`satb`, `multi-singer`, `polyphonic vocal`, or `vocal ensemble`.

Instrumental ensembles are routed elsewhere: **9 orchestral papers are tagged
`Instrumental`** (`SynthSOD: … Orchestra Music Source Separation`, `The Spheres Dataset:
Multitrack Orchestral Recordings`, `Orchestral Texture Classification`, …), because
`orchestra`/`orchestral` sits in the Instrumental term list.

So "ensemble processing is a 2.7% niche" means "choral processing is a 2.7% niche." Reversal
#2 — the claim that the *old* paper got the gap backwards — is itself produced by a
definitional choice, not by the corpus.

**Fix:** state the operational definition explicitly in 2.3 ("Ensemble = vocal ensemble;
instrumental ensembles are tagged Instrumental"), or re-tag with an ensemble axis that
crosses the vocal/instrumental one.

---

## Tier 3 — Reporting and PRISMA problems

### 11. The PRISMA identification count is post-exclusion

`phase1_2/raw_exports/Scopus_Filtered.csv` has 8,943 rows, and the PRISMA box in
`SLR_PAPER_UPDATE_GUIDE.md` reports "Scopus: 8,943 records" under **Identification**. But
cell 0 had already dropped non-Article/Conference-Paper types and records with null
abstracts or authors before writing that file:

```python
df_scopus = df_scopus[df_scopus['subtypeDescription'].isin(['Article','Conference Paper'])]
df_scopus = df_scopus.dropna(subset=['description','creator'])
```

The true identification count and the number dropped were printed to a cell output that was
never captured. PRISMA 2020 requires those removals to appear as a screening step with a
count and reason.

### 12. IEEE returned exactly 1,000 records — that is a ceiling, not a result

`IEEE_export2026.06.08-04.08.55.csv` has exactly 1,000 rows. Exact round numbers from an API
export are truncation. The notebook's IEEE cell also sets `max_records=200`, which does not
match the 1,000-row file — meaning the checked-in export came from a different, undocumented
route than the code in the repo. The IEEE search is therefore neither exhaustive nor
reproducible from this repository.

### 13. `Source Database` is `Rayyan` for all 365 rows

The round trip through Rayyan overwrote the provenance column. It is now impossible to state
the Scopus/IEEE split of the final corpus from the included file — a standard SLR reporting
requirement. `Publication Venue` is null for all 365 for the reasons already documented in
`phase5/README.md`.

### 14. Table 9's caption contradicts its own column

The caption says "46% of abstracts name no family at all — percentages describe the 54% that
do specify." The column is headed `% of corpus` and CNN reads 32.6%, which is 119/365 —
percent of corpus, not of specifiers. The era columns are also corpus-subset percentages
(37.4% × 123 = 46; 30.2% × 242 = 73; 46 + 73 = 119 ✓). The caption is simply wrong about
its own table.

### 15. Two databases are described, four are claimed

Already flagged in `SLR_PAPER_UPDATE_GUIDE.md` §1 and still unresolved: nothing in this repo
queries ISMIR, ACM DL, or SpringerLink. No code, no export, no evidence.

---

## The pattern behind all of it

Three recurring mechanisms produce every item above:

1. **A default branch gets reported as a result.** (#1, #6-reproducibility, #10)
   Anything the classifier could not label became a finding about the field.
2. **Substring matching on short lexical lists.** (#7, #8, and the `ensemble`/`mir`
   contamination that propagates into every Section 3 count.) The pipeline treats
   `term in text` as "the paper is about term."
3. **A metric computed on the same representation it claims to validate.** (#3, #4)
   Silhouette 0.04 and a self-referential modularity are the same problem seen twice.

`SLR_PAPER_UPDATE_GUIDE.md` and `WHAT_CHANGED_AND_WHY.md` already document a real subset of
this honestly — the comma bug, the venue bug, the LDA limitation, the two-database scope.
The gap is that the prose in Parts 3–6 was written at a confidence level the artefacts do
not support, and in five places (#1, #2, #4, #5, #10) it asserts validation that the files
do not contain.

## Suggested order of work

1. **#5** — delete or re-run the validation claim. Cheapest, highest risk if left.
2. **#2** — re-pull authors or rebuild references from DOI. Blocks the reference list.
3. **#1 and #10** — rename the fallback buckets and state the Ensemble definition. Prose
   only, no re-run needed.
4. **#3 and #4** — soften two paragraphs in 2.3 and 4.4.
5. **#7, #8, #11, #12** — require a re-run of Phase 1–2 and would change every count
   downstream. Decide as a team whether there is time; if not, footnote all four.
