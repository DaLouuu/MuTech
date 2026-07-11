"""
MuTech Project - Phase 5: SNA Synthesis & Visualization
========================================================
Systematic Literature Review on Intelligent Music Processing (MIR)

WHAT THIS DOES (per the masterfile Phase 5 checklist)
-------------------------------------------------------
1. Backend Math: builds a paper-similarity network (NetworkX) over the final 365-paper
   PRISMA-included corpus and analyzes how Phase 4's selected K-Means clusters relate to
   that network structure -- modularity of the K-Means partition, an independent Louvain
   community-detection cross-check, and an inter-cluster relationship matrix.
2. Rendering: exports the annotated network to Gephi (.gexf) for the team's own
   modularity/layout work and manuscript figures.

It also refreshes the SNA dashboard (docs/index.html), which previously ran on the
1,728-paper PRE-SCREENING pool (built before Phase 3/4 existed -- confirmed via git log
commit ordering) rather than the final 365-paper included corpus. This script rebuilds
every tab (keyword co-occurrence, publication trend, co-authorship, top keywords) on the
final corpus and adds a new "Topic Clusters" tab for the Phase 5 network above.

DATA SOURCES (joined on normalized title; see load_data())
------------------------------------------------------------
  phase1_2/rayyan/priority_records_from_rayyan.csv        - metadata (authors, keywords, year)
  phase3/phase3_output_real/cleaned_corpus.csv             - cleaned tokens (for TF-IDF)
  phase4/phase4_output_detailed/comparison/FINAL_SELECTED_assignments.csv  - K-Means cluster labels

NOTE ON MISSING VENUE DATA: `Publication Venue` is empty for all 365 papers in the source
export (checked directly, not a bug introduced here) -- the dashboard does not attempt a
venue breakdown. Author lists are also sparser than one might expect (most papers show as
effectively single-author in this export) -- the co-authorship tab reflects that honestly
rather than papering over it.

OUTPUTS
-------
  phase5_output/cluster_network.gexf          - paper-similarity graph, Gephi-ready
  phase5_output/cluster_relationship_matrix.csv - inter-cluster edge-count matrix
  phase5_output/network_summary.txt            - modularity, Louvain ARI, run settings
  docs/index.html                              - refreshed SNA dashboard (all 5 tabs)

HOW TO RUN
----------
  pip install -r requirements.txt
  python sna_synthesis.py
"""

from __future__ import annotations

import os
import re
from collections import Counter
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import NearestNeighbors

# ----------------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------------

RANDOM_STATE = 42
K_NEIGHBORS = 8          # cluster-network kNN degree per paper
MIN_COOCCURRENCE = 2     # keyword co-occurrence edge threshold (lower than the old
                          # 1,728-paper dashboard's threshold of 3, since this corpus is
                          # smaller -- the same absolute threshold would over-prune)
TOP_N_KEYWORDS = 80
TOP_N_AUTHORS = 60

# Same TF-IDF settings Phase 3/4 used throughout -- fully deterministic, so this refits
# from raw tokens rather than depending on any pickled vectorizer.
TFIDF_PARAMS = dict(max_features=2000, min_df=2, max_df=0.90, ngram_range=(1, 2), sublinear_tf=True)

# Hand-derived from Phase 4's final K-Means top-terms tables (same read used for the
# Phase 4 model-selection writeup).
CLUSTER_LABELS = {
    0: "Instrument Recognition / Classification",
    1: "Automatic Music Transcription (AMT)",
    2: "Singing Voice / Melody Extraction",
    3: "Source Separation",
    4: "Multi-Pitch Estimation",
    5: "Music Education & Performance Assessment",
    6: "Optical Music Recognition (OMR)",
}
CLUSTER_COLORS = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261", "#8ecae6", "#c77dff"]
COMMUNITY_PALETTE = [
    "#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261",
    "#a8dadc", "#8ecae6", "#06d6a0", "#ef476f", "#ffd166",
    "#118ab2", "#c77dff", "#48cae4", "#80b918", "#ff6b6b",
]

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS_DIR)
OUTDIR = os.path.join(THIS_DIR, "phase5_output")
DOCS_PATH = os.path.join(ROOT, "docs", "index.html")


# ----------------------------------------------------------------------------
# 1. LOAD + JOIN DATA
# ----------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    rayyan_path = os.path.join(ROOT, "phase1_2", "rayyan", "priority_records_from_rayyan.csv")
    corpus_path = os.path.join(ROOT, "phase3", "phase3_output_real", "cleaned_corpus.csv")
    assign_path = os.path.join(
        ROOT, "phase4", "phase4_output_detailed", "comparison", "FINAL_SELECTED_assignments.csv")

    for p in (rayyan_path, corpus_path, assign_path):
        if not os.path.exists(p):
            raise SystemExit(f"[ERROR] Missing input file: {p}")

    meta = pd.read_csv(rayyan_path, encoding="utf-8-sig")
    corpus = pd.read_csv(corpus_path, encoding="utf-8")
    assign = pd.read_csv(assign_path, encoding="utf-8")

    meta["title_key"] = meta["Title"].astype(str).str.strip().str.lower()
    corpus["title_key"] = corpus["title"].astype(str).str.strip().str.lower()
    assign["title_key"] = assign["title"].astype(str).str.strip().str.lower()

    df = assign[["title_key", "topic"]].rename(columns={"topic": "cluster"})
    df = df.merge(meta[["title_key", "Title", "Authors", "Year", "Keywords"]], on="title_key", how="left")
    df = df.merge(corpus[["title_key", "tokens"]], on="title_key", how="left")

    n_missing = df["cluster"].isna().sum() + df["Title"].isna().sum() + df["tokens"].isna().sum()
    if n_missing:
        raise SystemExit(f"[ERROR] {n_missing} papers failed to join across the three source files")
    if len(df) != 365:
        raise SystemExit(f"[ERROR] expected 365 papers after join, got {len(df)} (duplicate title match?)")

    df = df.reset_index(drop=True)
    df["cluster"] = df["cluster"].astype(int)
    df["cluster_label"] = df["cluster"].map(CLUSTER_LABELS)
    print(f"[load] joined {len(df)} papers across rayyan metadata + phase3 tokens + phase4 clusters")
    print(f"[load] cluster sizes: {dict(df['cluster'].value_counts().sort_index())}")
    return df


# ----------------------------------------------------------------------------
# 2. KEYWORD CO-OCCURRENCE NETWORK (rebuilt on the final 365-paper corpus)
# ----------------------------------------------------------------------------

def parse_keywords(kw_str) -> list[str]:
    if pd.isna(kw_str) or str(kw_str).strip() == "":
        return []
    kw_str = str(kw_str).replace(" | ", ";").replace("|", ";")
    return [k.strip().lower() for k in kw_str.split(";") if k.strip()]


def build_keyword_network(df: pd.DataFrame):
    kw_lists = df["Keywords"].apply(parse_keywords)
    all_kw = [k for kl in kw_lists for k in kl]
    kw_freq = Counter(all_kw)
    print(f"[keywords] records with keywords: {kw_lists.apply(bool).sum()}/{len(df)}, "
          f"total tokens: {len(all_kw)}, unique: {len(kw_freq)}")

    edge_counter = Counter()
    for kw_list in kw_lists:
        for pair in combinations(sorted(set(kw_list)), 2):
            edge_counter[pair] += 1

    G = nx.Graph()
    for (k1, k2), w in edge_counter.items():
        if w >= MIN_COOCCURRENCE:
            G.add_edge(k1, k2, weight=w)
    G.remove_nodes_from(list(nx.isolates(G)))
    if G.number_of_nodes() > TOP_N_KEYWORDS:
        top_nodes = {n for n, _ in sorted(G.degree(), key=lambda x: -x[1])[:TOP_N_KEYWORDS]}
        G = G.subgraph(top_nodes).copy()

    communities = list(nx.community.greedy_modularity_communities(G)) if G.number_of_nodes() else []
    node_community = {n: i for i, c in enumerate(communities) for n in c}
    print(f"[keywords] network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
          f"{len(communities)} communities")
    return G, kw_freq, communities, node_community


# ----------------------------------------------------------------------------
# 3. CO-AUTHORSHIP NETWORK (rebuilt on the final 365-paper corpus)
# ----------------------------------------------------------------------------

def parse_authors(author_str) -> list[str]:
    if pd.isna(author_str) or str(author_str).strip() == "":
        return []
    # This corpus's Authors field is sparser than the pre-screening pool's -- most rows
    # don't carry a full multi-author list. Split on both the ";" convention used
    # upstream and a written-out " and " between two authors to recover what's there.
    parts = re.split(r";|\band\b", str(author_str), flags=re.IGNORECASE)
    return [a.strip() for a in parts if a.strip()]


def build_coauthorship_network(df: pd.DataFrame):
    author_lists = df["Authors"].apply(parse_authors)
    n_multi = (author_lists.apply(len) >= 2).sum()
    print(f"[coauthorship] papers with 2+ parsed authors: {n_multi}/{len(df)}")

    edge_counter = Counter()
    for authors in author_lists:
        uniq = sorted(set(authors))
        if len(uniq) < 2:
            continue
        for pair in combinations(uniq, 2):
            edge_counter[pair] += 1

    G = nx.Graph()
    for (a1, a2), w in edge_counter.items():
        G.add_edge(a1, a2, weight=w)
    if G.number_of_nodes() > TOP_N_AUTHORS:
        top_authors = {n for n, _ in sorted(G.degree(), key=lambda x: -x[1])[:TOP_N_AUTHORS]}
        G = G.subgraph(top_authors).copy()
    G.remove_nodes_from(list(nx.isolates(G)))
    print(f"[coauthorship] network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# ----------------------------------------------------------------------------
# 4. PHASE 5 CORE: CLUSTER-RELATIONSHIP NETWORK
# ----------------------------------------------------------------------------

def build_cluster_network(df: pd.DataFrame, k: int = K_NEIGHBORS):
    """Nodes = papers, edges = k-NN cosine similarity in TF-IDF space (union-of-neighbors,
    not mutual -- keeps the graph connected enough for community detection given this
    corpus's already-low pairwise similarity, consistent with Phase 4's low silhouette)."""
    vectorizer = TfidfVectorizer(**TFIDF_PARAMS)
    X = vectorizer.fit_transform(df["tokens"].fillna("").astype(str))
    print(f"[cluster-network] TF-IDF: {X.shape[0]} papers x {X.shape[1]} terms")

    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine")  # +1 to drop self-match
    nn.fit(X)
    distances, indices = nn.kneighbors(X)

    G = nx.Graph()
    for i, row in df.iterrows():
        G.add_node(i, title=str(row["Title"]), year=int(row["Year"]) if pd.notna(row["Year"]) else 0,
                   cluster=int(row["cluster"]), cluster_label=str(row["cluster_label"]))

    for i in range(X.shape[0]):
        for rank in range(1, k + 1):
            j = int(indices[i, rank])
            sim = float(1 - distances[i, rank])
            if sim <= 0:
                continue
            if G.has_edge(i, j):
                G[i][j]["weight"] = max(G[i][j]["weight"], sim)
            else:
                G.add_edge(i, j, weight=sim)

    print(f"[cluster-network] graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def analyze_cluster_relationships(G: nx.Graph, df: pd.DataFrame) -> dict:
    n = len(df)
    cluster_of = {i: int(df.iloc[i]["cluster"]) for i in range(n)}
    cluster_ids = sorted(df["cluster"].unique())

    communities_kmeans = [{i for i in range(n) if cluster_of[i] == c} for c in cluster_ids]
    mod_kmeans = nx.algorithms.community.quality.modularity(G, communities_kmeans, weight="weight")

    communities_louvain = nx.community.louvain_communities(G, weight="weight", seed=RANDOM_STATE)
    mod_louvain = nx.algorithms.community.quality.modularity(G, communities_louvain, weight="weight")

    louvain_label = {node: ci for ci, comm in enumerate(communities_louvain) for node in comm}
    kmeans_arr = [cluster_of[i] for i in range(n)]
    louvain_arr = [louvain_label[i] for i in range(n)]
    ari = adjusted_rand_score(kmeans_arr, louvain_arr)

    mat = np.zeros((len(cluster_ids), len(cluster_ids)), dtype=int)
    for u, v in G.edges():
        cu, cv = cluster_of[u], cluster_of[v]
        mat[cu, cv] += 1
        if cu != cv:
            mat[cv, cu] += 1

    result = {
        "modularity_kmeans": mod_kmeans,
        "modularity_louvain": mod_louvain,
        "n_louvain_communities": len(communities_louvain),
        "ari_kmeans_vs_louvain": ari,
        "inter_cluster_matrix": mat,
        "cluster_ids": cluster_ids,
    }
    print(f"[cluster-network] modularity (K-Means partition): {mod_kmeans:.4f}")
    print(f"[cluster-network] modularity (Louvain, {len(communities_louvain)} communities): {mod_louvain:.4f}")
    print(f"[cluster-network] ARI K-Means vs Louvain: {ari:.4f}")
    return result


def export_gephi(G: nx.Graph, path: str) -> None:
    nx.write_gexf(G, path)
    # round-trip check -- confirms the file is valid and readable, not just written
    reloaded = nx.read_gexf(path)
    assert reloaded.number_of_nodes() == G.number_of_nodes(), "gexf round-trip node count mismatch"
    print(f"[gephi] wrote and verified {path} ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")


# ----------------------------------------------------------------------------
# 5. PLOTLY FIGURE BUILDERS
# ----------------------------------------------------------------------------

def plot_network(G: nx.Graph, node_color_map: dict, title: str, subtitle: str = "",
                  node_text_fn=None, seed: int = RANDOM_STATE, height: int = 680):
    pos = nx.spring_layout(G, k=1.2, seed=seed, weight="weight") if G.number_of_nodes() else {}

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                             line=dict(width=0.6, color="#666"), hoverinfo="none", opacity=0.35)

    node_x, node_y, node_text, node_colors, node_sizes = [], [], [], [], []
    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        deg = G.degree(n)
        node_sizes.append(deg * 5 + 8)
        node_colors.append(node_color_map.get(n, "#888888"))
        node_text.append(node_text_fn(n, G) if node_text_fn else str(n))

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers",
        marker=dict(size=node_sizes, color=node_colors, line=dict(width=0.5, color="white")),
        text=node_text, hoverinfo="text")

    fig = go.Figure(data=[edge_trace, node_trace])
    full_title = f"<b>{title}</b>" + (f"<br><sup>{subtitle}</sup>" if subtitle else "")
    fig.update_layout(
        title=dict(text=full_title, x=0.5, font=dict(color="white", size=15)),
        showlegend=False, height=height,
        paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def plot_trend(year_counts: pd.Series):
    fig = go.Figure(go.Bar(
        x=[str(y) for y in year_counts.index], y=year_counts.values,
        marker=dict(color="#457b9d", line=dict(color="white", width=0.3)),
        text=year_counts.values, textposition="outside", textfont=dict(color="white")))
    fig.update_layout(
        title=dict(text="<b>Papers Published per Year</b><br><sup>Final PRISMA-included corpus (365 papers)</sup>",
                    x=0.5, font=dict(color="white", size=15)),
        paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        xaxis=dict(color="white", title="Year", gridcolor="#333"),
        yaxis=dict(color="white", title="Papers", gridcolor="#333"),
        height=500)
    return fig


def plot_top_keywords(kw_freq: Counter, node_community: dict, top_n: int = 30):
    top = kw_freq.most_common(top_n)[::-1]
    labels = [k for k, _ in top]
    counts = [c for _, c in top]
    colors = [COMMUNITY_PALETTE[node_community.get(k, -1) % len(COMMUNITY_PALETTE)]
              if k in node_community else "#888888" for k in labels]
    fig = go.Figure(go.Bar(
        x=counts, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(color="white", width=0.3)),
        text=counts, textposition="outside", textfont=dict(color="white", size=9)))
    fig.update_layout(
        title=dict(text=f"<b>Top {top_n} Keywords by Frequency</b><br><sup>Colored by theme</sup>",
                    x=0.5, font=dict(color="white", size=15)),
        paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        xaxis=dict(color="white", title="Frequency", gridcolor="#333"),
        yaxis=dict(color="white", tickfont=dict(size=9)),
        height=700, margin=dict(l=220, r=60, t=80, b=60))
    return fig


def plot_cluster_heatmap(matrix: np.ndarray, cluster_ids: list[int]):
    labels = [f"{c}: {CLUSTER_LABELS.get(c, c)[:28]}" for c in cluster_ids]
    fig = go.Figure(go.Heatmap(
        z=matrix, x=labels, y=labels, colorscale="YlOrRd",
        text=matrix, texttemplate="%{text}", textfont=dict(size=10)))
    fig.update_layout(
        title=dict(text="<b>Inter-Cluster Relationship Matrix</b><br>"
                         "<sup>kNN-graph edge counts within/between K-Means clusters</sup>",
                    x=0.5, font=dict(color="white", size=15)),
        paper_bgcolor="#1a1a2e", plot_bgcolor="#1a1a2e",
        xaxis=dict(color="white", tickfont=dict(size=9)),
        yaxis=dict(color="white", tickfont=dict(size=9), autorange="reversed"),
        height=560, margin=dict(l=200, r=40, t=90, b=140))
    return fig


# ----------------------------------------------------------------------------
# 6. DASHBOARD ASSEMBLY
# ----------------------------------------------------------------------------

CSS = """
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f0f1a; color: white; font-family: 'Segoe UI', sans-serif; }
  header {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    padding: 30px 40px; border-bottom: 2px solid #457b9d;
  }
  header h1 { font-size: 1.4rem; color: #8ecae6; font-weight: 300; margin-bottom: 6px; }
  header h2 { font-size: 1.0rem; color: #aaa; font-weight: 300; }
  .stats {
    display: flex; gap: 20px; padding: 20px 40px;
    background: #13131f; border-bottom: 1px solid #2a2a4a; flex-wrap: wrap;
  }
  .stat {
    background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 8px;
    padding: 12px 22px; text-align: center;
  }
  .stat-num { font-size: 1.6rem; color: #8ecae6; font-weight: 700; }
  .stat-label { font-size: 0.75rem; color: #888; margin-top: 2px; }
  nav {
    background: #13131f; padding: 0 40px;
    display: flex; gap: 4px; border-bottom: 2px solid #2a2a4a; flex-wrap: wrap;
  }
  nav button {
    background: transparent; border: none; color: #888;
    padding: 14px 22px; cursor: pointer; font-size: 0.9rem;
    border-bottom: 3px solid transparent; transition: all 0.2s;
  }
  nav button:hover { color: #8ecae6; }
  nav button.active { color: #8ecae6; border-bottom-color: #457b9d; }
  .tab { display: none; padding: 30px 40px; }
  .tab.active { display: block; }
  .section-title {
    font-size: 0.85rem; color: #666; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 16px;
  }
  .legend-grid { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
  .legend-item {
    display: flex; align-items: center; gap: 8px;
    background: #1a1a2e; border: 1px solid #2a2a4a;
    border-radius: 20px; padding: 6px 14px; font-size: 0.82rem;
  }
  .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
  table { width: 100%; border-collapse: collapse; margin-top: 10px; }
  th { background: #1a1a2e; color: #8ecae6; padding: 10px 14px;
        text-align: left; font-size: 0.82rem; font-weight: 600; }
  td { padding: 8px 14px; font-size: 0.82rem; border-bottom: 1px solid #1a1a2e; color: #ccc; }
  tr:hover td { background: #1a1a2e; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
  @media (max-width: 900px) { .two-col { grid-template-columns: 1fr; } }
  footer { text-align: center; padding: 20px; color: #444; font-size: 0.75rem; }
"""

JS = """
function showTab(name, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}
"""


def legend_html(communities, get_label, palette=COMMUNITY_PALETTE, max_items=6):
    items = []
    for i in range(min(len(communities), max_items)):
        color = palette[i % len(palette)]
        label = get_label(communities[i], i)
        items.append(f'<div class="legend-item"><div class="legend-dot" style="background:{color}"></div>{label}</div>')
    return '<div class="legend-grid">' + "".join(items) + "</div>"


def build_dashboard(df, kw_G, kw_freq, kw_communities, kw_node_community,
                     auth_G, year_counts, cluster_G, cluster_stats) -> str:
    n_papers = len(df)
    n_authors = len({a for al in df["Authors"].apply(parse_authors) for a in al})
    year_min, year_max = int(df["Year"].min()), int(df["Year"].max())

    # --- figures ---
    kw_color_map = {n: COMMUNITY_PALETTE[kw_node_community.get(n, -1) % len(COMMUNITY_PALETTE)]
                    for n in kw_G.nodes()}
    fig_kw = plot_network(kw_G, kw_color_map, "Keyword Co-occurrence Network",
                           "Final 365-paper corpus, colored by theme",
                           node_text_fn=lambda n, G: f"{n}<br>connections: {G.degree(n)}")

    fig_trend = plot_trend(year_counts)

    auth_color_map = {n: "#e63946" for n in auth_G.nodes()}
    fig_auth = plot_network(auth_G, auth_color_map, "Co-authorship Network",
                             "Final 365-paper corpus (sparse -- most source records list a single author)",
                             node_text_fn=lambda n, G: f"{n}<br>collaborators: {G.degree(n)}", height=620)

    fig_topkw = plot_top_keywords(kw_freq, kw_node_community)

    cluster_color_map = {n: CLUSTER_COLORS[data["cluster"] % len(CLUSTER_COLORS)]
                          for n, data in cluster_G.nodes(data=True)}
    fig_clusters = plot_network(
        cluster_G, cluster_color_map, "Topic Cluster Network",
        f"K-Means clusters (k=7) over paper-similarity kNN graph -- modularity={cluster_stats['modularity_kmeans']:.3f}",
        node_text_fn=lambda n, G: f"{G.nodes[n]['title'][:70]}<br>{G.nodes[n]['cluster_label']}", height=680)

    fig_heatmap = plot_cluster_heatmap(cluster_stats["inter_cluster_matrix"], cluster_stats["cluster_ids"])

    def to_html(fig, first=False):
        return fig.to_html(full_html=False, include_plotlyjs=("cdn" if first else False),
                            config={"responsive": True})

    kw_legend = legend_html(
        kw_communities, lambda c, i: sorted(c, key=lambda n: kw_G.degree(n), reverse=True)[0]
        if c else f"Group {i+1}")
    cluster_legend = "".join(
        f'<div class="legend-item"><div class="legend-dot" style="background:{CLUSTER_COLORS[c % len(CLUSTER_COLORS)]}"></div>'
        f'{CLUSTER_LABELS.get(c, c)}</div>' for c in cluster_stats["cluster_ids"])
    cluster_legend = f'<div class="legend-grid">{cluster_legend}</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MuTech SLR — SNA Dashboard</title>
<style>{CSS}</style>
</head>
<body>
<header>
  <h1>MuTech SLR — Social Network Analysis Dashboard</h1>
  <h2>Intelligent Music Processing for Singing, Ensembles, and Instrumental Performance: A Systematic Literature Review</h2>
</header>
<div class="stats">
  <div class="stat"><div class="stat-num">{n_papers}</div><div class="stat-label">Included Papers (PRISMA final)</div></div>
  <div class="stat"><div class="stat-num">{kw_G.number_of_nodes()}</div><div class="stat-label">Keyword Nodes</div></div>
  <div class="stat"><div class="stat-num">{kw_G.number_of_edges()}</div><div class="stat-label">Co-occurrence Edges</div></div>
  <div class="stat"><div class="stat-num">7</div><div class="stat-label">Topic Clusters (K-Means)</div></div>
  <div class="stat"><div class="stat-num">{n_authors}</div><div class="stat-label">Authors</div></div>
  <div class="stat"><div class="stat-num">{year_min}–{year_max}</div><div class="stat-label">Year Range</div></div>
  <div class="stat"><div class="stat-num">{cluster_stats['modularity_kmeans']:.3f}</div><div class="stat-label">Cluster Network Modularity</div></div>
</div>
<nav>
  <button class="active" onclick="showTab('kw', this)">Keyword Network</button>
  <button onclick="showTab('trend', this)">Publication Trend</button>
  <button onclick="showTab('auth', this)">Co-authorship</button>
  <button onclick="showTab('keywords', this)">Top Keywords</button>
  <button onclick="showTab('clusters', this)">Topic Clusters</button>
</nav>

<div id="tab-kw" class="tab active">
  <p class="section-title">Keyword Co-occurrence Network — colored by theme</p>
  {kw_legend}
  <div style="height:680px; width:100%;">{to_html(fig_kw, first=True)}</div>
</div>

<div id="tab-trend" class="tab">
  <p class="section-title">Papers published per year across the final included corpus</p>
  <div style="height:500px; width:100%;">{to_html(fig_trend)}</div>
</div>

<div id="tab-auth" class="tab">
  <p class="section-title">Co-authorship network — final included corpus</p>
  <p style="color:#888; font-size:0.82rem; margin-bottom:14px;">
    Sparser than a typical bibliometric co-authorship map: most records in this export
    carry only one author name. This reflects the source metadata, not a processing error.
  </p>
  <div style="height:620px; width:100%;">{to_html(fig_auth)}</div>
</div>

<div id="tab-keywords" class="tab">
  <p class="section-title">Top 30 keywords by frequency, colored by theme</p>
  <div style="height:700px; width:100%;">{to_html(fig_topkw)}</div>
</div>

<div id="tab-clusters" class="tab">
  <p class="section-title">Phase 5 — Topic Cluster Relationship Network</p>
  {cluster_legend}
  <p style="color:#888; font-size:0.82rem; margin: 4px 0 18px;">
    Nodes = papers, edges = top-{K_NEIGHBORS} nearest neighbors by TF-IDF cosine similarity, colored by the
    Phase 4 K-Means cluster each paper was assigned to. Modularity of this K-Means partition on the
    network is <b>{cluster_stats['modularity_kmeans']:.4f}</b>; an independent Louvain community
    detection on the same network found <b>{cluster_stats['n_louvain_communities']}</b> communities with
    modularity <b>{cluster_stats['modularity_louvain']:.4f}</b> (Adjusted Rand Index vs. K-Means:
    <b>{cluster_stats['ari_kmeans_vs_louvain']:.4f}</b>). Full graph exported to
    <code>phase5/phase5_output/cluster_network.gexf</code> for Gephi.
  </p>
  <div class="two-col">
    <div style="height:680px; width:100%;">{to_html(fig_clusters)}</div>
    <div style="height:680px; width:100%;">{to_html(fig_heatmap)}</div>
  </div>
</div>

<footer>
  Generated by MuTech SLR Pipeline (Phase 5) &nbsp;|&nbsp; NetworkX + Plotly &nbsp;|&nbsp; {n_papers} included papers
</footer>
<script>{JS}</script>
</body>
</html>
"""
    return html


# ----------------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------------

def run() -> None:
    os.makedirs(OUTDIR, exist_ok=True)

    df = load_data()

    kw_G, kw_freq, kw_communities, kw_node_community = build_keyword_network(df)
    auth_G = build_coauthorship_network(df)
    year_counts = df["Year"].astype(str).str[:4].value_counts().sort_index()

    cluster_G = build_cluster_network(df)
    cluster_stats = analyze_cluster_relationships(cluster_G, df)

    export_gephi(cluster_G, os.path.join(OUTDIR, "cluster_network.gexf"))

    cluster_ids = cluster_stats["cluster_ids"]
    mat_df = pd.DataFrame(
        cluster_stats["inter_cluster_matrix"],
        index=[f"{c}:{CLUSTER_LABELS.get(c, c)}" for c in cluster_ids],
        columns=[f"{c}:{CLUSTER_LABELS.get(c, c)}" for c in cluster_ids])
    mat_df.to_csv(os.path.join(OUTDIR, "cluster_relationship_matrix.csv"))

    summary = "\n".join([
        "MuTech Phase 5 - SNA synthesis run summary",
        f"  papers                    : {len(df)}",
        f"  keyword network           : {kw_G.number_of_nodes()} nodes, {kw_G.number_of_edges()} edges, "
        f"{len(kw_communities)} communities",
        f"  co-authorship network     : {auth_G.number_of_nodes()} nodes, {auth_G.number_of_edges()} edges",
        f"  cluster network           : {cluster_G.number_of_nodes()} nodes, {cluster_G.number_of_edges()} edges "
        f"(k={K_NEIGHBORS} nearest neighbors, cosine similarity)",
        f"  modularity (K-Means)      : {cluster_stats['modularity_kmeans']:.4f}",
        f"  modularity (Louvain)      : {cluster_stats['modularity_louvain']:.4f} "
        f"({cluster_stats['n_louvain_communities']} communities)",
        f"  ARI K-Means vs Louvain    : {cluster_stats['ari_kmeans_vs_louvain']:.4f}",
        "",
        "Inter-cluster relationship matrix:",
        mat_df.to_string(),
    ])
    with open(os.path.join(OUTDIR, "network_summary.txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    print("\n" + summary)

    html = build_dashboard(df, kw_G, kw_freq, kw_communities, kw_node_community,
                            auth_G, year_counts, cluster_G, cluster_stats)
    with open(DOCS_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n[done] Dashboard written: {DOCS_PATH}")
    print(f"[done] Phase 5 outputs written to: {OUTDIR}")


if __name__ == "__main__":
    run()
