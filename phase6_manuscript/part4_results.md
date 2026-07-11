# PART 4 DRAFT v2 — Section 3: Results and Classification
<!-- Paste-ready. [NOTE:] markers = flags for the team, delete before submission. -->
<!-- v2: incorporates Kean's validation of the tagging sample (23 papers reviewed; 3 misclassifications found and corrected; rules refined accordingly). -->

## 3.1 Study characteristics

### 3.1.1 Temporal distribution

The corpus spans 2020 to mid-2026, corresponding to the search window (PUBYEAR > 2019). Publication volume grew steadily across the period: 32 papers in 2020, 46 in 2021, 45 in 2022, 51 in 2023, 62 in 2024, and 78 in 2025, with 51 papers already indexed from 2026 at the time of the search. The sustained growth from 2023 onward aligns with the broader adoption of Transformer-based architectures and pre-trained audio models in MIR. Table 6 shows the distribution by publication year and musical domain.

**Table 6:** Distribution of included studies by publication year and domain.

| Year | Solo Singing | Ensemble | Instrumental | General MIR | Total | % |
|---|---|---|---|---|---|---|
| 2020 | 5 | 0 | 10 | 17 | 32 | 8.8% |
| 2021 | 9 | 1 | 20 | 16 | 46 | 12.6% |
| 2022 | 9 | 2 | 12 | 22 | 45 | 12.3% |
| 2023 | 5 | 1 | 18 | 27 | 51 | 14.0% |
| 2024 | 11 | 2 | 21 | 28 | 62 | 17.0% |
| 2025 | 9 | 2 | 39 | 28 | 78 | 21.4% |
| 2026* | 4 | 2 | 13 | 32 | 51 | 14.0% |
| **Total** | **52** | **10** | **133** | **170** | **365** | **100%** |

*Note.* \*2026 count reflects publications indexed as of the search date and may be incomplete. Domain labels were assigned through an automated keyword-tagging pass over each paper's title, abstract, and keywords, and validated against a stratified sample manually reviewed by the authors; misclassifications identified in the sample were corrected and the tagging rules refined before final tabulation.

### 3.1.2 Domain distribution

General MIR is the largest domain (n = 170, 46.6%), followed by Instrumental (n = 133, 36.4%), Solo Singing (n = 52, 14.2%), and Ensemble (n = 10, 2.7%). This distribution differs markedly from vocal-centered reviews: the present corpus was retrieved through a deliberately broad query spanning music, instruments, and audio signal processing, and consequently captures the full breadth of intelligent music processing research rather than privileging vocal performance. The small Ensemble count indicates that ensemble-specific processing remains a narrow research niche within the wider field — under 3% of recent intelligent music processing output — reinforcing the gap identified in prior ensemble-focused work.

[NOTE: replaces the old "Solo Singing is the largest domain (35%)" narrative — that described the previous 100-paper corpus and is no longer true of this one.]

### 3.1.3 Modality distribution

Audio-only processing accounts for 259 of 365 included studies (71.0%), symbolic or score-based systems represent 71 papers (19.5%), and multimodal systems account for 35 papers (9.6%). Symbolic processing concentrates in the General MIR and Instrumental domains (40 and 28 papers respectively), driven largely by MIDI-based transcription and optical music recognition work; Solo Singing and Ensemble remain almost exclusively audio-based (45/52 and 8/10 papers respectively). Modality labels were assigned and validated by the same procedure as domain labels.

## 3.2 Classification matrix

Table 7 presents the domain × modality matrix for the full corpus.

**Table 7:** Classification matrix: domain (rows) × modality (columns).

| Domain | Audio | Symbolic | Multimodal | Total |
|---|---|---|---|---|
| Solo Singing | 45 (87%) | 2 (4%) | 5 (10%) | 52 |
| Ensemble | 8 (80%) | 1 (10%) | 1 (10%) | 10 |
| Instrumental | 96 (72%) | 28 (21%) | 9 (7%) | 133 |
| General MIR | 110 (65%) | 40 (24%) | 20 (12%) | 170 |
| **Total** | **259 (71.0%)** | **71 (19.5%)** | **35 (9.6%)** | **365** |

*Note.* Within-domain percentages calculated as proportion of row total; rows may not sum to 100% due to rounding.

The Audio–General MIR cell is the largest (n = 110), followed by Audio–Instrumental (n = 96); together they account for 56.4% of the corpus. Vocal domains are strikingly audio-bound: across Solo Singing and Ensemble combined, only 3 symbolic papers exist — consistent with the near-absence of score-informed vocal processing reported in earlier reviews.

## 3.3 Primary MIR task distribution

Unlike the domain and modality axes, task classification in this review is data-driven: the 365 papers were partitioned into seven topic clusters by the K-Means model selected in Section 2.3 (validated against Agglomerative, NMF, and LDA alternatives). Table 8 shows the resulting distribution.

**Table 8:** Topic-cluster distribution of included studies (K-Means, k = 7).

| # | Topic cluster | Papers | % |
|---|---|---|---|
| 0 | Instrument Recognition / Classification | 47 | 12.9% |
| 1 | Automatic Music Transcription (AMT) | 74 | 20.3% |
| 2 | Singing Voice / Melody Extraction | 41 | 11.2% |
| 3 | Source Separation | 72 | 19.7% |
| 4 | Multi-Pitch Estimation | 22 | 6.0% |
| 5 | Music Education & Performance Assessment | 79 | 21.6% |
| 6 | Optical Music Recognition (OMR) | 30 | 8.2% |
| | **Total** | **365** | **100%** |

*Note.* Each paper belongs to exactly one cluster (flat partition); cluster names were assigned by the review team from each cluster's highest-weighted TF-IDF terms.

Three clusters dominate: Music Education & Performance Assessment (21.6%), Automatic Music Transcription (20.3%), and Source Separation (19.7%), together covering three-fifths of the corpus. The prominence of the education/assessment cluster — the largest single cluster — indicates that applied, human-facing systems constitute a major share of recent intelligent music processing research, alongside the traditional signal-level tasks. Multi-Pitch Estimation is the smallest cluster (6.0%), and cross-referencing clusters against domain tags shows the vocal domains concentrate in Singing Voice / Melody Extraction (22 of its 41 papers are Solo Singing) and Source Separation (5 of the 10 Ensemble papers), while Instrument Recognition and OMR contain almost no vocal papers at all.

## 3.4 Summary

The corpus of 365 studies shows accelerating publication volume through 2025, a field-wide center of gravity in audio-only processing (71.0%), and a task landscape led by education/assessment applications, transcription, and source separation. Vocal performance research — solo and especially ensemble — represents a modest fraction of the field, and remains overwhelmingly audio-bound, with symbolic and multimodal vocal processing nearly absent.

[NOTE FOR DANA'S PASS: all figures recomputed from phase3/phase3_output_real/cleaned_corpus.csv + phase4/.../FINAL_SELECTED_assignments.csv + domain_modality_tags.csv (v2, post-validation); full crosstabs in numbers_manifest.txt]
