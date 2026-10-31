# SLR Historical Artifacts Archive (Prior Baseline Runs)

This directory preserves intermediate output artifacts and baseline model metrics generated during earlier iterations of the Systematic Literature Review (prior to the consolidated 2026 pipeline engine overhaul).

### Archive Subdirectories
* `prisma/`: Baseline deduplication, raw exclusion lists, and match candidates from initial Phase 1-2 screening passes.
* `representations/`: Historical TF-IDF matrices and cleaned tokens (prior to PMI phrase mining and 35-D LSA projections).
* `models/`: Baseline 4-model comparison results (`model_comparison_final.csv`, `FINAL_MODEL_SELECTION.txt`, etc.).
* `network/`: Historical Louvain community network exports (`cluster_network.gexf`).

---

### Canonical Active Artifacts
For current research synthesis, manuscript updates, and visualization, consult the active single-source-of-truth directories:
* `slr/outputs/prisma/phase1_merged_deduplicated.csv` & `phase2_screened_corpus.csv`
* `slr/outputs/representations/phase3_cleaned_corpus.csv`, `phase3_pmi_collocations.csv`, `phase3_tfidf_matrix.npz`
* `slr/outputs/models/phase4_clustered_corpus.csv`, `phase4_model_comparison.csv`, `phase4_soft_topic_distributions.csv`
* `slr/outputs/network/phase5_cluster_network.gexf`, `phase5_temporal_topic_evolution.csv`
