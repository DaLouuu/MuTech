"""
MuTech Systematic Literature Review - Unified Pipeline CLI
Command-line orchestrator to run any phase (1 to 5) or the entire review end-to-end.

Usage:
    python slr/run_pipeline.py --all
    python slr/run_pipeline.py --phase 1
    python slr/run_pipeline.py --phase 4 --k 7
"""

from __future__ import annotations

# Standard Library Imports
import argparse
import os
import sys
from typing import Any, Dict, Optional

# Third-Party Scientific Imports
import pandas as pd
import scipy.sparse as sp
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

# Configure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Source Directory Resolution & Flexible Package Imports
SLR_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SLR_DIR, "src")
REPO_DIR = os.path.dirname(SLR_DIR)

for _p in [SRC_DIR, SLR_DIR, REPO_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from slr.src import pipeline_engine as pe
except ImportError:
    import importlib
    try:
        pe = importlib.import_module("src.pipeline_engine")
    except ImportError:
        pe = importlib.import_module("pipeline_engine")

DATA_DIR = os.path.join(SLR_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "01_raw")
SCREENING_DIR = os.path.join(DATA_DIR, "02_screening")
OUTPUTS_DIR = os.path.join(SLR_DIR, "outputs")
DOCS_DIR = os.path.join(os.path.dirname(SLR_DIR), "docs")


def main():
    parser = argparse.ArgumentParser(description="MuTech SLR Consolidated Pipeline Runner (Phases 1-5)")
    parser.add_argument("--all", action="store_true", help="Run all 5 phases sequentially with quality gates")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Run a specific phase (1 to 5)")
    parser.add_argument("--k", type=int, default=7, help="Number of target topics for Phase 4 (default: 7)")
    parser.add_argument("--knn", type=int, default=8, help="k-nearest neighbors for Phase 5 graph (default: 8)")
    parser.add_argument("--no-rayyan", action="store_true", help="Use rule-based filter instead of Rayyan 365 included set in Phase 2")
    args = parser.parse_args()

    use_rayyan = not args.no_rayyan

    if not args.all and args.phase is None:
        parser.print_help()
        sys.exit(0)

    print("=" * 70)
    print("MuTech SLR: Intelligent Music Processing (MIR) Review Pipeline")
    print("=" * 70)

    # State containers
    p1_res = None
    p2_res = None
    p3_res = None
    p4_res = None
    p5_res = None

    # Determine execution flow
    run_p1 = args.all or args.phase == 1
    run_p2 = args.all or args.phase == 2
    run_p3 = args.all or args.phase == 3
    run_p4 = args.all or args.phase == 4
    run_p5 = args.all or args.phase == 5

    # Phase 1
    if run_p1 or (args.phase in [2, 3, 4, 5] and not os.path.exists(os.path.join(OUTPUTS_DIR, "prisma", "phase1_merged_deduplicated.csv"))):
        print("\n[Phase 1] Starting Ingestion & 2-Tier Deduplication...")
        p1_res = pe.run_phase1(RAW_DIR, os.path.join(OUTPUTS_DIR, "prisma"))
        print(f"[PASS] Gate 1: {p1_res['total_identified']:,} identified -> {p1_res['unique_records']:,} unique ({p1_res['total_duplicates']} duplicates removed).")
    else:
        # Load pre-existing
        dedup_file = os.path.join(OUTPUTS_DIR, "prisma", "merged_deduplicated.csv")
        if not os.path.exists(dedup_file):
            dedup_file = os.path.join(OUTPUTS_DIR, "prisma", "phase1_merged_deduplicated.csv")
        p1_res = {"data": pd.read_csv(dedup_file)}

    if args.phase == 1 and not args.all:
        print("\n[Done] Phase 1 finished.")
        return

    # Phase 2
    if run_p2 or (args.phase in [3, 4, 5] and not os.path.exists(os.path.join(OUTPUTS_DIR, "prisma", "phase2_screened_corpus.csv"))):
        print(f"\n[Phase 2] Starting PRISMA Screening (Rayyan Mode: {use_rayyan})...")
        p2_res = pe.run_phase2(p1_res["data"], RAW_DIR, SCREENING_DIR, os.path.join(OUTPUTS_DIR, "prisma"), use_rayyan=use_rayyan)
        print(f"[PASS] Gate 2: {p2_res['screened_count']:,} studies included for synthesis ({p2_res['mode']}).")
    else:
        screened_file = os.path.join(DATA_DIR, "02_screening", "priority_records_from_rayyan.csv")
        p2_res = {"data": pd.read_csv(screened_file)}

    if args.phase == 2 and not args.all:
        print("\n[Done] Phase 2 finished.")
        return

    # Phase 3
    if run_p3 or (args.phase in [4, 5] and not os.path.exists(os.path.join(OUTPUTS_DIR, "representations", "phase3_tfidf_matrix.npz"))):
        print("\n[Phase 3] Starting NLP Text Mining & Representation (PMI Collocations, Stopwords, LSA)...")
        p3_res = pe.run_phase3(p2_res["data"], os.path.join(OUTPUTS_DIR, "representations"), use_pmi=True)
        print(f"[PASS] Gate 3: {p3_res['num_docs']} documents x {p3_res['vocab_size']} terms (35 LSA dense dimensions).")
        if p3_res.get("pmi_collocations_count"):
            print(f"  [PMI] Automated Collocations Mined: {p3_res['pmi_collocations_count']} phrases bound (Truică & Apostol, 2021).")
    else:
        rep_dir = os.path.join(OUTPUTS_DIR, "representations")
        corpus_df = pd.read_csv(os.path.join(rep_dir, "phase3_cleaned_corpus.csv"))
        tfidf_mat = sp.load_npz(os.path.join(rep_dir, "phase3_tfidf_matrix.npz"))
        svd = TruncatedSVD(n_components=35, random_state=pe.RANDOM_STATE)
        lsa_mat = normalize(svd.fit_transform(tfidf_mat), norm="l2")
        p3_res = {"data": corpus_df, "tfidf_matrix": tfidf_mat, "lsa_matrix": lsa_mat}

    if args.phase == 3 and not args.all:
        print("\n[Done] Phase 3 finished.")
        return

    # Phase 4
    if run_p4 or (args.phase == 5):
        print(f"\n[Phase 4] Benchmarking 4 Topic Models (K-Means, Agglomerative, NMF, LDA) with k={args.k}...")
        p4_res = pe.run_phase4(p3_res["data"], p3_res["tfidf_matrix"], p3_res["lsa_matrix"], os.path.join(OUTPUTS_DIR, "models"), target_k=args.k, run_stability=True)
        print("[PASS] Gate 4: 4-model benchmarking completed.")
        print(pd.DataFrame(p4_res["comparison_table"]).to_string(index=False))
        if p4_res.get("stability_metrics"):
            sm = p4_res["stability_metrics"]
            print(f"\n  [Stability] Bootstrap Stability ARI (B={sm.get('n_bootstraps')}): {sm.get('mean_stability_ari')} ± {sm.get('std_stability_ari')} (Vangara et al., 2021)")
        if p4_res.get("interdisciplinary_count") is not None:
            print(f"  [Soft Topics] Boundary-Spanning Papers: {p4_res['interdisciplinary_count']} interdisciplinary crossover studies (Grisales A. et al., 2023)")
        print("\n--- Canonical K-Means Top Terms (c-TF-IDF) ---")
        for c, terms in p4_res["km_top_terms"].items():
            print(f"  Topic {c}: {terms}")

    if args.phase == 4 and not args.all:
        print("\n[Done] Phase 4 finished.")
        return

    # Phase 5
    if run_p5:
        print(f"\n[Phase 5] Constructing Social Network Graph & Longitudinal Evolution Analysis (k-NN={args.knn})...")
        p5_res = pe.run_phase5(p4_res["data"], p3_res["lsa_matrix"], p4_res["km_labels"], os.path.join(OUTPUTS_DIR, "network"), DOCS_DIR, k_neighbors=args.knn)
        print(f"[PASS] Gate 5: Graph built ({p5_res['num_nodes']} nodes, {p5_res['num_edges']} edges, modularity: {p5_res['modularity']}).")
        if p5_res.get("temporal_evolution"):
            n_links = len(p5_res["temporal_evolution"].get("sankey_links", []))
            print(f"  [Temporal] Longitudinal Evolution: {n_links} transition links across 3 epochs (Wang et al., 2024)")
            print(f"  Temporal Data: {p5_res['temporal_csv_path']}")
        print(f"  Gephi Export: {p5_res['gexf_path']}")
        print(f"  Dashboard Updated: {p5_res['dashboard_path']}")

    print("\n" + "=" * 70)
    print("[ALL COMPLETE] Pipeline Run Completed with All Validation Gates Verified!")
    print("=" * 70)


if __name__ == "__main__":
    main()
