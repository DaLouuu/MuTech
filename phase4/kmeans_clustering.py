"""
MuTech Project - Phase 4: ML Topic Clustering (K-Means)
========================================================
Systematic Literature Review on Intelligent Music Processing (MIR)

WHAT THIS DOES (per the masterfile Phase 4 checklist)
-----------------------------------------------------
1. Load Phase 3 outputs (tfidf_matrix.npz + tfidf_vectorizer.pkl +
   cleaned_corpus.csv) exactly as produced by text_mining.py.
2. Select k: sweep a range of k values, record inertia (elbow) and
   silhouette score, pick the best silhouette (overridable with --k).
3. Fit the final K-Means model and label every paper with its cluster.
4. Interpret clusters: top TF-IDF terms per cluster (from the centroids)
   and the most representative papers (closest to each centroid).
5. Visualize: k-selection curves + 2D TruncatedSVD scatter of the corpus
   colored by cluster.

Agglomerative / LDA / NMF are the next models in this phase; the pipeline is
structured so they slot in beside KMeans later (see fit_kmeans()). Note for
LDA: it needs raw term COUNTS, not TF-IDF - rebuild with CountVectorizer on
cleaned_corpus.csv's 'tokens' column when we get there.

MOCK MODE (so Phase 4 can start before Phase 3's final run)
-----------------------------------------------------------
    python kmeans_clustering.py --mock
generates a synthetic ~100-paper MIR corpus, writes it in EXACT Phase 3
output format to ./mock_phase3_output/, then clusters it. When Marian's
final dataset is ready and Phase 3 has been run on it:
    python kmeans_clustering.py --indir path/to/phase3_output
No other changes needed.

OUTPUTS (written to --outdir, default ./phase4_output)
------------------------------------------------------
  cluster_assignments.csv - one row per paper: title, year, cluster id,
                            distance to its centroid
  cluster_top_terms.csv   - top terms per cluster (the topic "labels")
  k_selection.csv         - inertia + silhouette for every k tried
  k_selection.png         - elbow + silhouette plots
  clusters_2d.png         - 2D SVD projection colored by cluster
  kmeans_model.pkl        - the fitted KMeans model (for phases 5/6)
  run_summary.txt         - counts + settings for the run

HOW TO RUN
----------
  pip install pandas numpy scipy scikit-learn matplotlib

  python kmeans_clustering.py --mock                     # test data, now
  python kmeans_clustering.py --indir phase3_output      # real data, later
  python kmeans_clustering.py --indir phase3_output --k 6   # force k
"""

from __future__ import annotations

import argparse
import os
import pickle
import random
import sys

import numpy as np
import pandas as pd
from scipy import sparse

# ----------------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------------

K_RANGE = range(2, 13)      # k values to try during selection
TOP_TERMS = 15              # top terms to report per cluster
TOP_PAPERS = 5              # representative papers to report per cluster
RANDOM_STATE = 42           # reproducibility
N_INIT = 20                 # KMeans restarts per k (higher = more stable)

# ----------------------------------------------------------------------------
# MOCK DATA - synthetic Phase 3 output so Phase 4 can be built/tested today.
# Five seeded "topics" that mirror what we expect in the real MIR corpus.
# ----------------------------------------------------------------------------

MOCK_TOPICS: dict[str, list[str]] = {
    "source_separation": [
        "source separation", "choir", "choral", "satb", "demixing", "unet",
        "time domain", "mask", "vocal part", "stem", "mixture", "sdr",
        "separation network", "waveform", "spectrogram",
    ],
    "pitch_intonation": [
        "pitch estimation", "intonation", "multi pitch", "f0", "vibrato",
        "tuning", "drift", "salience", "frequency", "contour", "quartet",
        "a cappella", "pitch tracking", "cent", "reference pitch",
    ],
    "singing_synthesis": [
        "singing synthesis", "voice synthesis", "vocoder", "unison",
        "generative", "diffusion", "autoregressive", "timbre", "expressive",
        "synthesizer", "waveform generation", "listening test", "naturalness",
    ],
    "datasets_benchmarks": [
        "dataset", "benchmark", "corpus", "annotation", "multitrack",
        "recording", "synthetic data", "augmentation", "evaluation set",
        "open data", "reproducibility", "baseline", "metadata",
    ],
    "transcription_alignment": [
        "transcription", "score alignment", "audio to score", "midi",
        "sheet music", "symbolic", "note event", "onset detection",
        "alignment", "music notation", "omr", "score following",
    ],
}

MOCK_SHARED = [
    "music information retrieval", "deep learning", "neural network",
    "ensemble singing", "audio", "acoustic", "signal", "polyphonic",
    "training", "evaluation", "feature", "performance",
]

MOCK_VENUES = ["ISMIR", "IEEE ICASSP", "TISMIR", "Applied Sciences",
               "IEEE/ACM TASLP", "DAFx", "EUSIPCO"]


def make_mock_phase3(outdir: str, n_docs: int = 100) -> None:
    """Write a synthetic corpus in EXACT Phase 3 output format."""
    rng = random.Random(RANDOM_STATE)
    topics = list(MOCK_TOPICS)
    rows = []
    for i in range(n_docs):
        topic = topics[i % len(topics)]
        vocab = MOCK_TOPICS[topic]
        # a pseudo "tokens" field: topic terms + shared MIR terms + noise
        toks = (rng.choices(vocab, k=rng.randint(25, 40))
                + rng.choices(MOCK_SHARED, k=rng.randint(8, 15))
                + rng.choices(sum(MOCK_TOPICS.values(), []), k=rng.randint(0, 6)))
        rng.shuffle(toks)
        tokens = " ".join(toks)
        rows.append({
            "title": f"Mock study {i + 1:03d}: {vocab[0]} for ensemble singing",
            "abstract": tokens,
            "keywords": "; ".join(rng.sample(vocab, 4)),
            "year": rng.randint(2020, 2026),
            "authors": f"Author {i + 1}",
            "doi": f"10.0000/mock.{i + 1:04d}",
            "source": rng.choice(MOCK_VENUES),
            "document_raw": tokens,
            "document_clean": tokens,
            "relevance_score": rng.randint(3, 10),
            "keep": True,
            "drop_reason": "",
            "tokens": tokens,
            "_true_topic": topic,   # ground truth, handy for sanity checks
        })
    df = pd.DataFrame(rows)

    from sklearn.feature_extraction.text import TfidfVectorizer
    # Same TFIDF_PARAMS as Phase 3's text_mining.py
    vec = TfidfVectorizer(max_features=2000, min_df=2, max_df=0.90,
                          ngram_range=(1, 2), sublinear_tf=True)
    matrix = vec.fit_transform(df["tokens"])

    os.makedirs(outdir, exist_ok=True)
    df.to_csv(os.path.join(outdir, "cleaned_corpus.csv"), index=False)
    sparse.save_npz(os.path.join(outdir, "tfidf_matrix.npz"), matrix)
    with open(os.path.join(outdir, "tfidf_features.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(vec.get_feature_names_out()))
    with open(os.path.join(outdir, "tfidf_vectorizer.pkl"), "wb") as f:
        pickle.dump(vec, f)
    with open(os.path.join(outdir, "run_summary.txt"), "w", encoding="utf-8") as f:
        f.write(f"MOCK Phase 3 output - {n_docs} synthetic docs, "
                f"{matrix.shape[1]} terms, 5 seeded topics\n")
    print(f"[mock] Wrote synthetic Phase 3 output ({n_docs} docs, "
          f"{matrix.shape[1]} terms) to: {outdir}")


# ----------------------------------------------------------------------------
# 1. LOAD PHASE 3 OUTPUT
# ----------------------------------------------------------------------------

def load_phase3(indir: str):
    """Load the three Phase 3 artifacts Phase 4 needs."""
    paths = {name: os.path.join(indir, name) for name in
             ("tfidf_matrix.npz", "tfidf_vectorizer.pkl", "cleaned_corpus.csv")}
    missing = [p for p in paths.values() if not os.path.exists(p)]
    if missing:
        sys.exit("[ERROR] Missing Phase 3 output file(s):\n  "
                 + "\n  ".join(missing)
                 + "\nRun text_mining.py first, or use --mock for test data.")

    X = sparse.load_npz(paths["tfidf_matrix.npz"])
    with open(paths["tfidf_vectorizer.pkl"], "rb") as f:
        vectorizer = pickle.load(f)
    corpus = pd.read_csv(paths["cleaned_corpus.csv"])
    terms = vectorizer.get_feature_names_out()

    if X.shape[0] != len(corpus):
        sys.exit(f"[ERROR] Matrix rows ({X.shape[0]}) != corpus rows "
                 f"({len(corpus)}) - mismatched Phase 3 run?")
    print(f"[load] {X.shape[0]} papers x {X.shape[1]} TF-IDF terms from {indir}")
    return X, corpus, terms


# ----------------------------------------------------------------------------
# 2. K SELECTION (elbow + silhouette)
# ----------------------------------------------------------------------------

def select_k(X, k_range=K_RANGE):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    records = []
    max_k = min(max(k_range), X.shape[0] - 1)
    for k in [k for k in k_range if k <= max_k]:
        km = KMeans(n_clusters=k, n_init=N_INIT, random_state=RANDOM_STATE)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels, metric="cosine")
        records.append({"k": k, "inertia": km.inertia_, "silhouette": sil})
        print(f"[select_k] k={k:2d}  inertia={km.inertia_:9.2f}  "
              f"silhouette={sil:.4f}")
    df = pd.DataFrame(records)
    best = int(df.loc[df["silhouette"].idxmax(), "k"])
    print(f"[select_k] Best k by silhouette: {best}")
    if df["silhouette"].max() < 0.15:
        print("[select_k] WARNING: silhouette is low/flat for every k - the "
              "clusters are weakly separated.\n"
              "           This is normal on real, messy corpora. Don't trust "
              "the automatic pick blindly:\n"
              "           re-run with --k for a few values (e.g. 4-8) and "
              "choose the one whose top terms\n"
              "           are most interpretable for the SLR.")
    return df, best


# ----------------------------------------------------------------------------
# 3. FINAL MODEL + INTERPRETATION
# ----------------------------------------------------------------------------

def fit_kmeans(X, k):
    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=k, n_init=N_INIT, random_state=RANDOM_STATE)
    labels = km.fit_predict(X)
    return km, labels


def top_terms_per_cluster(km, terms, n=TOP_TERMS) -> pd.DataFrame:
    rows = []
    for c, centroid in enumerate(km.cluster_centers_):
        idx = np.argsort(centroid)[::-1][:n]
        rows.append({"cluster": c,
                     "size": int((km.labels_ == c).sum()),
                     "top_terms": ", ".join(terms[i] for i in idx)})
    return pd.DataFrame(rows)


def assignments_table(X, km, labels, corpus) -> pd.DataFrame:
    from sklearn.metrics import pairwise_distances
    dists = pairwise_distances(X, km.cluster_centers_, metric="euclidean")
    dist_own = dists[np.arange(X.shape[0]), labels]
    out = pd.DataFrame({
        "title": corpus.get("title", pd.Series([""] * len(corpus))),
        "year": corpus.get("year", pd.Series([""] * len(corpus))),
        "source": corpus.get("source", pd.Series([""] * len(corpus))),
        "cluster": labels,
        "dist_to_centroid": np.round(dist_own, 4),
    })
    if "_true_topic" in corpus.columns:      # mock-mode sanity check
        out["_true_topic"] = corpus["_true_topic"]
    return out.sort_values(["cluster", "dist_to_centroid"]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# 4. PLOTS
# ----------------------------------------------------------------------------

def plot_k_selection(kdf: pd.DataFrame, best_k: int, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(kdf["k"], kdf["inertia"], "o-")
    axes[0].set(title="Elbow (inertia)", xlabel="k", ylabel="inertia")
    axes[1].plot(kdf["k"], kdf["silhouette"], "o-", color="tab:green")
    axes[1].axvline(best_k, ls="--", color="gray", label=f"best k = {best_k}")
    axes[1].set(title="Silhouette (cosine)", xlabel="k", ylabel="score")
    axes[1].legend()
    fig.suptitle("MuTech Phase 4 - K-Means k selection")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_clusters_2d(X, labels, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.decomposition import TruncatedSVD

    xy = TruncatedSVD(n_components=2, random_state=RANDOM_STATE).fit_transform(X)
    fig, ax = plt.subplots(figsize=(7, 6))
    sc = ax.scatter(xy[:, 0], xy[:, 1], c=labels, cmap="tab10", s=28, alpha=0.8)
    ax.set(title="MuTech Phase 4 - papers in 2D (TruncatedSVD of TF-IDF)",
           xlabel="SVD-1", ylabel="SVD-2")
    ax.legend(*sc.legend_elements(), title="cluster", loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------------

def run(indir: str, outdir: str, forced_k: int | None = None) -> None:
    os.makedirs(outdir, exist_ok=True)

    X, corpus, terms = load_phase3(indir)

    kdf, best_k = select_k(X)
    k = forced_k or best_k
    if forced_k:
        print(f"[run] Using forced k={k} (best silhouette was {best_k})")

    km, labels = fit_kmeans(X, k)
    tt = top_terms_per_cluster(km, terms)
    asg = assignments_table(X, km, labels, corpus)

    # representative papers per cluster (closest to centroid)
    print("\n=== Clusters ===")
    for _, row in tt.iterrows():
        c = row["cluster"]
        print(f"\nCluster {c} ({row['size']} papers): {row['top_terms']}")
        for t in asg[asg["cluster"] == c]["title"].head(TOP_PAPERS):
            print(f"    - {t}")

    # ---- save everything ----
    asg.to_csv(os.path.join(outdir, "cluster_assignments.csv"), index=False)
    tt.to_csv(os.path.join(outdir, "cluster_top_terms.csv"), index=False)
    kdf.to_csv(os.path.join(outdir, "k_selection.csv"), index=False)
    plot_k_selection(kdf, best_k, os.path.join(outdir, "k_selection.png"))
    plot_clusters_2d(X, labels, os.path.join(outdir, "clusters_2d.png"))
    with open(os.path.join(outdir, "kmeans_model.pkl"), "wb") as f:
        pickle.dump(km, f)

    summary = (
        "MuTech Phase 4 - K-Means clustering run summary\n"
        f"  input dir         : {indir}\n"
        f"  papers            : {X.shape[0]}\n"
        f"  tf-idf terms      : {X.shape[1]}\n"
        f"  k tried           : {list(kdf['k'])}\n"
        f"  best k (silhouette): {best_k}\n"
        f"  k used            : {k}\n"
        f"  silhouette at k   : "
        f"{kdf.loc[kdf['k'] == k, 'silhouette'].iloc[0]:.4f}\n"
        f"  cluster sizes     : "
        f"{ {int(c): int(n) for c, n in pd.Series(labels).value_counts().sort_index().items()} }\n"
    )
    with open(os.path.join(outdir, "run_summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    print("\n" + summary)
    print(f"[done] All outputs written to: {outdir}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="MuTech Phase 4 - K-Means topic clustering")
    p.add_argument("--indir", "-i", default="phase3_output",
                   help="Phase 3 output directory (default: phase3_output)")
    p.add_argument("--outdir", "-o", default="phase4_output",
                   help="output directory (default: phase4_output)")
    p.add_argument("--k", type=int, default=None,
                   help="force a specific k (default: best silhouette)")
    p.add_argument("--mock", action="store_true",
                   help="generate synthetic Phase 3-format test data first "
                        "and cluster that (for building ahead of Phase 3)")
    p.add_argument("--mock-docs", type=int, default=100,
                   help="number of synthetic papers in --mock mode")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    indir = args.indir
    if args.mock:
        indir = "mock_phase3_output"
        make_mock_phase3(indir, n_docs=args.mock_docs)
    run(indir, args.outdir, forced_k=args.k)
