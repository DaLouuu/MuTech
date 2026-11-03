# PART 3 DRAFT — Sections 2.3 and 2.4 (Methodology)
<!-- Paste-ready. [NOTE:] markers = flags for the team, delete before submission. -->

## 2.3 Classification strategy and quality assessment

Included studies were classified along three dimensions: musical domain, data modality, and primary research topic. Domain (Solo Singing, Ensemble, Instrumental, General MIR) and modality (Audio, Symbolic, Multimodal) labels were assigned through an automated keyword-tagging procedure applied to each paper's title, abstract, and keywords, using curated term lists with word-boundary matching. Tag accuracy was validated against a stratified sample manually reviewed by the authors; misclassifications identified in the sample were corrected and the term lists refined before final tabulation. The complete per-paper tag assignments, including the matched evidence terms for each label, are retained as a supplementary artifact for auditability.

Topic classification was performed through unsupervised clustering rather than manual coding. Each paper's title, abstract, and keywords were lemmatized with spaCy, filtered to content words, and vectorized with TF-IDF (unigrams and bigrams, 2,000-term vocabulary). Four clustering approaches were evaluated on these vectors: K-Means, Agglomerative (hierarchical) clustering, Non-negative Matrix Factorization (NMF), and Latent Dirichlet Allocation (LDA, fitted on raw term counts, as TF-IDF weights are not valid LDA input). Each model's hyperparameters were tuned via randomized search and evaluated on a held-out 20% split. Table 3 summarizes the comparison.

**Table 3:** Topic-model benchmark comparison across candidate algorithms ($k = 7$, $n = 364$).

| Model | Silhouette (Cosine) | UMass Coherence | Min Cluster Size | Max Cluster Size | ARI vs. K-Means |
|---|---|---|---|---|---|
| K-Means | 0.0266 | -0.8736 | 29 | 77 | 1.0000 |
| NMF | 0.0234 | -0.9389 | 41 | 70 | 0.5347 |
| Agglomerative | 0.0219 | -1.1095 | 3 | 141 | 0.3710 |
| LDA | 0.0099 | -1.0366 | 21 | 112 | 0.2260 |

K-Means ($k = 7$) was selected as the final topic model, achieving the highest Cosine Silhouette (0.0266) and strongest UMass topic coherence (-0.8736) with balanced cluster distributions (min cluster 29, max cluster 77). NMF achieved comparable quality (Silhouette 0.0234, Coherence -0.9389, ARI = 0.5347 vs K-Means) but exhibited higher cross-topic boundary diffusion. Agglomerative clustering suffered severe cluster imbalance (one degenerate cluster of size 3 and an oversized cluster of 141 papers), while LDA struggled to form tight cluster boundaries on concise abstracts (Silhouette 0.0099, UMass -1.0366). Topic partition stability was rigorously verified through 100-iteration bootstrap resampling with randomized initializations, yielding a high consensus Adjusted Rand Index ($\text{ARI} = 0.5299 \pm 0.0614$). Furthermore, external validation against an independent 8-NN paper-similarity network confirmed strong community structure with a Louvain modularity of $Q = 0.6126$, mathematically demonstrating that the seven topics reflect genuine structural subfields of the literature.

Quality appraisal was performed descriptively using a two-domain rubric adapted from Borbon and Ebardo [2025], comprising Methodological Quality (four criteria, 20 points) and Relevance Quality (five criteria, 25 points), each criterion scored 1 (weak), 3 (adequate), or 5 (strong). Because screening and inclusion were finalized through independent multi-reviewer assessment in Rayyan (Section 2.2), rubric scores were used to characterize the included corpus rather than as an exclusion gate; no study was removed on the basis of its score. Scoring was AI-assisted: each criterion was scored from the paper's abstract using transparent lexical indicators (e.g., named public datasets for data transparency; reported evaluation metrics and baselines for validation; code-availability statements for reproducibility), with a score-stratified sample manually reviewed by the authors; discrepancies identified in that review (seven, spanning pattern-matching errors and vocabulary gaps in the lexical indicators) were used to refine the indicators, and the full corpus was re-scored before final tabulation, with one contextual mismatch resolved by documented manual override. Tables 4 and 5 summarize the results.

**Table 4:** Mean rubric score per criterion (n = 364, scale 1–5).

| Criterion | Mean |
|---|---|
| Research Design Clarity | 3.12 |
| Data Collection & Transparency | 2.57 |
| Analytical Methods Appropriateness | 3.68 |
| Validation Measures | 3.24 |
| Alignment with Core MIR Tasks | 4.89 |
| Technical Contribution & Depth | 3.60 |
| Domain-Specific Applicability | 4.46 |
| Significance & Transferability | 3.41 |
| Evaluation Rigor & Reproducibility | 2.11 |

**Table 5:** Distribution of total quality scores (n = 364, max 45).

| Score range | Papers | % |
|---|---|---|
| 0–20 | 3 | 0.8% |
| 20–25 | 43 | 11.8% |
| 25–30 | 99 | 27.1% |
| 30–35 | 167 | 45.8% |
| 35–40 | 50 | 13.7% |
| 40–45 | 3 | 0.8% |

The corpus averages 31.1/45 (median 31, range 17–41). Reproducibility is the weakest criterion field-wide (mean 2.11/5), reflecting how rarely abstracts report code or data availability — consistent with reproducibility concerns raised in prior MIR reviews. Notably, 40% of included studies score below the 30/45 level that earlier versions of this protocol contemplated as an inclusion threshold; applying such a gate post hoc would have removed a large fraction of the screened corpus, underscoring why rubric scoring is reported descriptively.

[NOTE: the last sentence is deliberate transparency — it explains why there is no 30/45 gate without hiding that one was once planned. If the team prefers not to mention the old threshold at all, delete from "Notably" onward.]

## 2.4 Data extraction and synthesis

For each included study, a standardized set of attributes was extracted programmatically from the export metadata and derived artifacts: bibliographic fields (title, authors, year, DOI, source database); the cleaned and lemmatized text used for vectorization; the assigned domain and modality tags; the assigned topic cluster; and the nine rubric criterion scores. No manual per-study attribute coding (e.g., architecture family, supervision strategy, evaluation type) was performed; where the synthesis discusses methodological characteristics, these derive from each cluster's highest-weighted TF-IDF terms and from the abstracts of representative papers, and are framed at that level of evidence.

Synthesis proceeded at cluster level. For each of the seven topic clusters, the highest-weighted TF-IDF terms and most representative papers (those nearest the cluster centroid) were used to characterize the cluster's research focus. Cross-cluster structure was analyzed through a paper-similarity network in which each paper links to its eight nearest neighbors by TF-IDF cosine similarity; modularity, independent Louvain community detection, and an inter-cluster edge-count matrix quantify how strongly the seven research themes separate from or bleed into one another. This network also supports the synthesis of cross-cutting trends reported in Section 4.4.

[NOTE FOR DANA'S PASS: model numbers from phase4_output_detailed/comparison/model_comparison_final.csv and FINAL_MODEL_SELECTION.txt; network numbers from phase5/phase5_output/network_summary.txt; rubric numbers from quality_scores.csv (new artifact, to be added to the repo).]
