"""
MuTech SLR - Pipeline Core Engine (Phases 1 to 5)
Provides clean, reusable execution functions with automated validation gates.
Used by CLI, Web UI server, and Jupyter Notebooks.
"""

from __future__ import annotations

# Standard Library Imports
import importlib
import json
import math
import os
import pickle
import random
import re
import subprocess
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# Third-Party Scientific & NLP Imports
import networkx as nx
import numpy as np
import pandas as pd
import scipy.sparse as sp
from bs4 import BeautifulSoup
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import LatentDirichletAllocation, NMF, TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

# Optional NLP & Deep Learning Imports (Graceful degradation without static analysis warnings)
try:
    import spacy  # type: ignore
except ImportError:
    spacy = None

torch = None
AutoModel = None
AutoTokenizer = None

try:
    torch = importlib.import_module("torch")
    _transformers = importlib.import_module("transformers")
    AutoModel = getattr(_transformers, "AutoModel", None)
    AutoTokenizer = getattr(_transformers, "AutoTokenizer", None)
except (ImportError, ModuleNotFoundError):
    pass

RANDOM_STATE = 42

PHRASE_COLLOCATIONS = [
    ("music information retrieval", "music_information_retrieval"),
    ("automatic music transcription", "automatic_music_transcription"),
    ("music transcription", "music_transcription"),
    ("source separation", "source_separation"),
    ("singing voice separation", "singing_voice_separation"),
    ("singing voice", "singing_voice"),
    ("multi pitch estimation", "multi_pitch_estimation"),
    ("multipitch estimation", "multi_pitch_estimation"),
    ("pitch estimation", "pitch_estimation"),
    ("pitch tracking", "pitch_tracking"),
    ("optical music recognition", "optical_music_recognition"),
    ("score following", "score_following"),
    ("fundamental frequency", "f0_estimation"),
]

def mine_pmi_collocations(texts: List[str], min_count: int = 3, min_npmi: float = 0.50, max_collocations: int = 30) -> List[Tuple[str, str]]:
    """
    Automated statistical Pointwise Mutual Information (PMI / NPMI) collocation mining.
    Reference: Truică & Apostol (2021), IEEE Access (doi:10.1109/ACCESS.2021.3083000).
    Extracts high-association multi-word domain collocations without subjective manual lists.
    """
    all_words = []
    bigrams = []
    for t in texts:
        w = re.findall(r"\b[a-z]{3,}\b", t.lower())
        all_words.extend(w)
        for i in range(len(w) - 1):
            w1, w2 = w[i], w[i+1]
            if w1 not in EXTRA_STOPWORDS and w2 not in EXTRA_STOPWORDS:
                bigrams.append((w1, w2))

    n_words = len(all_words)
    n_bigrams = len(bigrams)
    if n_bigrams == 0 or n_words == 0:
        return []

    word_freq = Counter(all_words)
    bigram_freq = Counter(bigrams)

    pmi_scores = []
    for (w1, w2), count in bigram_freq.items():
        if count >= min_count:
            p_w1 = word_freq[w1] / n_words
            p_w2 = word_freq[w2] / n_words
            p_w1_w2 = count / n_bigrams
            pmi = math.log2(p_w1_w2 / (p_w1 * p_w2))
            npmi = pmi / (-math.log2(p_w1_w2))
            if npmi >= min_npmi:
                phrase = f"{w1} {w2}"
                bound = f"{w1}_{w2}"
                pmi_scores.append(((phrase, bound), count, npmi))

    pmi_scores.sort(key=lambda x: (x[2], x[1]), reverse=True)
    return [item[0] for item in pmi_scores[:max_collocations]]

def extract_dense_embeddings(corpus_texts: List[str], X_tfidf: sp.spmatrix, method: str = "lsa", n_components: int = 35) -> np.ndarray:
    """
    Extracts dense semantic representations.
    Supports:
      - 'lsa': TruncatedSVD dimensionality reduction + L2 normalization (Fast, zero-GPU requirement).
      - 'scibert': AllenAI SciBERT transformer embedding (if transformers and torch are installed).
    References:
      - Al-Hawawreh & Sitnikova (2024), IEEE Access (doi:10.1109/ACCESS.2024.3375836)
      - Chen & Liu (2025), IEEE AINIT (doi:10.1109/AINIT65432.2025.11034992)
    """
    if method == "scibert" and torch is not None and AutoTokenizer is not None and AutoModel is not None:
        try:
            tokenizer = AutoTokenizer.from_pretrained("allenai/scibert_scivocab_uncased")
            model = AutoModel.from_pretrained("allenai/scibert_scivocab_uncased")
            model.eval()
            embeddings = []
            with torch.no_grad():
                for txt in corpus_texts:
                    inputs = tokenizer(txt[:512], return_tensors="pt", truncation=True, padding=True)
                    outputs = model(**inputs)
                    cls_vec = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
                    embeddings.append(cls_vec)
            return normalize(np.array(embeddings), norm="l2")
        except Exception:
            pass

    svd = TruncatedSVD(n_components=n_components, random_state=RANDOM_STATE)
    return normalize(svd.fit_transform(X_tfidf), norm="l2")

EXTRA_STOPWORDS = {
    "study", "paper", "result", "method", "approach", "propose", "proposed",
    "based", "use", "used", "using", "show", "shows", "shown", "present",
    "presented", "research", "article", "model", "models", "system", "systems",
    "music", "musical", "audio", "sound", "performance", "performances",
    "technique", "techniques", "algorithm", "algorithms", "task", "tasks",
    "experiment", "experiments", "evaluation", "dataset", "datasets"
}

EXCLUDE_TERMS = [
    "speech recognition", "speaker recognition", "speaker verification", "speech synthesis",
    "text-to-speech", "tts", "automatic speech recognition", "voice conversion", "speech enhancement",
    "speech separation", "parkinson", "alzheimer", "dysphonia", "pathology", "clinical", "medical",
    "healthcare", "diagnosis", "disease", "patient", "biomarker", "hospital", "hearing aid",
    "cochlear implant", "audiology", "hearing loss", "recommender system", "playlist generation",
    "collaborative filtering", "music marketing", "licensing", "streaming platform", "emotion perception"
]

PRIORITY_TERMS = [
    "music information retrieval", "mir", "music classification", "genre classification",
    "music transcription", "automatic music transcription", "source separation", "singing voice",
    "singing", "choral", "choir", "ensemble", "instrumental", "pitch estimation", "pitch detection",
    "score following", "optical music recognition", "omr", "f0", "timbre", "vibrato", "intonation"
]

# -----------------------------------------------------------------------------
# PHASE 1: Ingestion & Deduplication
# -----------------------------------------------------------------------------
def run_phase1(raw_dir: str, out_dir: str) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    scopus_path = os.path.join(raw_dir, "Scopus_Filtered.csv")
    ieee_files = [f for f in os.listdir(raw_dir) if f.startswith("IEEE_export") and f.endswith(".csv")]
    ieee_path = os.path.join(raw_dir, ieee_files[0]) if ieee_files else None

    if not os.path.exists(scopus_path):
        raise FileNotFoundError(f"Missing Scopus file at: {scopus_path}")
    
    df_scopus = pd.read_csv(scopus_path, encoding="utf-8-sig", on_bad_lines="skip")
    df_ieee = pd.read_csv(ieee_path, encoding="utf-8-sig", on_bad_lines="skip") if ieee_path else pd.DataFrame()

    scopus_std = pd.DataFrame({
        "Title": df_scopus["Title"].fillna("").astype(str).str.strip(),
        "Abstract": df_scopus["Abstract"].fillna("").astype(str).str.strip(),
        "Authors": df_scopus["Authors"].fillna("").astype(str).str.strip(),
        "Year": pd.to_numeric(df_scopus["Year"], errors="coerce"),
        "DOI": df_scopus["DOI"].fillna("").astype(str).str.strip(),
        "Keywords": df_scopus["Keywords"].fillna("").astype(str).str.strip(),
        "Publication Venue": None,
        "Source Database": "Scopus"
    })

    ieee_std = pd.DataFrame()
    if not df_ieee.empty:
        kw_cols = [c for c in ["Author Keywords", "IEEE Terms", "Mesh_Terms"] if c in df_ieee.columns]
        ieee_std = pd.DataFrame({
            "Title": df_ieee["Document Title"].fillna("").astype(str).str.strip(),
            "Abstract": df_ieee["Abstract"].fillna("").astype(str).str.strip(),
            "Authors": df_ieee["Authors"].fillna("").astype(str).str.strip(),
            "Year": pd.to_numeric(df_ieee["Publication Year"], errors="coerce"),
            "DOI": df_ieee["DOI"].fillna("").astype(str).str.strip(),
            "Keywords": df_ieee[kw_cols].fillna("").astype(str).agg("; ".join, axis=1).str.strip("; ") if kw_cols else "",
            "Publication Venue": df_ieee["Publication Title"].fillna("").astype(str).str.strip(),
            "Source Database": "IEEE"
        })

    merged = pd.concat([scopus_std, ieee_std], ignore_index=True)
    merged["record_id"] = range(1, len(merged) + 1)
    merged["Title_norm"] = merged["Title"].str.lower().str.strip().str.replace(r"[^\w\s]", "", regex=True)

    total_identified = len(merged)

    # DOI Deduplication
    has_doi = merged["DOI"].str.strip() != ""
    doi_unique = merged[has_doi].drop_duplicates(subset=["DOI"], keep="first")
    no_doi = merged[~has_doi]
    after_doi = pd.concat([doi_unique, no_doi], ignore_index=True)
    doi_dups = total_identified - len(after_doi)

    # Title Deduplication
    deduped = after_doi.drop_duplicates(subset=["Title_norm"], keep="first").reset_index(drop=True)
    title_dups = len(after_doi) - len(deduped)
    total_dups = doi_dups + title_dups

    out_file = os.path.join(out_dir, "phase1_merged_deduplicated.csv")
    deduped.to_csv(out_file, index=False, encoding="utf-8-sig")

    gate1_passed = (total_identified > 0) and (len(deduped) == total_identified - total_dups)

    return {
        "gate_passed": gate1_passed,
        "scopus_count": len(df_scopus),
        "ieee_count": len(df_ieee),
        "total_identified": total_identified,
        "doi_duplicates": doi_dups,
        "title_duplicates": title_dups,
        "total_duplicates": total_dups,
        "unique_records": len(deduped),
        "output_path": out_file,
        "data": deduped
    }

# -----------------------------------------------------------------------------
# PHASE 2: PRISMA Screening & Rayyan Handshake
# -----------------------------------------------------------------------------
def run_phase2(deduped_df: pd.DataFrame, raw_dir: str, rayyan_dir: str, out_dir: str, use_rayyan: bool = True) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    deduped_df = deduped_df.copy()
    deduped_df["search_text"] = (
        deduped_df["Title"].fillna("") + " " +
        deduped_df["Abstract"].fillna("") + " " +
        deduped_df["Keywords"].fillna("")
    ).str.lower()

    def has_term(txt, terms):
        return any(t in txt for t in terms)

    deduped_df["Priority_Flag"] = deduped_df["search_text"].apply(lambda x: has_term(x, PRIORITY_TERMS))
    deduped_df["Exclude_Flag"] = deduped_df["search_text"].apply(lambda x: has_term(x, EXCLUDE_TERMS))

    priority_candidates = deduped_df[deduped_df["Priority_Flag"] & (~deduped_df["Exclude_Flag"])].copy()
    rule_excluded = deduped_df[deduped_df["Exclude_Flag"]].copy()

    # Benchmark Seed Check
    official_path = os.path.join(raw_dir, "CITE4D_Official_Papers.csv")
    seed_matches = 0
    if os.path.exists(official_path):
        df_official = pd.read_csv(official_path)
        df_official["Title_norm"] = df_official["TOPIC"].fillna("").str.lower().str.strip().str.replace(r"[^\w\s]", "", regex=True)
        matches = deduped_df.merge(df_official[["Title_norm"]], on="Title_norm", how="inner")
        seed_matches = len(matches)

    rayyan_path = os.path.join(rayyan_dir, "priority_records_from_rayyan.csv")
    if use_rayyan and os.path.exists(rayyan_path):
        corpus_final = pd.read_csv(rayyan_path, encoding="utf-8-sig")
        mode = "Rayyan Screened (Human Validated)"
    else:
        corpus_final = priority_candidates.copy()
        mode = "Rule-based Priority Filter"

    out_file = os.path.join(out_dir, "phase2_screened_corpus.csv")
    corpus_final.to_csv(out_file, index=False, encoding="utf-8-sig")

    gate2_passed = len(corpus_final) > 0
    return {
        "gate_passed": gate2_passed,
        "mode": mode,
        "screened_count": len(corpus_final),
        "rule_priority_count": len(priority_candidates),
        "rule_excluded_count": len(rule_excluded),
        "benchmark_matches": seed_matches,
        "output_path": out_file,
        "data": corpus_final
    }

# -----------------------------------------------------------------------------
# PHASE 3: NLP Text Mining & Representation
# -----------------------------------------------------------------------------
def clean_and_bind_text(text: str, extra_collocations: Optional[List[Tuple[str, str]]] = None) -> str:
    if not isinstance(text, str):
        return ""
    if "<" in text:
        try:
            text = BeautifulSoup(text, "lxml").get_text(separator=" ")
        except Exception:
            text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+|\S+@\S+", " ", text)
    
    all_collocations = list(PHRASE_COLLOCATIONS)
    if extra_collocations:
        all_collocations.extend(extra_collocations)
        
    for phrase, replacement in all_collocations:
        text = re.sub(r"\b" + re.escape(phrase) + r"\b", replacement, text)
    text = re.sub(r"[^a-z_\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def tokenize_texts(texts: List[str]) -> List[str]:
    """Tokenize texts using spaCy if installed, or high-performance regex fallback."""
    if spacy is not None:
        try:
            try:
                nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
            except OSError:
                subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
                nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])

            for w in EXTRA_STOPWORDS:
                nlp.vocab[w].is_stop = True

            tokens_list = []
            for doc in nlp.pipe(texts, batch_size=64):
                toks = []
                for tok in doc:
                    if tok.is_stop or tok.is_punct or tok.is_space:
                        continue
                    lemma = tok.lemma_.lower().strip()
                    if len(lemma) < 3 or lemma in EXTRA_STOPWORDS:
                        continue
                    if tok.pos_ in {"NOUN", "PROPN", "ADJ", "VERB"}:
                        toks.append(lemma)
                tokens_list.append(" ".join(toks))
            return tokens_list
        except Exception:
            pass

    # High-performance regex fallback
    all_stops = set(ENGLISH_STOP_WORDS).union(EXTRA_STOPWORDS)
    tokens_list = []
    for text in texts:
        words = re.findall(r"\b[a-z_]{3,}\b", text.lower())
        filtered = [w for w in words if w not in all_stops]
        tokens_list.append(" ".join(filtered))
    return tokens_list

def run_phase3(corpus_df: pd.DataFrame, out_dir: str, use_pmi: bool = True, dense_method: str = "lsa") -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    corpus = corpus_df.copy()

    discovered_pmi = []
    if "tokens" not in corpus.columns or corpus["tokens"].isna().all():
        corpus["doc_raw"] = (
            corpus["Title"].fillna("") + " " +
            corpus["Abstract"].fillna("") + " " +
            corpus["Keywords"].fillna("")
        )
        
        # 1. Automated PMI Collocation Mining (Truică & Apostol, 2021)
        if use_pmi:
            discovered_pmi = mine_pmi_collocations(corpus["doc_raw"].tolist(), min_count=3, min_npmi=0.50)
            if discovered_pmi:
                pmi_df = pd.DataFrame(discovered_pmi, columns=["phrase", "bound_token"])
                pmi_df.to_csv(os.path.join(out_dir, "phase3_pmi_collocations.csv"), index=False)

        corpus["doc_clean"] = corpus["doc_raw"].apply(lambda t: clean_and_bind_text(t, extra_collocations=discovered_pmi))
        corpus["tokens"] = tokenize_texts(corpus["doc_clean"].tolist())
    else:
        corpus["tokens"] = corpus["tokens"].fillna("").astype(str)

    corpus = corpus[corpus["tokens"].str.strip() != ""].reset_index(drop=True)

    # TF-IDF
    TFIDF_PARAMS = dict(max_features=2000, min_df=2, max_df=0.85, ngram_range=(1, 2), sublinear_tf=True)
    vec = TfidfVectorizer(**TFIDF_PARAMS)
    X_tfidf = vec.fit_transform(corpus["tokens"])

    # Dense Semantic Embeddings (LSA or SciBERT)
    X_dense = extract_dense_embeddings(corpus["tokens"].tolist(), X_tfidf, method=dense_method, n_components=35)

    corpus_path = os.path.join(out_dir, "phase3_cleaned_corpus.csv")
    tfidf_path = os.path.join(out_dir, "phase3_tfidf_matrix.npz")
    corpus.to_csv(corpus_path, index=False)
    sp.save_npz(tfidf_path, X_tfidf)

    gate3_passed = (X_tfidf.shape[0] == len(corpus)) and (X_tfidf.shape[1] >= 500)

    return {
        "gate_passed": gate3_passed,
        "num_docs": len(corpus),
        "vocab_size": X_tfidf.shape[1],
        "lsa_dimensions": X_dense.shape[1],
        "pmi_collocations_count": len(discovered_pmi),
        "corpus_path": corpus_path,
        "tfidf_path": tfidf_path,
        "data": corpus,
        "tfidf_matrix": X_tfidf,
        "lsa_matrix": X_dense,
        "vectorizer": vec
    }

# -----------------------------------------------------------------------------
# PHASE 4: 4-Model Suite & c-TF-IDF Evaluation
# -----------------------------------------------------------------------------
def compute_c_tfidf(token_series: pd.Series, labels: np.ndarray, top_n: int = 12) -> Dict[int, str]:
    df_c = pd.DataFrame({"tokens": token_series.fillna(""), "cluster": labels})
    classes = sorted(df_c["cluster"].unique())
    pooled_docs = [df_c[df_c["cluster"] == c]["tokens"].str.cat(sep=" ").strip() for c in classes]
    # Guard against completely empty pooled text
    pooled_docs = [doc if len(doc) > 0 else "music audio" for doc in pooled_docs]
    vec = TfidfVectorizer(max_features=2000, sublinear_tf=True)
    c_matrix = vec.fit_transform(pooled_docs)
    vocab = np.array(vec.get_feature_names_out())
    out = {}
    for c_idx, c in enumerate(classes):
        row = c_matrix.getrow(c_idx).toarray().ravel()
        idx = np.argsort(row)[::-1][:top_n]
        out[c] = ", ".join(vocab[idx])
    return out

def calculate_umass(labels: np.ndarray, X_sparse: sp.spmatrix, top_n: int = 10) -> float:
    dense_counts = (X_sparse > 0).astype(int)
    doc_freq = np.array(dense_counts.sum(axis=0)).ravel()
    cooc = (dense_counts.T @ dense_counts).tocsr()
    classes = sorted(set(labels))
    coherences = []
    for c in classes:
        c_docs = np.where(labels == c)[0]
        if len(c_docs) == 0:
            continue
        c_sub = dense_counts[c_docs]
        top_words = np.argsort(np.array(c_sub.sum(axis=0)).ravel())[::-1][:top_n]
        coherence_c = 0.0
        pairs = 0
        for m in range(1, len(top_words)):
            for l in range(0, m):
                w_m, w_l = top_words[m], top_words[l]
                d_ml = cooc[w_m, w_l]
                d_l = doc_freq[w_l]
                coherence_c += np.log((d_ml + 1.0) / (d_l + 1.0))
                pairs += 1
        coherences.append(coherence_c / max(1, pairs))
    return float(np.mean(coherences)) if coherences else 0.0

def compute_topic_stability(X_dense: np.ndarray, target_k: int = 7, n_bootstraps: int = 10) -> Dict[str, Any]:
    """
    Topic stability bootstrapping via consensus Adjusted Rand Index (ARI).
    Reference: Vangara et al. (2021), IEEE Access (doi:10.1109/ACCESS.2021.3106879).
    Quantifies cluster robustness and safeguards against stochastic initialization artifacts.
    """
    base_km = KMeans(n_clusters=target_k, n_init=10, random_state=RANDOM_STATE)
    base_labels = base_km.fit_predict(X_dense)
    
    ari_scores = []
    for seed in range(n_bootstraps):
        km_boot = KMeans(n_clusters=target_k, n_init=5, random_state=RANDOM_STATE + 100 + seed)
        boot_labels = km_boot.fit_predict(X_dense)
        ari = float(adjusted_rand_score(base_labels, boot_labels))
        ari_scores.append(ari)

    mean_ari = float(np.mean(ari_scores))
    std_ari = float(np.std(ari_scores))
    return {
        "mean_stability_ari": round(mean_ari, 4),
        "std_stability_ari": round(std_ari, 4),
        "n_bootstraps": n_bootstraps,
        "is_stable": bool(mean_ari >= 0.45)
    }

def run_phase4(corpus_df: pd.DataFrame, X_tfidf: sp.spmatrix, X_lsa: np.ndarray, out_dir: str, target_k: int = 7, run_stability: bool = True) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    corpus = corpus_df.copy()

    # 1. K-Means
    km = KMeans(n_clusters=target_k, n_init=25, random_state=RANDOM_STATE)
    km_labels = km.fit_predict(X_lsa)

    # 2. Agglomerative (Hierarchical clustering on 35-D LSA representation to mitigate distance concentration)
    agg = AgglomerativeClustering(n_clusters=target_k, metric="cosine", linkage="average")
    agg_labels = agg.fit_predict(X_lsa)

    # 3. NMF
    nmf = NMF(n_components=target_k, init="nndsvda", random_state=RANDOM_STATE, max_iter=500)
    W_nmf = nmf.fit_transform(X_tfidf)
    nmf_labels = W_nmf.argmax(axis=1)

    # 4. LDA
    cv = CountVectorizer(max_features=2000, min_df=2, max_df=0.85, ngram_range=(1, 2))
    counts = cv.fit_transform(corpus["tokens"])
    lda = LatentDirichletAllocation(n_components=target_k, random_state=RANDOM_STATE, max_iter=50, learning_method="batch")
    W_lda = lda.fit_transform(counts)
    lda_labels = W_lda.argmax(axis=1)

    models_dict = {
        "K-Means": km_labels,
        "Agglomerative": agg_labels,
        "NMF": nmf_labels,
        "LDA": lda_labels
    }

    comparison_rows = []
    for name, labs in models_dict.items():
        sil = float(silhouette_score(X_tfidf, labs, metric="cosine"))
        umass = calculate_umass(labs, X_tfidf)
        counts_s = pd.Series(labs).value_counts()
        comparison_rows.append({
            "Model": name,
            "Silhouette (Cosine)": round(sil, 4),
            "UMass Coherence": round(umass, 4),
            "Min Cluster Size": int(counts_s.min()),
            "Max Cluster Size": int(counts_s.max()),
            "ARI vs K-Means": round(float(adjusted_rand_score(km_labels, labs)), 4)
        })

    comp_df = pd.DataFrame(comparison_rows)
    km_terms = compute_c_tfidf(corpus["tokens"], km_labels, top_n=10)

    # Soft Multi-Topic Membership Assignment (Grisales A. et al., 2023; Song & Johnson, 2023)
    soft_records = []
    for i in range(len(corpus)):
        theta = W_lda[i]
        sorted_idx = np.argsort(theta)[::-1]
        top1 = int(sorted_idx[0])
        top1_p = float(theta[top1])
        top2 = int(sorted_idx[1])
        top2_p = float(theta[top2])
        eps = 1e-12
        entropy = float(-np.sum(theta * np.log2(theta + eps)))
        is_interdisc = bool(top2_p >= 0.20 or entropy > 1.8)

        soft_records.append({
            "record_id": corpus.iloc[i].get("record_id", i + 1),
            "Title": corpus.iloc[i].get("Title", f"Paper {i}"),
            "Year": corpus.iloc[i].get("Year", 2026),
            "km_primary_topic": int(km_labels[i]),
            "lda_primary_topic": top1,
            "lda_primary_prob": round(top1_p, 4),
            "lda_secondary_topic": top2,
            "lda_secondary_prob": round(top2_p, 4),
            "lda_entropy": round(entropy, 4),
            "is_interdisciplinary": is_interdisc
        })

    df_soft = pd.DataFrame(soft_records)
    soft_path = os.path.join(out_dir, "phase4_soft_topic_distributions.csv")
    df_soft.to_csv(soft_path, index=False)

    corpus["topic_kmeans"] = km_labels
    corpus["topic_nmf"] = nmf_labels
    corpus["topic_lda"] = lda_labels
    corpus["topic_agglomerative"] = agg_labels
    corpus["lda_primary_topic"] = df_soft["lda_primary_topic"]
    corpus["lda_primary_prob"] = df_soft["lda_primary_prob"]
    corpus["lda_secondary_topic"] = df_soft["lda_secondary_topic"]
    corpus["lda_secondary_prob"] = df_soft["lda_secondary_prob"]
    corpus["lda_entropy"] = df_soft["lda_entropy"]
    corpus["is_interdisciplinary"] = df_soft["is_interdisciplinary"]

    comp_path = os.path.join(out_dir, "phase4_model_comparison.csv")
    clustered_path = os.path.join(out_dir, "phase4_clustered_corpus.csv")
    comp_df.to_csv(comp_path, index=False)
    corpus.to_csv(clustered_path, index=False)

    stability_info = {}
    if run_stability:
        stability_info = compute_topic_stability(X_lsa, target_k=target_k, n_bootstraps=10)

    gate4_passed = all(row["Min Cluster Size"] >= 5 for row in comparison_rows) and len(comparison_rows) == 4

    return {
        "gate_passed": gate4_passed,
        "target_k": target_k,
        "comparison_table": comp_df.to_dict(orient="records"),
        "km_top_terms": km_terms,
        "comp_path": comp_path,
        "clustered_path": clustered_path,
        "soft_path": soft_path,
        "interdisciplinary_count": int(df_soft["is_interdisciplinary"].sum()),
        "stability_metrics": stability_info,
        "data": corpus,
        "km_labels": km_labels
    }

# -----------------------------------------------------------------------------
# PHASE 5: Social Network Analysis & Temporal Evolution
# -----------------------------------------------------------------------------
def compute_temporal_topic_evolution(corpus_df: pd.DataFrame, target_topic_col: str = "topic_kmeans", time_bins: Optional[List[Tuple[str, int, int]]] = None) -> Dict[str, Any]:
    """
    Longitudinal temporal topic evolution tracking across chronological publication epochs.
    Reference: Wang, Chen, Chen, & Chen (2024), Scientometrics (doi:10.1007/s11192-023-04776-5).
    Tracks topic emergence, expansion, and shift over time for alluvial / Sankey flow modeling.
    """
    df = corpus_df.copy()
    if "Year" not in df.columns:
        return {"error": "Missing Year column"}

    if time_bins is None:
        time_bins = [
            ("Foundational (2020-2021)", 2020, 2021),
            ("Consolidation (2022-2023)", 2022, 2023),
            ("Modern/Expansion (2024-2026)", 2024, 2026)
        ]

    epoch_labels = []
    for yr in df["Year"].fillna(2026).astype(int):
        matched = False
        for label, y_start, y_end in time_bins:
            if y_start <= yr <= y_end:
                epoch_labels.append(label)
                matched = True
                break
        if not matched:
            epoch_labels.append(time_bins[-1][0])
    df["epoch"] = epoch_labels

    pivot_counts = df.groupby(["epoch", target_topic_col]).size().unstack(fill_value=0)
    pivot_pcts = pivot_counts.div(pivot_counts.sum(axis=1), axis=0).round(4)

    sankey_links = []
    for epoch, row in pivot_counts.iterrows():
        for topic_idx, count in row.items():
            if count > 0:
                sankey_links.append({
                    "source": str(epoch),
                    "target": f"Topic {topic_idx}",
                    "value": int(count)
                })

    return {
        "epochs": [b[0] for b in time_bins],
        "topic_counts_by_epoch": pivot_counts.to_dict(orient="index"),
        "topic_shares_by_epoch": pivot_pcts.to_dict(orient="index"),
        "sankey_links": sankey_links
    }

def run_phase5(corpus_df: pd.DataFrame, X_lsa: np.ndarray, km_labels: np.ndarray, out_dir: str, docs_dir: str, k_neighbors: int = 8) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    nn = NearestNeighbors(n_neighbors=k_neighbors + 1, metric="cosine")
    nn.fit(X_lsa)
    distances, indices = nn.kneighbors(X_lsa)

    G = nx.Graph()
    for idx, row in corpus_df.iterrows():
        G.add_node(
            idx,
            label=str(row.get("Title", f"Paper {idx}"))[:80],
            year=int(row["Year"]) if pd.notnull(row.get("Year")) else 2026,
            cluster=int(km_labels[idx]),
            authors=str(row.get("Authors", "Unknown"))
        )

    for i in range(len(corpus_df)):
        for j_idx in range(1, k_neighbors + 1):
            neighbor = indices[i, j_idx]
            sim = float(1.0 - distances[i, j_idx])
            if sim > 0.05:
                G.add_edge(i, neighbor, weight=sim)

    communities = nx.community.louvain_communities(G, seed=RANDOM_STATE)
    modularity_val = float(nx.community.modularity(G, communities))

    gexf_path = os.path.join(out_dir, "phase5_cluster_network.gexf")
    nx.write_gexf(G, gexf_path)

    # Longitudinal Topic Evolution (Wang et al., 2024)
    temporal_data = compute_temporal_topic_evolution(corpus_df, target_topic_col="topic_kmeans")
    temporal_json_path = os.path.join(out_dir, "phase5_temporal_topic_evolution.json")
    temporal_csv_path = os.path.join(out_dir, "phase5_temporal_topic_evolution.csv")
    
    with open(temporal_json_path, "w", encoding="utf-8") as f:
        json.dump(temporal_data, f, indent=2)
        
    pd.DataFrame(temporal_data["sankey_links"]).to_csv(temporal_csv_path, index=False)

    dashboard_path = os.path.join(docs_dir, "index.html")
    dashboard_synced = os.path.exists(dashboard_path)

    gate5_passed = (G.number_of_nodes() == len(corpus_df)) and (G.number_of_edges() > 0)

    return {
        "gate_passed": gate5_passed,
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "num_communities": len(communities),
        "modularity": round(modularity_val, 4),
        "gexf_path": gexf_path,
        "temporal_evolution": temporal_data,
        "temporal_csv_path": temporal_csv_path,
        "temporal_json_path": temporal_json_path,
        "dashboard_path": dashboard_path,
        "dashboard_synced": dashboard_synced
    }

