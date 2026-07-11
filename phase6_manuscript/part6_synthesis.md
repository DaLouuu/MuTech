# PART 6 DRAFT — Sections 4.3, 4.4, and 4.5 (Synthesis: RQ3, RQ4)
<!-- Paste-ready. [NOTE:] markers = flags for the team, delete before submission. -->

## 4.3 RQ3: Domain-specific challenges and limitations

**RQ3:** *What domain-specific challenges and limitations are reported in current intelligent music processing systems, particularly with respect to generalization, data availability, and reproducibility?*

Challenges were identified through a lexical evidence pass over all 365 abstracts (the same abstract-level standard described in Section 2.4), grouping challenge language into four recurring categories. Table 11 reports how many papers in each domain surface each challenge in their abstracts; because abstracts understate what full texts discuss, these counts are conservative lower bounds.

**Table 11:** Challenge categories by domain (papers whose abstracts report the challenge).

| Challenge | Solo Singing (n=52) | Ensemble (n=10) | Instrumental (n=133) | General MIR (n=170) | Total |
|---|---|---|---|---|---|
| Generalization / robustness | 12 | 2 | 19 | 16 | 49 |
| Real-world / noisy conditions | 7 | 0 | 10 | 16 | 33 |
| Data scarcity | 4 | 0 | 3 | 9 | 16 |

A fourth candidate category, evaluation inconsistency, was screened for but proved essentially invisible at abstract level (one paper corpus-wide): concerns about evaluation practice surface not as an articulated challenge but through the reproducibility rubric (Section 2.3) and the near-absence of subjective evaluation documented in Section 4.4. Generalization is the most frequently reported challenge in every domain. In solo singing, cross-lingual and cross-style generalization is an explicit design goal of current synthesis work [Shen, 2025]; in instrumental research, systematic biases of transcription models across sound sources have been documented directly [Marták, 2026]; and in the ensemble domain, generalization across vocal styles and pitch distributions is assessed directly in vocal-quartet voice assignment [Cuesta, 2022]. Real-world degradation concerns concentrate where systems meet live use: opera recordings [Krause, 2021] and lead-instrument recognition in mixed real-world signals [Zheng, 2026] both report performance drops outside curated data. Data scarcity is reported most often for annotation-hungry tasks: note-level singing transcription [Qiu, 2024], drum source separation [Mezza et al., 2024], and multi-pitch estimation, where weakly aligned training data is used precisely because strongly aligned annotations are scarce [Weiss, 2021].

Reproducibility, the third concern named by RQ3, is better measured by the rubric of Section 2.3 than by abstract mentions: 47% of included papers score at the rubric floor (1/5) on Evaluation Rigor & Reproducibility, only 3% reach the top score, and just 7% of abstracts mention code or data availability at all. Whatever the actual code-release rate, the field does not treat reproducibility as abstract-worthy information, which is itself a finding.

The Ensemble column of Table 11 is nearly empty, and this absence is informative rather than reassuring: at 10 papers (2.7% of the corpus), ensemble research is too small to surface challenge patterns at all. The challenges documented in ensemble-focused reviews — synthetic-to-real transfer, absent benchmarks, proprietary recordings — are invisible at field scale because the field barely engages the domain.

## 4.4 RQ4: Methodological trends and research gaps

**RQ4:** *What overarching methodological trends and research gaps emerge from recent work?*

Three trends define the review period. (1) Deep learning is the default paradigm: 76% of all abstracts specify a deep or neural architecture, and every topic cluster is dominated by learned models. (2) The field's center of gravity is shifting toward applied, human-facing systems: the Music Education & Performance Assessment cluster grew from 11 papers in 2020–2022 to 68 in 2023–2026 — a 6.2× increase, far outpacing every signal-level task cluster (transcription grew 1.6×, source separation 1.1×). (3) Foundation-model adoption remains modest rather than transformative: mentions of pre-training, self-supervision, or transfer learning rise only from 8% of papers (2020–2022) to 10% (2023–2026), suggesting the pre-trained-backbone era reported in adjacent audio fields has not yet restructured intelligent music processing research.

[NOTE: trend (3) deliberately *reverses* the old draft's claim that pre-trained audio-language models are "increasingly used as backbones" — the corpus does not support that claim, and the old supporting citations are not in the new reference list.]

Four structural gaps emerge. **Gap 1 — ensemble research is a niche, not a pillar:** 10 papers in six and a half years, half of them on source separation, with synchrony analysis, intonation interaction, and conductor-following essentially unaddressed. **Gap 2 — score-informed vocal processing is nearly absent:** of 62 vocal papers (solo + ensemble), only 3 use symbolic representations, despite scores and lyrics being central to vocal practice. **Gap 3 — reproducibility infrastructure is missing:** the 47% rubric-floor rate and 7% code-mention rate indicate that shared artifacts remain the exception. **Gap 4 — subjective evaluation is systematically underused:** only 2.7% of papers mention listening tests, user studies, or perceptual evaluation, even though the largest topic cluster (education and assessment, 79 papers) exists precisely to serve human users.

Network analysis of the corpus (Section 2.4) quantifies how these themes relate structurally. The seven-cluster partition achieves a modularity of 0.53 on the paper-similarity network — well above the ~0.3 threshold conventionally taken as evidence of genuine community structure — and independent Louvain community detection agrees with the partition at an Adjusted Rand Index of 0.53. Within that structure, connectivity is uneven. Music Education & Performance Assessment is the corpus's connective tissue: it is the first- or second-largest external neighbor of every other cluster, absorbing 44% of Instrument Recognition's external similarity edges and between 19% and 31% of every other cluster's. Multi-Pitch Estimation, by contrast, is structurally an appendage of transcription, sending 49% of its external edges to AMT. Optical Music Recognition is the most self-contained cluster (69% of its edges are internal), consistent with its distinct image-based inputs. Source Separation is the most inward-looking of the audio clusters (64% internal), exchanging most of its external similarity with Singing Voice / Melody Extraction — the same vocal-centric coupling visible in Table 8. For future work, this connectivity map suggests that advances in the education/assessment cluster propagate widest, while OMR and ensemble-specific methods are least likely to benefit incidentally from progress elsewhere and require deliberate investment.

## 4.5 Summary

[NOTE: 4.5 spans all four RQs — RQ1/RQ2 belong to Part 5's owner. Proposed replacement below; whoever writes 4.1–4.2 should merge or veto.]

The synthesis reveals a field that has consolidated technically while diversifying in application. Deep learning is the uncontested default, and the fastest-growing research area is no longer a signal-level task but education- and assessment-oriented systems serving human users. Yet the practices that would make this growth cumulative — shared benchmarks, released code, perceptual evaluation, and coverage of underserved domains such as ensemble performance and score-informed vocal processing — lag well behind modeling ambition. The network structure of the corpus reinforces this reading: research themes are genuinely distinct communities, connected chiefly through applied assessment work, with the least-connected themes coinciding exactly with the least-served domains.

[NOTE FOR PART 8 (references): two Mezza et al. 2024 papers exist in the corpus; the citation in 4.3 refers to "Toward deep drum source separation" (the StemGMD dataset paper) — key as 2024a/2024b when building the reference list.]

[NOTE FOR DANA'S PASS: every statistic derives from challenge_evidence.csv, quality_scores.csv, phase5/cluster_relationship_matrix.csv, and the year×cluster crosstab; all citations are corpus papers verified against priority_records_from_rayyan.csv. The old 4.4 citations (Wu et al. 2023, Yuan et al. 2024, etc.) were removed — they are not in the new corpus.]
