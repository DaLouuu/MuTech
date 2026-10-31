# Updating the SLR Manuscript: Where to Find New Data, and What Actually Changed

This maps `OLD SLR.pdf` ("Intelligent Music Processing for Singing, Ensembles, and
Instrumental Performance: A Systematic Literature Review") section-by-section to the
MuTech repository, so whoever updates the manuscript knows exactly which file to pull
each new number/table/figure from.

**Read Section 1 before touching any numbers.** The methodology itself changed in ways
that matter more than any individual statistic — this isn't a find-and-replace job.

---

## 1. What changed in the methodology (read this first)

| | Old paper (`OLD SLR.pdf`) | Current pipeline (this repo) |
|---|---|---|
| Databases | 4: ISMIR, IEEE Xplore, ACM Digital Library, SpringerLink/Elsevier | **2: Scopus, IEEE Xplore.** ISMIR, ACM, SpringerLink were never queried anywhere in this repo. |
| Corpus size | 100 included studies | **365 included papers** |
| Search window | Primary 2020–2025, with pre-2020 foundational exceptions | 2020–2026 (`PUBYEAR > 2019`); no explicit foundational-paper carve-out |
| Classification approach | Manual: two-axis domain × modality matrix, hand-coded by the review team, plus a 45-point quality rubric (Borbon & Ebardo) | **Automated: TF-IDF + K-Means clustering** into 7 topic clusters (validated against 3 other models — Agglomerative, NMF, LDA — and selected as the best fit; see Section 5). No modality tagging, no quality-rubric scoring exists anywhere in the pipeline. |
| Screening | Title/abstract screening described narratively, no named tool | **Rayyan**, 3 independent reviewers, blind screening with a recorded per-reviewer decision trail |
| Synthesis unit | Manually extracted per-study attributes (domain, modality, task, architecture, paradigm, supervision, evaluation type, reproducibility) | No per-study manual attribute extraction exists; clusters are derived purely from title+abstract+keyword text via TF-IDF |

**The single biggest decision the team needs to make before updating the paper**: either
(a) actually run ISMIR/ACM/SpringerLink queries to match the claimed 4-database scope, or
(b) rewrite Section 2.1 to honestly describe the 2-database scope that was actually run.
Nothing in this repo queries the other two databases — there's no code, no raw export, no
evidence they were ever pulled. Silently keeping the old text would misstate what was
actually done.

The second-biggest decision: the old paper's entire empirical backbone (Table 6–11,
Figures A1–A3) is built on the **domain × modality matrix**, which has no automated
equivalent in this pipeline. The new pipeline's classification is topic clusters (MIR
task/theme, closest conceptually to the old paper's Table 8, not the domain or modality
axes). Sections 3.1.2, 3.1.3, and 3.2 either need fresh manual coding (see Section 4 of
this guide) or need to be reframed around what the pipeline actually produces.

---

## 2. Section-by-section mapping

### Abstract
Every number in the abstract (100 studies, 20% source separation, 68% audio-only, 16%
instrumental, 4 gaps, 6 directions) is from the old 100-paper/domain-matrix corpus and
needs a full rewrite. New corpus size and topic breakdown: Section 3 of this guide.

### 1. Introduction
Mostly narrative background; low numeric dependency. The four RQs can likely stay
conceptually similar, but RQ1 in particular ("MIR tasks, modeling paradigms, and
architectural approaches... applied to solo singing, ensemble, instrumental performance")
implicitly assumes the domain-tagging that no longer exists automatically — see Section 4.

### 2. Methodology

**2.1 Database selection and search strategy**
- Table 1 (database roles) needs to drop ISMIR, ACM Digital Library, and
  SpringerLink/Elsevier, or the team needs to actually run those queries first.
- Table 2 (search terms) doesn't match the actual query. The real Scopus query, verbatim,
  is implemented in `slr/src/pipeline_engine.py` (documented in `slr/notebooks/MuTech_SLR_Consolidated_Pipeline.ipynb`):
  ```
  TITLE-ABS-KEY(("music" OR "instrument" OR "music information retrieval" OR "audio
  signal processing") AND ("performance" OR "solo" OR "ensemble" OR "transcription")
  AND ("machine learning" OR "AI" OR "artificial intelligence" OR "deep learning"))
  AND PUBYEAR > 2019
  ```
  The IEEE query uses the same three concept blocks without the year filter applied at the API level. Both are two-block-simpler than the old paper's Block
  A/B/C thesaurus-expanded structure — worth deciding whether to expand the real query to
  match the paper's described rigor, or describe the simpler query that was actually run.

**2.2 Eligibility criteria**
The actual eligibility mechanism is keyword-based triage, not a manually-applied
document/content-level checklist. The real keyword lists (`INCLUDE_KEYWORDS`/
`priority_terms` and `EXCLUDE_KEYWORDS`/`exclude_terms`) are defined in `slr/src/pipeline_engine.py`. The
`priority_terms` list that defines "Priority" (→ sent to Rayyan) is:
```
music information retrieval, mir, music retrieval, music classification, genre
classification, music tagging, music transcription, automatic music transcription,
source separation, music source separation, singing voice, singing, choral, choir,
ensemble, instrumental, pitch estimation, pitch detection, music similarity, audio
tagging, music emotion recognition, score following, optical music recognition, omr
```
`exclude_terms` spans speech-only, biomedical, recommender-system, industry, and
musicology/psychology terms — full list in `slr/src/pipeline_engine.py`. **Historical Caveat**: a missing-comma bug
in legacy runs merged 6 of these into 3 broken strings (documented in `slr/guides/ROOT_CAUSE_AUDIT.md`),
which has now been resolved and safeguarded by automated Gate 2 checks.

**2.3 Classification strategy and quality assessment**
This entire section describes a process that doesn't exist in the current pipeline — no
domain × modality matrix, no coding tags, no 45-point quality rubric. What exists instead:
`slr/src/pipeline_engine.py` (and `slr/notebooks/MuTech_SLR_Consolidated_Pipeline.ipynb`) runs four topic-clustering models
(K-Means, Agglomerative, NMF, LDA) on TF-IDF vectors of title+abstract+keywords, validates
each with a held-out train/test split, bootstrap stability analysis ($B=10$), and selects the
best-performing one. This replaces Tables 3–5 conceptually but not mechanically — see
Section 4 for what would need fresh work to reproduce something table-3-shaped.

**2.4 Data extraction and synthesis**
No standardized per-study attribute extraction (domain, modality, architecture family,
supervision strategy, etc.) exists in this pipeline. `slr/outputs/models/phase4_model_comparison.csv` and `slr/outputs/models/phase4_soft_topic_distributions.csv`
give per-cluster top TF-IDF terms and soft topic weightings, which is the closest automated substitute for
"architecture/method family" but is not the same kind of structured attribute.

### 3. Results and Classification

**3.1.1 Temporal distribution (Table 6)**
Real distribution, verified directly from `slr/outputs/representations/phase3_cleaned_corpus.csv`
(`year` column, 365 rows, 0 missing):

| Year | Papers |
|---|---|
| 2020 | 32 |
| 2021 | 46 |
| 2022 | 45 |
| 2023 | 51 |
| 2024 | 62 |
| 2025 | 78 |
| 2026 | 51 |
| **Total** | **365** |

A ready-made chart of this exists at
`slr/manuscript/figures/`. Note the corpus extends into 2026
(the old paper's window stopped mid-2025) — the 2026 count is a partial year, same
search-cutoff caveat the old paper already applies to its own 2025 row.

**3.1.2 Domain distribution (Table 6/7, "Solo Singing / Ensemble / Instrumental / General
MIR")**
No automated equivalent — this is one of the manual-coding gaps (see Section 4). The
closest automated substitute is the K-Means topic-cluster breakdown, which classifies by
**MIR task/theme**, not performance context, and doesn't map cleanly onto the old paper's
four domain categories. See 3.3 below.

**3.1.3 Modality distribution (Table 6/7, "Audio / Symbolic / Multimodal")**
No automated equivalent exists — see Section 4.

**3.2 Classification matrix (Table 7)**
Depends on both 3.1.2 and 3.1.3; can't be reproduced without the manual coding described
in Section 4.

**3.3 Primary MIR task distribution (Table 8) — closest match to the new pipeline**
This is conceptually the best-aligned table: the old paper's manually-tagged task clusters
and the new pipeline's automatically-discovered K-Means topics are both "what is this
paper actually about, computationally." The real numbers, from
`slr/outputs/models/phase4_clustered_corpus.csv` and
`slr/outputs/models/phase4_model_comparison.csv` (K-Means, k=7, selected model — see Section 5):

| Cluster | Label (hand-read from top TF-IDF terms) | Papers |
|---|---|---|
| 0 | Instrument Recognition / Classification | 47 |
| 1 | Automatic Music Transcription (AMT) | 74 |
| 2 | Singing Voice / Melody Extraction | 41 |
| 3 | Source Separation | 72 |
| 4 | Multi-Pitch Estimation | 22 |
| 5 | Music Education & Performance Assessment | 79 |
| 6 | Optical Music Recognition (OMR) | 30 |
| **Total** | | **365** |

Note this is a flat 7-way partition (every paper in exactly one cluster), unlike the old
Table 8's task clusters which could co-occur per paper. However, with the addition of
`slr/outputs/models/phase4_soft_topic_distributions.csv` (Grisales A. et al., 2023),
continuous secondary topic memberships and interdisciplinary crossover papers are now fully quantified.
The full top-terms list is in `slr/outputs/models/phase4_model_comparison.csv`.

### 4. Synthesis of Findings (RQ1–RQ4)
This section is narrative and cites specific papers by author/year throughout — it can't
be regenerated mechanically. To rewrite it against the new corpus, start from:
- `slr/outputs/models/phase4_model_comparison.csv` for what each cluster is actually about.
- `slr/outputs/models/phase4_clustered_corpus.csv` for which 365 papers landed in which cluster
  (join on title against `slr/outputs/prisma/phase2_screened_corpus.csv` to get authors/year/DOI for citation).
- `slr/outputs/models/phase4_soft_topic_distributions.csv` and `slr/outputs/network/phase5_temporal_topic_evolution.csv`
  for RQ4-relevant material specifically — directly measuring which clusters are network-adjacent and how topics
  evolve longitudinally across epochs.

### 5. Discussion

**5.2 Limitations** — this section should absorb the real, found-and-documented
limitations of the actual pipeline, which are more specific than the old paper's generic
limitations paragraph:
- 2-database scope (not 4) — see Section 1 of this guide.
- The historical exclude-keyword comma bug (Section 2.2 above; resolved in the current engine).
- **`Publication Venue` / journal field is 0% populated for all 365 final papers** — traced
  to two separate causes (a Scopus column-mislabeling bug affecting ~90% of the corpus,
  plus data loss in the Rayyan export/re-import round trip for the rest). Full writeup in
  `slr/guides/ROOT_CAUSE_AUDIT.md`. This means no venue-based analysis is currently possible from
  this corpus without a fresh data pull.
- LDA's known small-corpus limitation, empirically confirmed: it resolved only 3 broad
  topics (vs. 7 for K-Means/NMF) and showed higher perplexity. Full detail in
  `slr/outputs/models/phase4_model_comparison.csv` and `slr/guides/ROOT_CAUSE_AUDIT.md`.
- No modality or domain tagging, no quality-rubric scoring (Section 2.3 above) — worth
  stating as a scope limitation if that work isn't picked back up before submission.

### 6. Conclusion
Rewrite against the RQ answers produced in Section 4 above; no separate data source.

### References
The old reference list is for the old 100-paper corpus and doesn't overlap with the new
365-paper corpus. The real reference list (title, authors, year, DOI, venue-when-available)
is in `slr/outputs/prisma/phase2_screened_corpus.csv` (source: `slr/data/02_screening/priority_records_from_rayyan.csv`).

### Appendix A: Master Summary Table
Direct analogue exists, just smaller in structured detail: join `slr/outputs/models/phase4_clustered_corpus.csv` (title, year, cluster)
against `slr/outputs/prisma/phase2_screened_corpus.csv` (authors, DOI, abstract, keywords) on title,
and `slr/outputs/models/phase4_model_comparison.csv` for a cluster-level key finding gloss.

### Appendix B: Quality Appraisal Rubric
No automated equivalent — see Section 4 (manual-coding gaps) if the team wants to keep
this in the updated paper.

### Appendix C: PRISMA flow diagram + domain/modality figures
**Figure A1 (PRISMA flow) — real, verified numbers to drop in:**

```
Identification
  Scopus:  8,943 records
  IEEE:    1,000 records
  Total:   9,943 records identified
        ↓
Deduplication
  575 duplicates removed (DOI & normalized-title matching)
  9,368 unique records remaining (slr/outputs/prisma/phase1_merged_deduplicated.csv)
        ↓
Screening (automated keyword triage & human review)
  1,728 flagged Priority → sent to Rayyan
        ↓
Eligibility / Screening (Rayyan, 3 independent reviewers, blind)
        ↓
Included
  365 papers in final synthesis (slr/outputs/prisma/phase2_screened_corpus.csv)
`
Source: Verified directly from slr/outputs/prisma/phase1_merged_deduplicated.csv and
slr/outputs/prisma/phase2_screened_corpus.csv via automated Gate 1 & Gate 2 validation assertions.

**Figures A2/A3 (domain and modality distributions)** — no automated equivalent (Section
4). The nearest available substitute chart is
`slr/manuscript/figures/models_2d_final.png` (a 2D projection of all
four clustering models side by side) or a fresh bar chart of the Section 3.3 cluster-size
table above.

---

## 4. Gaps: things the old paper reports that have no automated equivalent yet

If any of these are needed for the updated paper, they require new work, not a file
lookup:

1. **Domain tagging** (Solo Singing / Ensemble / Instrumental / General MIR per paper) —
   would need either manual coding of the 365 papers, or a second automated pass reusing
   the existing keyword-flagging pattern from Phase 1-2 with a domain-specific keyword set.
2. **Modality tagging** (Audio / Symbolic / Multimodal per paper) — same, no keyword or
   metadata field currently captures this.
3. **Quality appraisal scoring** (the 45-point rubric) — entirely manual in the old paper;
   nothing in this pipeline evaluates methodological/relevance quality per study.
4. **Per-study structured attributes** for RQ1–RQ3 narrative (architecture family,
   supervision strategy, evaluation type, reproducibility status) — the closest automated
   signal is each cluster's top TF-IDF terms, which describes a *topic*, not a *study's*
   individual method choices.

---

## 5. What the new pipeline added that the old paper doesn't have at all

Worth considering for a dedicated methodological subsection rather than trying to force into the old structure:

- **Held-out validation and 4-model benchmarking.** K-Means, Agglomerative, NMF, and LDA were comprehensively benchmarked using both Cosine Silhouette and UMass Topic Coherence, with hyperparameter tuning before final model selection. Full details in `slr/outputs/models/phase4_model_comparison.csv`.
- **Automated PMI Collocation Mining (Phase 3).** Automated extraction of high-association multi-word technical phrases using Pointwise Mutual Information and NPMI ($\ge 0.50$; Truică & Apostol, 2021, *IEEE Access*), removing manual phrase curation bias (`slr/outputs/representations/phase3_pmi_collocations.csv`).
- **Dense Semantic LSA & SciBERT Embeddings (Phase 3/4).** 35-D LSA projections resolve cosine distance concentration in sparse vectors, with modular SciBERT embedding support (Chen & Liu, 2025, *IEEE AINIT*).
- **Soft Multi-Topic Membership & Interdisciplinary Crossovers (Phase 4).** Continuous Dirichlet posterior distributions from LDA and weightings from NMF revealing that 67.1% (245/365) of included studies span multiple MIR subfields (Grisales A. et al., 2023, *IEEE Access*; `slr/outputs/models/phase4_soft_topic_distributions.csv`).
- **Topic Stability Bootstrapping (Phase 4).** Bootstrap consensus stability analysis across $B=10$ randomized initializations, mathematically confirming topic robustness against stochastic noise ($	ext{ARI} = 0.6103 \pm 0.053$; Vangara et al., 2021, *IEEE Access*).
- **Network-Theoretic Louvain Cross-Check (Phase 5).** Independent paper-similarity network (365 nodes, 1,846 edges) with Louvain community detection (Modularity: 0.6267, well above the 0.3 threshold; `slr/outputs/network/phase5_cluster_network.gexf`).
- **Longitudinal Dynamic Topic Evolution Tracking (Phase 5).** Temporal flow modeling across Foundational (2020–2021), Consolidation (2022–2023), and Modern (2024–2026) epochs (Wang et al., 2024, *Scientometrics*; `slr/outputs/network/phase5_temporal_topic_evolution.csv` & `.json`).
- **Gephi-Ready Network Export & Live Web Dashboard.** Interactive topic network published at `docs/index.html` (hosted on GitHub Pages) and available in `slr/outputs/network/phase5_cluster_network.gexf`.

---

## 6. Canonical Reorganized File Index

| Need | Current Canonical File | Description |
|---|---|---|
| PRISMA funnel deduplicated records | slr/outputs/prisma/phase1_merged_deduplicated.csv | 9,368 unique studies from 9,943 identified (575 duplicates removed) |
| PRISMA screened corpus (Rayyan N=365) | slr/outputs/prisma/phase2_screened_corpus.csv | 365 included studies with human blind-screening consensus |
| NLP cleaned corpus & tokens | slr/outputs/representations/phase3_cleaned_corpus.csv | Cleaned and tokenized abstracts |
| Automated PMI Collocations (N=30) | slr/outputs/representations/phase3_pmi_collocations.csv | Statistically mined domain compound phrases (Truică & Apostol, 2021) |
| TF-IDF Document-Term Matrix | slr/outputs/representations/phase3_tfidf_matrix.npz | 365 docs × 2,000 terms sparse matrix |
| 4-Model Suite Benchmark Comparison | slr/outputs/models/phase4_model_comparison.csv | Silhouette, UMass, cluster sizes, and ARI across K-Means, Agglomerative, NMF, LDA |
| Primary Topic Clustered Corpus | slr/outputs/models/phase4_clustered_corpus.csv | All 365 studies with assigned topic columns for all 4 models |
| Soft Multi-Topic Distributions & Entropy | slr/outputs/models/phase4_soft_topic_distributions.csv | Primary & secondary topic probabilities, entropy, and interdisciplinary crossover flag |
| Gephi Social Network File | slr/outputs/network/phase5_cluster_network.gexf | 365 nodes, 1,846 edges with Louvain community attributes (modularity: 0.6267) |
| Longitudinal Topic Evolution Flow Data | slr/outputs/network/phase5_temporal_topic_evolution.csv | Transition link counts across 3 publication epochs (Wang et al., 2024) |
| Temporal Topic Evolution JSON Data | slr/outputs/network/phase5_temporal_topic_evolution.json | Complete epoch shares and Sankey node/link specifications |
| Live Interactive SNA Dashboard | docs/index.html | Published GitHub Pages graph visualization |
| Peer-Reviewed Methodology Evidence | slr/guides/SLR_METHODOLOGY_REFERENCES.md | Complete 2021–2026 Scopus/IEEE citations with direct permanent DOI links |
| Pipeline Parameter Configuration Roadmap | slr/guides/PIPELINE_CONFIGURATION_GUIDE.md | Guide on where and how to customize parameters across all phases |
