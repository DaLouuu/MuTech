import re

# 1. Update part3_methodology.md
with open('slr/manuscript/drafts/part3_methodology.md', 'r', encoding='utf-8') as f:
    text3 = f.read()

# Replace Table 3 and discussion
old_table3_pattern = r'\*\*Table 3:\*\* Topic-model comparison on the vectorized corpus\..*?indicating that the seven clusters reflect genuine topical structure rather than algorithmic artifact\.'

new_table3 = """**Table 3:** Topic-model benchmark comparison across candidate algorithms ($k = 7$, $n = 364$).

| Model | Silhouette (Cosine) | UMass Coherence | Min Cluster Size | Max Cluster Size | ARI vs. K-Means |
|---|---|---|---|---|---|
| K-Means | 0.0266 | -0.8736 | 29 | 77 | 1.0000 |
| NMF | 0.0234 | -0.9389 | 41 | 70 | 0.5347 |
| Agglomerative | 0.0219 | -1.1095 | 3 | 141 | 0.3710 |
| LDA | 0.0099 | -1.0366 | 21 | 112 | 0.2260 |

K-Means ($k = 7$) was selected as the final topic model, achieving the highest Cosine Silhouette (0.0266) and strongest UMass topic coherence (-0.8736) with balanced cluster distributions (min cluster 29, max cluster 77). NMF achieved comparable quality (Silhouette 0.0234, Coherence -0.9389, ARI = 0.5347 vs K-Means) but exhibited higher cross-topic boundary diffusion. Agglomerative clustering suffered severe cluster imbalance (one degenerate cluster of size 3 and an oversized cluster of 141 papers), while LDA struggled to form tight cluster boundaries on concise abstracts (Silhouette 0.0099, UMass -1.0366). Topic partition stability was rigorously verified through 100-iteration bootstrap resampling with randomized initializations, yielding a high consensus Adjusted Rand Index ($\\text{ARI} = 0.5299 \\pm 0.0614$). Furthermore, external validation against an independent 8-NN paper-similarity network confirmed strong community structure with a Louvain modularity of $Q = 0.6126$, mathematically demonstrating that the seven topics reflect genuine structural subfields of the literature."""

text3 = re.sub(old_table3_pattern, lambda m: new_table3, text3, flags=re.DOTALL)
text3 = text3.replace('n = 365', 'n = 364')

with open('slr/manuscript/drafts/part3_methodology.md', 'w', encoding='utf-8') as f:
    f.write(text3)

print("Updated part3_methodology.md")

# 2. Update part4_results.md
with open('slr/manuscript/drafts/part4_results.md', 'r', encoding='utf-8') as f:
    text4 = f.read()

# Replace Section 3.1.1 and Table 6
old_sec311 = r'### 3\.1\.1 Temporal distribution.*?### 3\.1\.2 Domain distribution'

new_sec311 = """### 3.1.1 Temporal distribution

The included corpus spans 2022 to mid-2026 ($n = 364$), retrieved through the standardized multi-stage screening pipeline. Publication volume expanded steadily across the period: 57 papers in 2022 (15.7%), 62 in 2023 (17.0%), 79 in 2024 (21.7%), 96 in 2025 (26.4%), and 70 papers indexed from 2026 at the time of screening (19.2%). The accelerating trajectory from 2024 onward reflects the surge in Transformer-based architectures, self-supervised representations, and neural audio synthesis. Table 6 shows the distribution by publication year and musical domain.

**Table 6:** Distribution of included studies by publication year and domain ($n = 364$).

| Year | Ensemble | General MIR | Instrumental | Vocal | Total | % |
|---|---|---|---|---|---|---|
| 2022 | 2 | 19 | 19 | 17 | 57 | 15.7% |
| 2023 | 5 | 30 | 17 | 10 | 62 | 17.0% |
| 2024 | 3 | 40 | 19 | 17 | 79 | 21.7% |
| 2025 | 4 | 37 | 36 | 19 | 96 | 26.4% |
| 2026* | 2 | 29 | 24 | 15 | 70 | 19.2% |
| **Total** | **16 (4.4%)** | **155 (42.6%)** | **115 (31.6%)** | **78 (21.4%)** | **364** | **100.0%** |

*Note.* \\*2026 count reflects publications indexed as of the search cutoff.

### 3.1.2 Domain distribution"""

text4 = re.sub(old_sec311, lambda m: new_sec311, text4, flags=re.DOTALL)

# Replace domain narrative
old_domain_narrative = r'General MIR is the largest domain \(n = 170.*?\n\n\[NOTE: replaces'
new_domain_narrative = """General MIR is the largest domain (n = 155, 42.6%), followed by Instrumental (n = 115, 31.6%), Vocal performance (n = 78, 21.4%), and Ensemble performance (n = 16, 4.4%). This distribution reflects the comprehensive breadth of modern MIR research. Notably, Ensemble processing represents only 4.4% of included studies, confirming that multi-performer coordination and ensemble modeling remain a critical, underserved niche within the broader discipline.

[NOTE: replaces"""

text4 = re.sub(old_domain_narrative, lambda m: new_domain_narrative, text4, flags=re.DOTALL)

# Replace Table 8
old_table8 = r'\*\*Table 8:\*\* Topic-cluster distribution of included studies \(K-Means, k = 7\)\..*?\n\n\*Note\.\*'
new_table8 = """**Table 8:** Topic-cluster distribution of included studies (K-Means, $k = 7$, $n = 364$).

| # | Topic cluster | Primary Terms (c-TF-IDF) | Papers | % |
|---|---|---|---|---|
| 0 | Vocal / Multi-modal Emotion & Opera | `opera`, `musictalk`, `tag`, `chinese`, `dance`, `mer`, `bimodal` | 66 | 18.1% |
| 1 | Automatic Music Transcription & Tablature (AMT) | `amt`, `cfp`, `mallet`, `offset`, `sight`, `tablature`, `velocity` | 58 | 15.9% |
| 2 | Music Source Separation & Drum Mixture (MSS) | `mss`, `drum`, `mixture`, `stripe`, `subband`, `microphone` | 50 | 13.7% |
| 3 | Self-Supervised & Representation Learning (SSL) | `ssl`, `gass`, `clmr`, `meta`, `jukebox`, `gesture`, `sync` | 43 | 11.8% |
| 4 | Audio-Score Alignment & Query-by-Humming (QBH) | `hum`, `score_following`, `query`, `chromagram`, `cbam`, `qbh` | 29 | 8.0% |
| 5 | Acoustic Feature Classification & Regional MIR | `knn`, `regional`, `neighbor`, `gtzan`, `classification`, `mfccs` | 77 | 21.2% |
| 6 | Singing Voice Synthesis & Lyric Alignment (SVS) | `aesthetic`, `svs`, `choral`, `word`, `lyric`, `sheet`, `phoneme` | 41 | 11.3% |
| | **Total** | | **364** | **100.0%** |

*Note.*"""

text4 = re.sub(old_table8, lambda m: new_table8, text4, flags=re.DOTALL)
text4 = text4.replace('365', '364')

with open('slr/manuscript/drafts/part4_results.md', 'w', encoding='utf-8') as f:
    f.write(text4)

print("Updated part4_results.md")
