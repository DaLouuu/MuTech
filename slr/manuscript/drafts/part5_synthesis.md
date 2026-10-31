# PART 5 DRAFT — Sections 4.1, 4.2, and final 4.5 (Synthesis: RQ1, RQ2)
<!-- Paste-ready. [NOTE:] markers = flags for the team, delete before submission. -->

## 4.1 RQ1: MIR tasks, modeling paradigms, and architectural approaches

**RQ1:** *What MIR tasks, modeling paradigms, and architectural approaches have been most frequently applied to solo singing, ensemble or choral singing, and instrumental performance between 2020 and 2026?*

[NOTE for Part 2 owner (Marian): the intro currently states "2015 and 2025" in RQ1 — the actual search window is 2020–2026 (PUBYEAR > 2019); please align the intro wording.]

The task landscape is reported in Section 3.3: seven data-driven topic clusters led by education/assessment applications (21.6%), automatic transcription (20.3%), and source separation (19.7%). This section addresses the paradigms and architectures within them. Architectural evidence was extracted by the same abstract-level lexical pass used throughout the synthesis (Section 2.4); families are non-exclusive, since papers may combine several. Table 9 summarizes prevalence and change across the review period.

**Table 9:** Architecture-family prevalence (papers whose abstracts mention the family; families are non-exclusive, and 46% of abstracts name no family at all — percentages describe the 54% that do specify their architecture).

| Family | Papers | % of corpus | 2020–2022 | 2023–2026 |
|---|---|---|---|---|
| CNN / convolutional | 119 | 32.6% | 37.4% | 30.2% |
| RNN / LSTM / GRU | 68 | 18.6% | 21.1% | 17.4% |
| Transformer / attention | 48 | 13.2% | 8.9% | 15.3% |
| Classical ML (SVM, RF, HMM) | 32 | 8.8% | 8.1% | 9.1% |
| U-Net / encoder–decoder | 31 | 8.5% | 8.9% | 8.3% |
| GAN | 6 | 1.6% | 2.4% | 1.2% |
| NMF / signal processing | 9 | 2.5% | 4.1% | 1.7% |
| Diffusion | 2 | 0.5% | 0.0% | 0.8% |

Convolutional architectures remain the field's default across every cluster and every domain, though their share is declining (37.4% of 2020–2022 papers to 30.2% of 2023–2026 papers). The only family clearly rising is the Transformer, whose share climbs from 8.9% of 2020–2022 papers to 15.3% of 2023–2026 papers, with end-to-end attention models appearing even in traditionally pipeline-heavy tasks such as optical music recognition [Ríos-Vila et al., 2022]. Notably, the generative-model wave visible in adjacent audio fields has barely reached this corpus: GANs appear in six papers and diffusion models in two — the architectural conservatism mirrors the modest foundation-model adoption reported in Section 4.4.

Individual tasks show distinct architectural signatures. Instrument recognition is a near-monoculture: 64% of its papers specify convolutional models [Dubey et al., 2023], with classical ML (23%) as the main alternative. Source separation is the U-Net's home territory — 24% of its papers use encoder–decoder architectures against 8.5% corpus-wide [Kostrzewa et al., 2026]. Transcription blends convolutional and recurrent modeling (35% and 30% respectively), exemplified by U-Net-style convolutional transcription systems [Scarpiniti et al., 2023]. Viewed by performance domain, solo singing, instrumental, and general MIR research all lead with CNNs (33%, 32%, 34%); the small ensemble corpus leans recurrent (40%), though at n = 10 this is indicative rather than conclusive. Emerging in singing-voice work specifically is the reuse of pre-trained self-supervised speech frontends [Yamamoto et al., 2023] — consistent with, but not yet reversing, the low corpus-wide pre-training adoption noted in Section 4.4.

## 4.2 RQ2: Influence of data modality on system design

**RQ2:** *How do choices of data modality (audio, symbolic, or multimodal) influence system design, learning strategies, and evaluation practices across these musical domains?*

Modality shapes system design in two visible ways and, contrary to expectation, fails to shape it in a third. Table 10 summarizes.

**Table 10:** Design patterns by modality (n = 365; percentages within modality).

| | Audio (n=259) | Symbolic (n=71) | Multimodal (n=35) |
|---|---|---|---|
| Dominant families | CNN 36%, RNN 19% | CNN 31%, RNN 28% | fusion-specific; CNN 9%, RNN 0% |
| Task concentration | separation, education, instrument recognition | AMT (33 papers), OMR (20) | education (11), OMR (9) |
| Objective metrics in abstract | 49.8% | 42.3% | 42.9% |
| Subjective evaluation in abstract | 2.7% | 2.8% | 2.9% |

First, modality steers architecture. Symbolic systems lean on sequence modeling — recurrent families appear in 28% of symbolic papers versus 19% of audio papers, reflecting the token-like structure of MIDI and notation data. Multimodal systems, by contrast, are backbone-light: standard family names largely vanish (no recurrent mentions at all, convolutional in only 9%) with abstracts typically describing task-specific fusion or alignment designs rather than naming a backbone family. Second, modality maps onto task ecosystems rather than spreading evenly: symbolic processing lives almost entirely inside transcription (33 of 71 symbolic papers) and optical music recognition (20), and OMR is in turn almost purely non-audio (a single audio paper). Multimodal work concentrates in education/assessment systems and OMR, the two clusters where scores, video, or interface data naturally accompany audio.

Third — and this is the corpus's most instructive negative result — modality does *not* influence evaluation practice. Objective-metric reporting is closely similar across audio, symbolic, and multimodal papers (49.8%, 42.3%, 42.9%), and subjective evaluation is uniformly rare (2.7–2.9%) regardless of modality. Whatever evaluation-culture differences might be expected from multimodal, human-facing systems, they do not materialize: the evaluation monoculture documented in Section 4.4 (Gap 4) is modality-independent. For the vocal domains this compounds the pattern reported in Section 3.2: solo and ensemble research is not only overwhelmingly audio-bound (only 3 symbolic papers across 62), it also inherits audio's objective-metric-centric evaluation habits, leaving perceptual quality — arguably the core concern of vocal performance — largely unmeasured.

## 4.5 Summary

[NOTE: this replaces the placeholder proposal pasted earlier — now final, since 4.1–4.4 share the same evidence base.]

Across the four research questions, the synthesis shows a field that has consolidated technically while diversifying in application. Convolutional architectures remain the default and Transformers are the only clearly rising family, yet generative and foundation-model paradigms remain marginal (RQ1). Modality steers architecture choice and task ecosystem — symbolic work concentrates in transcription and OMR, multimodal work in applied assessment settings — but leaves the field's evaluation monoculture untouched (RQ2). The challenges practitioners report are dominated by generalization and real-world robustness, while reproducibility languishes at the rubric floor for nearly half the corpus (RQ3). Structurally, the fastest-growing research area is education- and assessment-oriented systems, which also form the connective tissue of the field's similarity network, while the least-connected themes — OMR and ensemble processing — coincide exactly with the least-served domains (RQ4). The practices that would make this growth cumulative — shared benchmarks, released code, perceptual evaluation, and coverage of ensemble and score-informed vocal processing — remain the field's clearest unfinished business.

[NOTE FOR DANA'S PASS: Table 9/10 numbers and all percentages recomputed from cleaned_corpus.csv + domain_modality_tags.csv (architecture/eval-style lexical passes documented in phase6_manuscript/); citations verified 1:1 against the corpus.]
