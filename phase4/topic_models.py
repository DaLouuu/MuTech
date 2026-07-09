"""
MuTech Project - Phase 4: Full Topic-Model Suite
=================================================
Systematic Literature Review on Intelligent Music Processing (MIR)

Runs ALL FOUR Phase 4 models on the Phase 3 TF-IDF output and compares them:

  1. K-Means          - hard clustering on TF-IDF (same as kmeans_clustering.py)
  2. Agglomerative    - hierarchical clustering, cosine distance, average linkage
  3. NMF              - matrix factorization on TF-IDF; doc's top component = topic
  4. LDA              - probabilistic topic model; needs raw term COUNTS, so a
                        CountVectorizer is rebuilt from cleaned_corpus.csv's
                        'tokens' column (same vocab settings as Phase 3 TF-IDF)

All models share the same k (chosen by K-Means silhouette, or forced with --k)
so their outputs are directly comparable.

COMPARISON METRICS
------------------
  silhouette (cosine) - cluster separation in TF-IDF space, higher = better
  ARI matrix          - Adjusted Rand Index between every pair of models
                        (1.0 = identical partitions, ~0 = unrelated)
  vs. _true_topic     - in --mock mode only: ARI against the seeded topics

HOW TO RUN
----------
  python topic_models.py --mock                    # synthetic data, today
  python topic_models.py --indir phase3_output     # real data, later
  python topic_models.py --indir phase3_output --k 6

OUTPUTS (in --outdir/models/, default ./phase4_output/models)
-------------------------------------------------------------
  <model>_assignments.csv - paper -> topic/cluster label, per model
  <model>_top_terms.csv   - top terms per topic, per model
  model_comparison.csv    - silhouette + ARI matrix
  models_2d.png           - same 2D projection, colored by each model
  models_summary.txt      - counts + settings for the run
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

# reuse the Phase 4 core: loader, mock generator, k selection
from kmeans_clustering import (K_RANGE, RANDOM_STATE, TOP_TERMS,
                               fit_kmeans, load_phase3, make_mock_phase3,
                               select_k)

# LDA's CountVectorizer mirrors Phase 3's TFIDF_PARAMS (minus tf-idf weighting)
COUNT_PARAMS = dict(max_features=2000, min_df=2, max_df=0.90, ngram_range=(1, 2))
LDA_MAX_ITER = 25
NMF_MAX_ITER = 400


# ----------------------------------------------------------------------------
# MODELS - each returns (labels, top_terms_dataframe)
# ----------------------------------------------------------------------------

def _terms_from_components(components, terms, n=TOP_TERMS) -> pd.DataFrame:
    rows = []
    for c, comp in enumerate(components):
        idx = np.argsort(comp)[::-1][:n]
        rows.append({"topic": c, "top_terms": ", ".join(terms[i] for i in idx)})
    return pd.DataFrame(rows)


def _terms_from_cluster_means(X, labels, terms, n=TOP_TERMS) -> pd.DataFrame:
    """Top terms = highest mean TF-IDF within each cluster (for models
    without centroids/components, e.g. Agglomerative)."""
    rows = []
    for c in sorted(set(labels)):
        mean_vec = np.asarray(X[labels == c].mean(axis=0)).ravel()
        idx = np.argsort(mean_vec)[::-1][:n]
        rows.append({"topic": c, "top_terms": ", ".join(terms[i] for i in idx)})
    return pd.DataFrame(rows)


def model_kmeans(X, corpus, terms, k):
    km, labels = fit_kmeans(X, k)
    return labels, _terms_from_components(km.cluster_centers_, terms)


def model_agglomerative(X, corpus, terms, k):
    from sklearn.cluster import AgglomerativeClustering
    dense = X.toarray()
    try:
        agg = AgglomerativeClustering(n_clusters=k, metric="cosine",
                                      linkage="average")
    except TypeError:  # scikit-learn < 1.2 uses 'affinity'
        agg = AgglomerativeClustering(n_clusters=k, affinity="cosine",
                                      linkage="average")
    labels = agg.fit_predict(dense)
    return labels, _terms_from_cluster_means(X, labels, terms)


def model_nmf(X, corpus, terms, k):
    from sklearn.decomposition import NMF
    nmf = NMF(n_components=k, init="nndsvda", random_state=RANDOM_STATE,
              max_iter=NMF_MAX_ITER)
    W = nmf.fit_transform(X)                 # docs x topics
    labels = W.argmax(axis=1)
    return labels, _terms_from_components(nmf.components_, terms)


def model_lda(X, corpus, terms, k):
    """LDA runs on raw term counts, NOT TF-IDF - rebuild from 'tokens'."""
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.feature_extraction.text import CountVectorizer

    if "tokens" not in corpus.columns:
        sys.exit("[ERROR] cleaned_corpus.csv has no 'tokens' column - "
                 "needed to rebuild counts for LDA.")
    cv = CountVectorizer(**COUNT_PARAMS)
    counts = cv.fit_transform(corpus["tokens"].fillna("").astype(str))
    lda = LatentDirichletAllocation(n_components=k, random_state=RANDOM_STATE,
                                    learning_method="batch",
                                    max_iter=LDA_MAX_ITER)
    doc_topic = lda.fit_transform(counts)    # docs x topics (proportions)
    labels = doc_topic.argmax(axis=1)
    return labels, _terms_from_components(lda.components_,
                                          cv.get_feature_names_out())


MODELS = {
    "kmeans": model_kmeans,
    "agglomerative": model_agglomerative,
    "nmf": model_nmf,
    "lda": model_lda,
}


# ----------------------------------------------------------------------------
# COMPARISON + PLOTS
# ----------------------------------------------------------------------------

def compare_models(X, all_labels: dict[str, np.ndarray],
                   corpus: pd.DataFrame) -> pd.DataFrame:
    from sklearn.metrics import adjusted_rand_score, silhouette_score

    names = list(all_labels)
    rows = []
    for name in names:
        lab = all_labels[name]
        sil = (silhouette_score(X, lab, metric="cosine")
               if len(set(lab)) > 1 else float("nan"))
        row = {"model": name, "silhouette_cosine": round(sil, 4)}
        for other in names:
            row[f"ari_vs_{other}"] = round(
                adjusted_rand_score(all_labels[other], lab), 4)
        if "_true_topic" in corpus.columns:   # mock-mode ground truth
            row["ari_vs_true_topic"] = round(
                adjusted_rand_score(corpus["_true_topic"], lab), 4)
        rows.append(row)
    return pd.DataFrame(rows)


def plot_models_2d(X, all_labels: dict[str, np.ndarray], path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.decomposition import TruncatedSVD

    xy = TruncatedSVD(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    for ax, (name, labels) in zip(axes.ravel(), all_labels.items()):
        ax.scatter(xy[:, 0], xy[:, 1], c=labels, cmap="tab10", s=22, alpha=0.8)
        ax.set_title(name)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("MuTech Phase 4 - same corpus, four models "
                 "(2D TruncatedSVD of TF-IDF)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------------

def run(indir: str, outdir: str, forced_k: int | None = None) -> None:
    models_dir = os.path.join(outdir, "models")
    os.makedirs(models_dir, exist_ok=True)

    X, corpus, terms = load_phase3(indir)

    if forced_k:
        k = forced_k
        print(f"[run] Using forced k={k}")
    else:
        _, k = select_k(X, K_RANGE)
        print(f"[run] Shared k for all models: {k}")

    all_labels: dict[str, np.ndarray] = {}
    for name, fn in MODELS.items():
        print(f"\n[{name}] fitting ...")
        labels, top_terms = fn(X, corpus, terms, k)
        all_labels[name] = labels

        asg = pd.DataFrame({
            "title": corpus.get("title", pd.Series([""] * len(corpus))),
            "year": corpus.get("year", pd.Series([""] * len(corpus))),
            "topic": labels,
        })
        if "_true_topic" in corpus.columns:
            asg["_true_topic"] = corpus["_true_topic"]
        asg.to_csv(os.path.join(models_dir, f"{name}_assignments.csv"),
                   index=False)
        top_terms.to_csv(os.path.join(models_dir, f"{name}_top_terms.csv"),
                         index=False)
        sizes = pd.Series(labels).value_counts().sort_index()
        print(f"[{name}] topic sizes: "
              f"{ {int(c): int(n) for c, n in sizes.items()} }")
        for _, r in top_terms.iterrows():
            print(f"    topic {r['topic']}: {r['top_terms'][:90]}")

    comparison = compare_models(X, all_labels, corpus)
    comparison.to_csv(os.path.join(models_dir, "model_comparison.csv"),
                      index=False)
    plot_models_2d(X, all_labels, os.path.join(models_dir, "models_2d.png"))

    summary = (
        "MuTech Phase 4 - full model suite run summary\n"
        f"  input dir   : {indir}\n"
        f"  papers      : {X.shape[0]}\n"
        f"  k (shared)  : {k}\n"
        f"  models      : {', '.join(MODELS)}\n\n"
        "Comparison:\n" + comparison.to_string(index=False) + "\n"
    )
    with open(os.path.join(models_dir, "models_summary.txt"), "w",
              encoding="utf-8") as f:
        f.write(summary)
    print("\n" + summary)
    print(f"[done] All outputs written to: {models_dir}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="MuTech Phase 4 - full topic-model suite "
                    "(K-Means, Agglomerative, NMF, LDA)")
    p.add_argument("--indir", "-i", default="phase3_output")
    p.add_argument("--outdir", "-o", default="phase4_output")
    p.add_argument("--k", type=int, default=None,
                   help="force a shared k (default: K-Means silhouette pick)")
    p.add_argument("--mock", action="store_true",
                   help="generate synthetic Phase 3-format test data first")
    p.add_argument("--mock-docs", type=int, default=100)
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    indir = args.indir
    if args.mock:
        indir = "mock_phase3_output"
        make_mock_phase3(indir, n_docs=args.mock_docs)
    run(indir, args.outdir, forced_k=args.k)
