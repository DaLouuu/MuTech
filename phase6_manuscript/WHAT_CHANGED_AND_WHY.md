# What Changed and Why — SLR Update Brief for the Team

*Covers sections 2.3–2.4, 3.1–3.4, and all of Section 4 (Parts 3, 4, 5, 6 — Kean).
Every change below has a receipt in `phase6_manuscript/` in the repo. Read this
before Dana's final pass so no one is surprised by Dr. Ryan's questions.*

## The one-sentence version

The old paper described a 100-paper, manually-coded review; the new pipeline is a
365-paper, automated one — so several of the old paper's claims weren't just
outdated, they were now **false**, and we changed them with evidence instead of
quietly keeping them.

## Claims that REVERSED (know these before defending the paper)

| # | Old paper said | New paper says | Why it changed | Receipt |
|---|---|---|---|---|
| 1 | Solo Singing is the largest domain (35%) | General MIR (47%) and Instrumental (36%) dominate; Ensemble is 2.7% | The broad Scopus+IEEE query captures the whole field, not a vocal-centered slice | `domain_modality_tags.csv`, `numbers_manifest.txt` |
| 2 | "Instrumental domain is underdeveloped (16 papers)" — Gap 1 | Instrumental is the 2nd-largest domain (133); **ensemble** is the real gap (10 papers) | Old claim described the old corpus; inverted in the new one | Table 6/8 + `numbers_manifest.txt` |
| 3 | Pre-trained audio-language models "increasingly used as backbones" | Adoption is modest and nearly flat: 8% → 10% of papers | We measured it; the corpus doesn't support the trend claim | 4.4 + lexical pass documented in `part6_synthesis.md` |
| 4 | Multimodal systems use "mixed evaluation with user studies" | Evaluation practice is **modality-independent**: subjective evaluation ~3% everywhere | Measured across all 365 papers — the difference doesn't exist | Table 10 in `part5_synthesis.md` |
| 5 | 30/45 rubric score "required for inclusion" | Rubric is **descriptive only** — no paper excluded by score | Corpus was already frozen by Rayyan screening; a post-hoc gate would invalidate phases 3–5 or be a false claim. Dana approved 07/11. **40% of the corpus scores below the old threshold** — proof the gate never operated | `quality_scores.csv`, 2.3 |

## Structural changes (not reversals, but big)

- **Classification is now automated.** The hand-coded domain×modality matrix and
  coding tags (old Tables 3–5) are replaced by: keyword tagging (validated on a
  sample by Kean — 3 mistags found and fixed) + K-Means topic clustering (k=7,
  chosen over NMF/Agglomerative/LDA with tuning + held-out validation).
- **Two new validation layers the old paper never had:** every clustering model
  was validated on a held-out split, and Phase 5's network analysis independently
  confirms the clusters (modularity 0.53; Louvain agrees at ARI 0.53).
- **Table 11 (challenges) lost a row honestly.** "Evaluation inconsistency"
  turned out to match papers *doing* subjective evaluation, not papers reporting
  inconsistency — strict recount: 1 paper. It's now reported as a finding
  (evaluation-practice concerns are invisible at abstract level) instead of a table row.
- **All evidence is abstract-level and says so.** No claim pretends we read 365
  full texts. Synthesis claims cite corpus papers verified 1:1 against the dataset.

## If Dr. Ryan asks…

- *"Why does the paper contradict the previous version?"* → The corpus and method
  changed; keeping the old claims would have been misstating what was done. Every
  change is measured, not stylistic.
- *"Was quality appraisal done?"* → Yes, descriptively: his own (Borbon & Ebardo)
  rubric, adapted to AI-assisted abstract-level scoring, disclosed as such,
  validated on a human-reviewed sample, no exclusion gate. [Heads-up: ideally
  someone walks him through this *before* he reads it cold — it adapts his rubric.]
- *"Can I verify number X?"* → Every statistic in sections 2.3–4.5 is recomputable
  from `phase6_manuscript/numbers_manifest.txt` + the CSVs in one lookup.

## Still open (owners needed)

- Intro RQ1 still says "2015 and 2025" → must become 2020–2026 (**Marian**, Part 2).
- Abstract still describes the old methodology (Part 1 owner).
- Appendices still say "100 studies" / old PRISMA caption (Part 8 owner).
- References must be rebuilt from the new corpus; note: two "Mezza et al. 2024"
  papers exist — key them 2024a/b (Part 8 owner).
