import pandas as pd
import numpy as np
import re

# Load outputs
df = pd.read_csv('slr/outputs/models/phase4_clustered_corpus.csv')
comp = pd.read_csv('slr/outputs/models/phase4_model_comparison.csv')
net_evol = pd.read_csv('slr/outputs/network/phase5_temporal_topic_evolution.csv')

out = []
out.append('==============================================================================')
out.append('MUTECH SLR — CANONICAL NUMBERS MANIFEST v4 (364 STUDIES)')
out.append('==============================================================================\n')
out.append('Corpus screened via Gemini-validated preliminary screening.')
out.append('Total candidates: 547 | Included: 364 | Excluded: 75 | Deferred (API limit): 108\n')

out.append('1. YEAR DISTRIBUTION')
out.append('------------------------------------------------------------------------------')
yc = df['Year'].value_counts().sort_index()
for y, c in yc.items():
    out.append(f'  {y}: {c:3d} ({c/len(df)*100:5.1f}%)')
out.append(f'  Total: {len(df)}\n')

out.append('2. DOMAIN DISTRIBUTION (Gemini Standardized)')
out.append('------------------------------------------------------------------------------')
dc = df['domain_gemini'].value_counts()
for d, c in dc.items():
    out.append(f'  {d:<15}: {c:3d} ({c/len(df)*100:5.1f}%)')
out.append(f'  Total: {len(df)}\n')

out.append('3. TOPIC CLUSTER DISTRIBUTION (K-Means k=7)')
out.append('------------------------------------------------------------------------------')
names = {
    0: 'Vocal / Multi-modal Emotion & Opera',
    1: 'Automatic Music Transcription & Tablature (AMT)',
    2: 'Music Source Separation & Drum Mixture (MSS)',
    3: 'Self-Supervised & Representation Learning (SSL)',
    4: 'Audio-Score Alignment & Query-by-Humming (QBH)',
    5: 'Acoustic Feature Classification & Regional MIR',
    6: 'Singing Voice Synthesis & Lyric Alignment (SVS)'
}
tc = df['topic_kmeans'].value_counts().sort_index()
for t, c in tc.items():
    out.append(f'  Topic {t} ({names[t]}): {c:3d} ({c/len(df)*100:5.1f}%)')
out.append(f'  Total: {len(df)}\n')

out.append('4. TOPIC x DOMAIN CROSSTAB')
out.append('------------------------------------------------------------------------------')
xt_dom = pd.crosstab(df['topic_kmeans'], df['domain_gemini'], margins=True)
out.append(xt_dom.to_string())
out.append('\n')

out.append('5. TOPIC x YEAR CROSSTAB')
out.append('------------------------------------------------------------------------------')
xt_yr = pd.crosstab(df['topic_kmeans'], df['Year'], margins=True)
out.append(xt_yr.to_string())
out.append('\n')

out.append('6. MODEL BENCHMARK COMPARISON')
out.append('------------------------------------------------------------------------------')
out.append(comp.to_string(index=False))
crossover_count = int(df['is_interdisciplinary'].sum())
crossover_pct = float(df['is_interdisciplinary'].mean() * 100)
out.append(f'\nTopic Stability: Mean ARI = 0.5299 +- 0.0614 (100 bootstrap iterations)')
out.append(f'Interdisciplinary / Crossover Studies: {crossover_count} ({crossover_pct:.1f}%)\n')

out.append('7. NETWORK TOPOLOGY')
out.append('------------------------------------------------------------------------------')
out.append('Nodes: 364 | Edges: 1873 (8-NN Cosine Similarity Graph)')
out.append('Louvain Modularity Q: 0.6126')
out.append('Temporal Alluvial Transitions (2 Epochs: 2022-2023 vs 2024-2026):')
for _, row in net_evol.iterrows():
    out.append(f'  {row["source"]} -> {row["target"]}: {row["value"]} papers')
out.append('\n')

def search_terms(text, terms):
    if not isinstance(text, str):
        return False
    for t in terms:
        if re.search(r'\b' + re.escape(t) + r'\b', text, re.IGNORECASE):
            return True
    return False

archs = {
    'CNN / Convolutional': ['cnn', 'convolutional', 'convnet', 'resnet', 'u-net', 'unet'],
    'Transformer / Attention': ['transformer', 'attention', 'conformer', 'bert', 'cross-attention'],
    'RNN / LSTM / GRU': ['rnn', 'lstm', 'gru', 'recurrent'],
    'Self-Supervised / Pretrained / Foundation': ['self-supervised', 'ssl', 'contrastive', 'clmr', 'jukebox', 'foundation model', 'pretrained', 'pre-trained'],
    'Diffusion / Generative': ['diffusion', 'ddpm', 'gan', 'generative adversarial', 'vae', 'variational autoencoder'],
    'Classical ML / DSP': ['svm', 'support vector', 'random forest', 'knn', 'nearest neighbor', 'decision tree', 'nmf', 'matrix factorization', 'hmm']
}

out.append('8. ARCHITECTURAL PREVALENCE & TEMPORAL SHIFT')
out.append('------------------------------------------------------------------------------')
for name, terms in archs.items():
    cnt = df['doc_raw'].apply(lambda x: search_terms(x, terms)).sum()
    pct = cnt / len(df) * 100
    early = df[df['Year'] <= 2023]['doc_raw'].apply(lambda x: search_terms(x, terms)).sum() / len(df[df['Year'] <= 2023]) * 100
    late = df[df['Year'] >= 2024]['doc_raw'].apply(lambda x: search_terms(x, terms)).sum() / len(df[df['Year'] >= 2024]) * 100
    out.append(f'  {name:<42}: {cnt:3d} ({pct:5.1f}%) | 2022-2023: {early:5.1f}% -> 2024-2026: {late:5.1f}%')
out.append('\n')

challenges = {
    'Generalization / Robustness / Domain Shift': ['generalization', 'robustness', 'domain shift', 'real-world', 'unseen', 'in-the-wild', 'out-of-domain'],
    'Data Scarcity / Annotation Bottleneck': ['scarcity', 'scarce', 'few-shot', 'zero-shot', 'unlabeled', 'data-hungry', 'annotation', 'annotated dataset', 'lack of data'],
    'Noise / Polyphony / Mixture Complexity': ['noise', 'noisy', 'reverberation', 'polyphonic', 'polyphony', 'interference', 'crosstalk', 'bleeding'],
    'Real-time / Latency / Embedded Deployment': ['real-time', 'low latency', 'latency', 'edge', 'embedded', 'mobile', 'on-device', 'computationally efficient', 'lightweight'],
    'Subjective Evaluation / Listening Tests': ['listening test', 'subjective evaluation', 'mos', 'mean opinion score', 'mushra', 'perceptual evaluation', 'human evaluation']
}

out.append('9. REPORTED CHALLENGES & PRACTICES')
out.append('------------------------------------------------------------------------------')
for name, terms in challenges.items():
    cnt = df['doc_raw'].apply(lambda x: search_terms(x, terms)).sum()
    pct = cnt / len(df) * 100
    early = df[df['Year'] <= 2023]['doc_raw'].apply(lambda x: search_terms(x, terms)).sum() / len(df[df['Year'] <= 2023]) * 100
    late = df[df['Year'] >= 2024]['doc_raw'].apply(lambda x: search_terms(x, terms)).sum() / len(df[df['Year'] >= 2024]) * 100
    out.append(f'  {name:<42}: {cnt:3d} ({pct:5.1f}%) | 2022-2023: {early:5.1f}% -> 2024-2026: {late:5.1f}%')

manifest_content = '\n'.join(out)
with open('slr/manuscript/tables/numbers_manifest_v4_canonical.txt', 'w', encoding='utf-8') as f:
    f.write(manifest_content)

print('Generated slr/manuscript/tables/numbers_manifest_v4_canonical.txt successfully!')

