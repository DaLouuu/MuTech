# Phase 6 — Manuscript Update Artifacts (Parts 3 & 4: Kean)

Supplementary artifacts behind the rewritten manuscript sections 2.3–2.4
(methodology) and 3.1–3.4 (results). The Google Doc (SLR tab) is the canonical
manuscript text; the .md files here are the drafts those sections were pasted from.

| File | What it is |
| --- | --- |
| `domain_modality_tags.csv` | All 365 papers with automated domain (Solo Singing / Ensemble / Instrumental / General MIR) and modality (Audio / Symbolic / Multimodal) tags, **including the matched keyword evidence for every label**. Source for manuscript Tables 6–7. |
| `validation_sample_30.xlsx` | The stratified tag-validation sample as manually reviewed by Kean (3 misclassifications found → tagging rules refined, corpus re-tagged). This is the audit trail behind the "validated against a manually reviewed sample" claim in 3.1.1. |
| `quality_scores.csv` | Descriptive quality-rubric scores for all 365 papers: nine criteria (1/3/5, adapted from Borbon & Ebardo 2025) scored via transparent lexical indicators from abstracts. **Descriptive only — no paper was excluded by score.** Source for manuscript Tables 4–5. |
| `quality_spotcheck_15.xlsx` | Score-stratified scoring-validation sample as reviewed by Kean (7 discrepancies found → indicators fixed, corpus re-scored, 1 documented manual override). Audit trail behind the scoring-validation claim in 2.3. |
| `numbers_manifest.txt` | Every statistic in sections 3.1–3.3 recomputed from the repo CSVs (year×domain, domain×modality, cluster×domain crosstabs). Use this to verify any number in the manuscript in one lookup. |
| `part6_synthesis.md` | Paste-source draft for manuscript sections 4.3–4.5 (RQ3/RQ4 synthesis + summary proposal). Verified with a 5-pass protocol: citation integrity, independent numerical recompute (22/22), consistency with pasted 2.3–3.4, RQ/promise audit, and claim-level review. |
| `challenge_evidence.csv` | Paper-level evidence behind Table 11: every abstract that reports each challenge category, with domain, cluster, and citation. Note: the "evaluation inconsistency" category was audited and found to be a false-positive pattern (papers *performing* subjective evaluation, not reporting inconsistency); the strict recount (1 paper) is reported as a finding in 4.3 instead of a table row. |
| `part3_methodology.md` / `part4_results.md` | The paste-source drafts for manuscript sections 2.3–2.4 and 3.1–3.4. |

Reproducibility note: tags and scores derive from `phase3/phase3_output_real/cleaned_corpus.csv`
joined with `phase4/phase4_output_detailed/comparison/FINAL_SELECTED_assignments.csv` on
normalized title (365/365 matched). Scoring is abstract-level evidence and is disclosed as
such in the manuscript.
