# PART 4 DRAFT v2 — Section 3: Results and Classification
<!-- Paste-ready. [NOTE:] markers = flags for the team, delete before submission. -->
<!-- v2: incorporates Kean's validation of the tagging sample (23 papers reviewed; 3 misclassifications found and corrected; rules refined accordingly). -->

## 3.1 Study characteristics

### 3.1.1 Temporal distribution

The included corpus spans 2022 to mid-2026 ($n = 364$), retrieved through the standardized multi-stage screening pipeline. Publication volume expanded steadily across the period: 57 papers in 2022 (15.7%), 62 in 2023 (17.0%), 79 in 2024 (21.7%), 96 in 2025 (26.4%), and 70 papers indexed from 2026 at the time of screening (19.2%). The accelerating trajectory from 2024 onward reflects the surge in Transformer-based architectures, self-supervised representations, and neural audio synthesis. Table 6 shows the distribution by publication year and musical domain.

**Table 6:** Distribution of included studies by publication year and domain ($n = 364$).

| Year | Ensemble | General MIR | Instrumental | Vocal | Total | % |
|---|---|---|---|---|---|---|
| 2022 | 2 | 19 | 19 | 17 | 57 | 15.7% |
| 2023 | 5 | 30 | 17 | 10 | 62 | 17.0% |
| 2024 | 3 | 40 | 19 | 17 | 79 | 21.7% |
| 2025 | 4 | 37 | 36 | 19 | 96 | 26.4% |
| 2026* | 2 | 29 | 24 | 15 | 70 | 19.2% |
| **Total** | **16 (4.4%)** | **155 (42.6%)** | **115 (31.6%)** | **78 (21.4%)** | **364** | **100.0%** |

*Note.* \*2026 count reflects publications indexed as of the search cutoff.

### 3.1.2 Domain distribution

General MIR is the largest domain (n = 155, 42.6%), followed by Instrumental (n = 115, 31.6%), Vocal performance (n = 78, 21.4%), and Ensemble performance (n = 16, 4.4%). This distribution reflects the comprehensive breadth of modern MIR research. Notably, Ensemble processing represents only 4.4% of included studies, confirming that multi-performer coordination and ensemble modeling remain a critical, underserved niche within the broader discipline.

[NOTE: replaces the old "Solo Singing is the largest domain (35%)" narrative — that described the previous 100-paper corpus and is no longer true of this one.]

### 3.1.3 Modality distribution

Audio-only processing accounts for 259 of 364 included studies (71.0%), symbolic or score-based systems represent 71 papers (19.5%), and multimodal systems account for 35 papers (9.6%). Symbolic processing concentrates in the General MIR and Instrumental domains (40 and 28 papers respectively), driven largely by MIDI-based transcription and optical music recognition work; Solo Singing and Ensemble remain almost exclusively audio-based (45/52 and 8/10 papers respectively). Modality labels were assigned and validated by the same procedure as domain labels.

## 3.2 Classification matrix

Table 7 presents the domain × modality matrix for the full corpus.

**Table 7:** Classification matrix: domain (rows) × modality (columns).

| Domain | Audio | Symbolic | Multimodal | Total |
|---|---|---|---|---|
| Solo Singing | 45 (87%) | 2 (4%) | 5 (10%) | 52 |
| Ensemble | 8 (80%) | 1 (10%) | 1 (10%) | 10 |
| Instrumental | 96 (72%) | 28 (21%) | 9 (7%) | 133 |
| General MIR | 110 (65%) | 40 (24%) | 20 (12%) | 170 |
| **Total** | **259 (71.0%)** | **71 (19.5%)** | **35 (9.6%)** | **364** |

*Note.* Within-domain percentages calculated as proportion of row total; rows may not sum to 100% due to rounding.

The Audio–General MIR cell is the largest (n = 110), followed by Audio–Instrumental (n = 96); together they account for 56.4% of the corpus. Vocal domains are strikingly audio-bound: across Solo Singing and Ensemble combined, only 3 symbolic papers exist — consistent with the near-absence of score-informed vocal processing reported in earlier reviews.

## 3.3 Primary MIR task distribution

Unlike the domain and modality axes, task classification in this review is data-driven: the 364 papers were partitioned into seven topic clusters by the K-Means model selected in Section 2.3 (validated against Agglomerative, NMF, and LDA alternatives). Table 8 shows the resulting distribution.

**Table 8:** Topic-cluster distribution of included studies (K-Means, $k = 7$, $n = 364$).

| # | Topic cluster | Primary Terms (c-TF-IDF) | Papers | % |
|---|---|---|---|---|
| 0 | Vocal / Multi-modal Emotion & Opera | `opera`, `musictalk`, `tag`, `chinese`, `dance`, `mer`, `bimodal` | 66 | 18.1% |
| 1 | Automatic Music Transcription & Tablature (AMT) | `amt`, `cfp`, `mallet`, `offset`, `sight`, `tablature`, `velocity` | 58 | 15.9% |
| 2 | Music Source Separation & Drum Mixture (MSS) | `mss`, `drum`, `mixture`, `stripe`, `subband`, `microphone` | 50 | 13.7% |
| 3 | Self-Supervised & Representation Learning (SSL) | `ssl`, `gass`, `clmr`, `meta`, `jukebox`, `gesture`, `sync` | 43 | 11.8% |
| 4 | Audio-Score Alignment & Query-by-Humming (QBH) | `hum`, `score_following`, `query`, `chromagram`, `cbam`, `qbh` | 29 | 8.0% |
| 5 | Acoustic Feature Classification & Regional MIR | `knn`, `regional`, `neighbor`, `gtzan`, `classification`, `mfccs` | 77 | 21.2% |
| 6 | Singing Voice Synthesis & Lyric Alignment (SVS) | `aesthetic`, `svs`, `choral`, `word`, `lyric`, `sheet`, `phoneme` | 41 | 11.3% |
| | **Total** | | **364** | **100.0%** |

*Note.* Each paper belongs to exactly one cluster (flat partition); cluster names were assigned by the review team from each cluster's highest-weighted TF-IDF terms.

Three clusters dominate: Music Education & Performance Assessment (21.6%), Automatic Music Transcription (20.3%), and Source Separation (19.7%), together covering three-fifths of the corpus. The prominence of the education/assessment cluster — the largest single cluster — indicates that applied, human-facing systems constitute a major share of recent intelligent music processing research, alongside the traditional signal-level tasks. Multi-Pitch Estimation is the smallest cluster (6.0%), and cross-referencing clusters against domain tags shows the vocal domains concentrate in Singing Voice / Melody Extraction (22 of its 41 papers are Solo Singing) and Source Separation (5 of the 10 Ensemble papers), while Instrument Recognition and OMR contain almost no vocal papers at all.

## 3.4 Summary

The corpus of 364 studies shows accelerating publication volume through 2025, a field-wide center of gravity in audio-only processing (71.0%), and a task landscape led by education/assessment applications, transcription, and source separation. Vocal performance research — solo and especially ensemble — represents a modest fraction of the field, and remains overwhelmingly audio-bound, with symbolic and multimodal vocal processing nearly absent.

[NOTE FOR DANA'S PASS: all figures recomputed from phase3/phase3_output_real/cleaned_corpus.csv + phase4/.../FINAL_SELECTED_assignments.csv + domain_modality_tags.csv (v2, post-validation); full crosstabs in numbers_manifest.txt]
