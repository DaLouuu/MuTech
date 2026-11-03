import os
import sys
import pandas as pd
import numpy as np

# Ensure root, slr, and slr/src are in sys.path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("slr"))
sys.path.insert(0, os.path.abspath("slr/src"))

from slr.src import pipeline_engine as pe

# 1. Load Gemini results and normalized records
results_path = "slr/notebooks/test/mir_screening_outputs/gemini_all_results.csv"
papers_path = "slr/notebooks/test/mir_screening_outputs/records_normalized.csv"

df_results = pd.read_csv(results_path)
df_papers = pd.read_csv(papers_path)

df_results["record_id"] = df_results["record_id"].astype(str)
df_papers["record_id"] = df_papers["record_id"].astype(str)

# Filter for the 364 eligible RETRIEVE_FULL_TEXT papers
eligible = df_results[df_results["decision"] == "RETRIEVE_FULL_TEXT"].copy()
merged = eligible.merge(
    df_papers[["record_id", "title", "abstract", "year", "authors", "venue", "doi"]],
    on="record_id",
    how="inner",
)

corpus_std = pd.DataFrame({
    "record_id": merged["record_id"],
    "Title": merged["title"].fillna("").astype(str).str.strip(),
    "Abstract": merged["abstract"].fillna("").astype(str).str.strip(),
    "Year": pd.to_numeric(merged["year"], errors="coerce").fillna(2024).astype(int),
    "Authors": merged["authors"].fillna("").astype(str),
    "Publication Venue": merged["venue"].fillna("").astype(str),
    "DOI": merged["doi"].fillna("").astype(str),
    "Keywords": "",
    "Source Database": "Scopus/IEEE",
    "domain_gemini": merged["domain"],
})

print(f"======================================================================")
print(f"MuTech SLR: Processing Canonical Gemini Corpus ({len(corpus_std)} Studies)")
print(f"======================================================================")

# Save canonical Phase 2 output
out_prisma = "slr/outputs/prisma"
os.makedirs(out_prisma, exist_ok=True)
p2_file = os.path.join(out_prisma, "phase2_screened_corpus.csv")
corpus_std.to_csv(p2_file, index=False)
print(f"[Phase 2] Exported screened corpus: {p2_file} ({len(corpus_std)} records)")

# Run Phase 3
out_rep = "slr/outputs/representations"
print(f"\n[Phase 3] Running NLP Text Mining & 35-D LSA Representation...")
p3_res = pe.run_phase3(corpus_std, out_rep)
print(f"  [PASS] Gate 3: Docs={p3_res['num_docs']}, Vocab={p3_res['vocab_size']}, PMI collocations={p3_res['pmi_collocations_count']}")

# Run Phase 4
out_models = "slr/outputs/models"
print(f"\n[Phase 4] Benchmarking 4 Topic Models (K-Means, Agglomerative, NMF, LDA) with k=7...")
p4_res = pe.run_phase4(p3_res["data"], p3_res["tfidf_matrix"], p3_res["lsa_matrix"], out_models, target_k=7)
print(f"  [Gate 4 Status]: {p4_res['gate_passed']}")
print(f"  [Topic Stability]: Mean ARI = {p4_res['stability_metrics']['mean_stability_ari']} ± {p4_res['stability_metrics']['std_stability_ari']}")
print(f"  [Soft Topics]: {p4_res['interdisciplinary_count']} interdisciplinary crossover studies")
print("\n--- Canonical K-Means Top Terms (c-TF-IDF) ---")
for t_idx, terms in p4_res["km_top_terms"].items():
    print(f"  Topic {t_idx}: {terms}")

# Run Phase 5
out_net = "slr/outputs/network"
docs_dir = "docs"
print(f"\n[Phase 5] Running 8-NN Similarity Graph & Temporal Topic Evolution...")
p5_res = pe.run_phase5(p4_res["data"], p3_res["lsa_matrix"], p4_res["km_labels"], out_net, docs_dir)
print(f"  [PASS] Gate 5: Nodes={p5_res['num_nodes']}, Edges={p5_res['num_edges']}, Modularity={p5_res['modularity']}")
print(f"  [Temporal Evolution]: {len(p5_res['temporal_evolution']['sankey_links'])} alluvial transition links")

print(f"\n======================================================================")
print(f"[DONE] Phases 3 to 5 fully processed, generated, and saved to slr/outputs/")
print(f"======================================================================")

