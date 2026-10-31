# Systematic Literature Review (SLR) Research Pipeline
## Intelligent Music Processing for Singing, Ensembles, and Instrumental Performance

This directory contains the complete academic research pipeline analyzing **365 peer-reviewed studies** collected from Scopus and IEEE Xplore, synthesized following the **PRISMA 2020** methodology.

---

## Execution Interfaces (Phases 1 to 5)

Rather than running separate scripts for each phase, the research pipeline can be run through any of these interfaces:

| Interface Type | Entry Point | Description |
|---|---|---|
| **Web UI Dashboard** | `python slr/pipeline_ui_server.py` | Local web dashboard at `http://localhost:8000` with controls for each phase, parameter tuning, log outputs, and validation status. |
| **Interactive Widget Notebook** | [`notebooks/MuTech_SLR_Interactive_UI.ipynb`](notebooks/MuTech_SLR_Interactive_UI.ipynb) | Jupyter notebook interface using `ipywidgets`. |
| **Sequential Notebook** | [`notebooks/MuTech_SLR_Consolidated_Pipeline.ipynb`](notebooks/MuTech_SLR_Consolidated_Pipeline.ipynb) | End-to-end notebook containing the full execution flow, validation checks, and literature citations. |
| **Command-Line Interface (CLI)** | `python slr/run_pipeline.py [--all \| --phase N]` | CLI runner for individual phases or full automated pipeline runs. |

---

## Directory Structure

```text
slr/
├── data/                               # Raw and screening data
│   ├── 01_raw/                         # Scopus and IEEE export files
│   └── 02_screening/                   # Rayyan screening decision exports
│
├── outputs/                            # Pipeline output artifacts by phase
│   ├── prisma/                         # Deduplicated and screened records
│   ├── representations/                # TF-IDF matrix, cleaned corpus, PMI collocations
│   ├── models/                         # Model benchmark comparison, topic clusters, soft distributions
│   └── network/                        # Similarity graph (.gexf) and temporal evolution files
│
├── archive/                            # Archived baseline runs
│   └── prior_runs/                     # Baseline run outputs (prisma, models, network, representations)
│
├── manuscript/                         # Publication files
│   ├── drafts/                         # Manuscript sections (Methodology, Results, Synthesis)
│   ├── figures/                        # Publication figures
│   └── tables/                         # Verified evidence matrices, quality assessment, numbers manifest
│
├── guides/                             # Methodology guides and audit documentation
│   ├── ROOT_CAUSE_AUDIT.md             # Defect audit and resolution record
│   ├── SLR_METHODOLOGY_REFERENCES.md   # Peer-reviewed methodology citations (2021–2026)
│   ├── SLR_METHODOLOGY_REFERENCES.docx # Formatted Word reference document
│   ├── PIPELINE_CONFIGURATION_GUIDE.md # Pipeline parameter guide
│   ├── PIPELINE_CONFIGURATION_GUIDE.docx # Pipeline parameter guide (Word)
│   └── SLR_PAPER_UPDATE_GUIDE.md       # Manuscript update reconciliation guide
│
├── notebooks/                          # Jupyter notebooks
│   ├── MuTech_SLR_Consolidated_Pipeline.ipynb   # Complete pipeline (Phases 1-5)
│   ├── MuTech_SLR_Interactive_UI.ipynb          # Interactive in-notebook UI
│   └── MuTech_Phase4_Detailed_DeepDive.ipynb    # Model parameter sensitivity analysis
│
├── src/                                # Core pipeline engine
│   ├── __init__.py
│   └── pipeline_engine.py              # Modular pipeline functions and validation checks
│
├── pipeline_ui_server.py               # Local FastAPI web dashboard server
├── run_pipeline.py                     # CLI pipeline runner
└── requirements.txt                    # Python dependencies
```

---

## Automated Validation Gates (Checks & Balances)

Every phase transition is guarded by automated assertions enforcing PRISMA compliance:

* **Gate 1 (Post-Phase 1):** Verifies non-empty database ingestion and ensures deduplication math accounts for all identified records ($\text{Identified} - \text{Duplicates} = \text{Unique}$).
* **Gate 2 (Post-Phase 2):** Verifies PRISMA study flow conservation and validates the 365 included study count against Rayyan human screening.
* **Gate 3 (Post-Phase 3):** Validates feature extraction, checks vocabulary size ($>500$ content terms), and verifies zero silent drops during text mining.
* **Gate 4 (Post-Phase 4):** Ensures all 4 models converge without degenerate/singleton clusters, computes both Cosine Silhouette and UMass Topic Coherence, and extracts c-TF-IDF keywords.
* **Gate 5 (Post-Phase 5):** Confirms 100% corpus node representation in the similarity graph, evaluates Louvain modularity, and synchronizes the live web dashboard.

---

## Pipeline Methodology Enhancements (Phases 3 to 5)

In accordance with rigorous 2021–2026 IEEE/Scopus bibliometric literature, the pipeline incorporates 5 major methodological enhancements:

1. **Automated PMI Collocation Mining (Phase 3):**
   * *Evidence:* Truică & Apostol (2021), *IEEE Access*, [doi:10.1109/ACCESS.2021.3083000](https://doi.org/10.1109/ACCESS.2021.3083000).
   * *Mechanism:* Calculates Pointwise Mutual Information (PMI) and Normalized PMI (NPMI) across document sliding word windows, automatically identifying and binding high-association domain compound phrases without subjective manual lists.
   * *Artifact:* `slr/outputs/representations/phase3_pmi_collocations.csv`.

2. **Scientific Domain Contextual Representations (SciBERT) (Phase 3/4):**
   * *Evidence:* Chen & Liu (2025), *IEEE AINIT*, [doi:10.1109/AINIT65432.2025.11034992](https://doi.org/10.1109/AINIT65432.2025.11034992).
   * *Mechanism:* Provides modular architecture in `extract_dense_embeddings()` supporting 35-D LSA (fast default) and deep contextual transformers (`allenai/scibert_scivocab_uncased`).

3. **Soft Multi-Topic Membership & Interdisciplinary Crossover Detection (Phase 4):**
   * *Evidence:* Grisales A. et al. (2023), *IEEE Access*, [doi:10.1109/ACCESS.2022.3232939](https://doi.org/10.1109/ACCESS.2022.3232939).
   * *Mechanism:* Evaluates continuous Dirichlet posterior topic distributions ($\theta_d$) from LDA and continuous weightings from NMF. Identifies primary and secondary topic assignments, computes Shannon entropy ($H$), and flags crossover papers spanning multiple MIR subfields.
   * *Artifact:* `slr/outputs/models/phase4_soft_topic_distributions.csv`.

4. **Topic Stability Bootstrapping (Phase 4):**
   * *Evidence:* Vangara et al. (2021), *IEEE Access*, [doi:10.1109/ACCESS.2021.3106879](https://doi.org/10.1109/ACCESS.2021.3106879).
   * *Mechanism:* Executes $B=10$ bootstrap iterations with randomized initializations, computing consensus Adjusted Rand Index (ARI) to mathematically prove topic stability against stochastic perturbations.

5. **Longitudinal Dynamic Topic Evolution Tracking (Phase 5):**
   * *Evidence:* Wang et al. (2024), *Scientometrics*, [doi:10.1007/s11192-023-04776-5](https://doi.org/10.1007/s11192-023-04776-5).
   * *Mechanism:* Dissects the corpus into chronological publication epochs (Foundational: 2020–2021, Consolidation: 2022–2023, Modern/Expansion: 2024–2026). Generates transition link data for alluvial / Sankey flow mapping.
   * *Artifacts:* `slr/outputs/network/phase5_temporal_topic_evolution.csv` and `.json`.

---

## Published Interactive SNA Dashboard

The interactive topic co-occurrence network generated in Phase 5 is published via GitHub Pages:
* Live Dashboard: [https://dalouuu.github.io/MuTech/](https://dalouuu.github.io/MuTech/)
* Source file: [`docs/index.html`](../docs/index.html)
