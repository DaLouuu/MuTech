#!/usr/bin/env python3
"""
MuTech Phase 6 — corrected-artifact rebuild.

Corpus is FROZEN at the 365 papers Rayyan included. This script does not re-screen and
does not change corpus membership. It repairs everything downstream of screening that can
be repaired without a re-pull, and it labels honestly what cannot.

What it fixes
-------------
1. Provenance     `Source Database` was overwritten to "Rayyan" for all 365 rows by the
                  Rayyan round trip. Recovered by joining back to merged_deduplicated.csv.
2. Venue          `Publication Venue` is null for all 365. The IEEE rows had a real venue
                  before the round trip; recovered from the same join. Scopus venues were
                  never pulled from the API and stay null (documented, not faked).
3. Domain tags    "General MIR" was the tagger's no-match default with zero evidence in
                  170/365 rows. Renamed to "Unclassified" and marked with an explicit
                  `domain_rule` column. Matching is now word-boundary, not substring.
4. Ensemble axis  "Ensemble" was operationalised as vocal ensemble only, sending 9
                  orchestral papers to "Instrumental". A separate orthogonal
                  `ensemble_scope` axis now records vocal / instrumental / not-indicated
                  multi-performer context without disturbing the domain axis.
5. Modality tags  "Audio" was likewise a no-match default (259 rows, zero evidence).
                  Positive audio indicators are now tested, splitting it into evidenced
                  Audio and genuinely Unspecified.
6. Quality        `q_alignment` is near-constant (345/365 score 5) and inflates every
                  total. A `quality_total_excl_alignment` column is added alongside the
                  original. Score bins are made non-overlapping.
7. Growth         2020-2022 (3 yrs) vs 2023-2026 (4 yrs, partial) was compared as a raw
                  ratio. Per-year and share-normalised rates are computed alongside it.

Outputs land in phase6_manuscript/corrected/. Nothing existing is overwritten.

Deterministic: no randomness, no network. Re-runnable.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
OUT = HERE / "corrected"
OUT.mkdir(exist_ok=True)

CLEANED = REPO / "phase3" / "phase3_output_real" / "cleaned_corpus.csv"
ASSIGN = REPO / "phase4" / "phase4_output_detailed" / "comparison" / "FINAL_SELECTED_assignments.csv"
RAYYAN = REPO / "phase1_2" / "rayyan" / "priority_records_from_rayyan.csv"
MERGED = REPO / "phase1_2" / "output" / "merged_deduplicated.csv"
OLDTAGS = HERE / "domain_modality_tags.csv"
QUALITY = HERE / "quality_scores.csv"

CLUSTER_LABELS = {
    0: "Instrument Recognition / Classification",
    1: "Automatic Music Transcription (AMT)",
    2: "Singing Voice / Melody Extraction",
    3: "Source Separation",
    4: "Multi-Pitch Estimation",
    5: "Music Education & Performance Assessment",
    6: "Optical Music Recognition (OMR)",
}


# --------------------------------------------------------------------------------------
# matching
# --------------------------------------------------------------------------------------

def norm_title(s: pd.Series) -> pd.Series:
    return (
        s.fillna("")
        .str.lower()
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
        .str.replace(r"[^\w\s]", "", regex=True)
        .str.replace(r"\s+", " ", regex=True)
    )


def hits(text: str, terms: list[str]) -> list[str]:
    """Word-boundary matches. Fixes the `term in text` substring bug from Phase 1-2,
    which let 'mir' match 'mirror' and 'omr' match inside longer tokens."""
    found = []
    for t in terms:
        if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", text):
            found.append(t)
    return found


# ML "ensemble" is not a musical ensemble. This was the single largest false-positive
# source in Phase 1-2 screening: 15 of 37 'ensemble' hits in the final corpus are
# ensemble-learning papers.
ML_ENSEMBLE = re.compile(
    r"(?<!\w)(ensemble\s+(learning|learn|method|methods|model|models|classifier|classifiers|"
    r"approach|approaches|technique|techniques|strateg\w*|framework|of\s+(deep|neural|"
    r"classifiers?|models?))|stacking\s+ensemble|ensemble[- ]based\s+(learning|classif\w+|model)|"
    r"voting\s+ensemble|bagging|boosting)(?!\w)"
)

# Terms deliberately EXCLUDED from the ensemble lists after inspecting their actual
# matches in this corpus — each is a homonym that produced a verified false positive:
#   "chorus"  -> song-structure label ("verse or chorus") in music structure analysis.
#                The v2 tagger used it and mis-tagged "Classification of Music Structural
#                Functions using Deep Learning" as an Ensemble paper.
#   "duet"    -> DUET, the Degenerate Unmixing Estimation Technique, a standard blind
#                source separation algorithm named alongside FastICA and NMF.
#   "vibrato" -> an expressive element of violin playing as much as of singing; it
#                mis-tagged "Violinist identification based on vibrato features".
VOCAL_ENSEMBLE = [
    "choral", "choir", "a cappella", "acappella", "satb", "multi-singer",
    "multisinger", "polyphonic vocal", "vocal ensemble", "vocal quartet", "vocal quartets",
    "barbershop", "vocal harmony", "vocal harmonies", "chorale",
]

INSTRUMENTAL_ENSEMBLE = [
    "orchestra", "orchestral", "orchestras", "symphony", "symphonic", "string quartet",
    "quartet", "quartets", "quintet", "trio", "chamber music", "chamber ensemble",
    "big band", "brass band", "wind band", "concert band", "jazz band", "gamelan",
    "philharmonic", "instrumental ensemble", "ensemble performance",
]

SOLO_SINGING = [
    "singing voice", "singer", "singers", "solo singing", "solo voice", "vocal performance",
    "singing style", "singing styles", "singing synthesis", "voice synthesis", "svs",
    "singing transcription", "vocal melody", "lead vocal", "vocalist", "vocalists",
    "singing evaluation", "vocal technique", "singing skill",
]

INSTRUMENTAL = [
    "piano", "violin", "guitar", "drum", "drums", "percussion", "cello", "flute", "clarinet",
    "saxophone", "trumpet", "trombone", "bass guitar", "double bass", "harp", "organ",
    "accordion", "sitar", "pipa", "guzheng", "erhu", "guqin", "tabla", "veena", "sarod",
    "shakuhachi", "koto", "oud", "bagpipe", "ukulele", "mandolin", "banjo", "xylophone",
    "marimba", "vibraphone", "musical instrument", "musical instruments", "instrument recognition",
    "instrument classification", "instrument identification", "instruments sound",
    "instrumental performance", "instrumental music", "fingering", "playing technique",
]

SYMBOLIC = [
    "midi", "symbolic", "music notation", "musical notation", "music score", "music scores",
    "sheet music", "musicxml", "piano roll", "tablature", "abc notation", "kern",
    "optical music recognition", "omr", "score following", "score-informed", "chord chart",
    "lead sheet", "note-level annotation", "symbolic music",
]

MULTIMODAL = [
    "multimodal", "multi-modal", "cross-modal", "crossmodal", "audio-visual", "audiovisual",
    "video", "gesture", "motion capture", "eeg", "electroencephalogram", "sensor data",
    "lyrics", "text-to-music", "image and audio", "vision and audio", "haptic",
]

AUDIO = [
    "audio", "waveform", "spectrogram", "mel-spectrogram", "mel spectrogram", "stft",
    "acoustic", "acoustic signal", "audio signal", "raw audio", "wav", "cqt",
    "constant-q", "mfcc", "chromagram", "time-frequency", "audio recording",
    "audio recordings", "signal processing", "sound", "spectral",
]


def tag_row(text: str) -> dict:
    """Single-label domain with explicit precedence, plus an orthogonal ensemble axis."""
    # Neutralise ML-ensemble phrasing before any musical-ensemble matching.
    musical = ML_ENSEMBLE.sub(" ", text)

    ve = hits(musical, VOCAL_ENSEMBLE)
    ie = hits(musical, INSTRUMENTAL_ENSEMBLE)
    ss = hits(text, SOLO_SINGING)
    inst = hits(text, INSTRUMENTAL)

    # Domain precedence, unchanged from the original tagger so counts stay comparable:
    # vocal ensemble > solo singing > instrumental > unclassified.
    if ve:
        domain, ev, rule = "Ensemble (vocal)", ve, "matched"
    elif ss:
        domain, ev, rule = "Solo Singing", ss, "matched"
    elif inst or ie:
        domain, ev, rule = "Instrumental", (inst + ie), "matched"
    else:
        domain, ev, rule = "Unclassified", [], "no-match default"

    if ve and ie:
        scope, sev = "Mixed / both", ve + ie
    elif ve:
        scope, sev = "Vocal ensemble", ve
    elif ie:
        scope, sev = "Instrumental ensemble", ie
    else:
        scope, sev = "Not indicated", []

    sym = hits(text, SYMBOLIC)
    mm = hits(text, MULTIMODAL)
    aud = hits(text, AUDIO)

    if mm:
        modality, mev, mrule = "Multimodal", mm, "matched"
    elif sym:
        modality, mev, mrule = "Symbolic", sym, "matched"
    elif aud:
        modality, mev, mrule = "Audio", aud, "matched"
    else:
        modality, mev, mrule = "Unspecified", [], "no-match default"

    return {
        "domain": domain,
        "domain_evidence": "; ".join(ev),
        "domain_rule": rule,
        "ensemble_scope": scope,
        "ensemble_evidence": "; ".join(sev),
        "modality": modality,
        "modality_evidence": "; ".join(mev),
        "modality_rule": mrule,
    }


# --------------------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------------------

def build() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    log: list[str] = []

    corpus = pd.read_csv(CLEANED)
    assign = pd.read_csv(ASSIGN)
    corpus["tn"] = norm_title(corpus["title"])
    assign["tn"] = norm_title(assign["title"])

    df = corpus.merge(assign[["tn", "topic"]], on="tn", how="left", validate="one_to_one")
    assert len(df) == 365, f"expected 365 rows, got {len(df)}"
    assert df["topic"].notna().all(), "cluster join incomplete"
    df["cluster_label"] = df["topic"].astype(int).map(CLUSTER_LABELS)
    log.append(f"cluster join: {len(df)}/365 papers matched to a K-Means cluster")

    # ---- 1 & 2: provenance and venue -------------------------------------------------
    merged = pd.read_csv(MERGED, low_memory=False)
    merged["tn"] = norm_title(merged["Title"])
    merged = merged.drop_duplicates(subset="tn", keep="first")

    # merged_deduplicated.csv predates the venue fix in the Phase 1-2 notebook, so its
    # Publication Venue column still carries the bug: the literal string "Scopus" (the
    # which-database flag) was copied in as if it were a journal name, for 8,570 rows.
    # Treat that sentinel as null rather than propagating a fake venue.
    merged["Publication Venue"] = merged["Publication Venue"].replace(
        {"Scopus": pd.NA, "IEEE": pd.NA}
    )

    prov = merged[["tn", "Source Database", "Publication Venue"]].rename(
        columns={"Source Database": "source_database", "Publication Venue": "publication_venue"}
    )
    df = df.merge(prov, on="tn", how="left")

    # second pass on DOI for titles that did not normalise identically
    unmatched = df["source_database"].isna()
    if unmatched.any():
        by_doi = (
            merged.dropna(subset=["DOI"])
            .drop_duplicates(subset="DOI", keep="first")
            .set_index(merged.dropna(subset=["DOI"]).drop_duplicates(subset="DOI", keep="first")["DOI"].str.lower().str.strip())
        )
        fill_src = df.loc[unmatched, "doi"].str.lower().str.strip().map(by_doi["Source Database"])
        fill_ven = df.loc[unmatched, "doi"].str.lower().str.strip().map(by_doi["Publication Venue"])
        df.loc[unmatched, "source_database"] = fill_src
        df.loc[unmatched, "publication_venue"] = fill_ven

    n_prov = int(df["source_database"].notna().sum())
    df["source_database"] = df["source_database"].fillna("Unrecovered")
    log.append(
        f"provenance recovered for {n_prov}/365 papers "
        f"({df['source_database'].value_counts().to_dict()})"
    )
    n_ven = int(df["publication_venue"].notna().sum())
    log.append(
        f"publication venue recovered for {n_ven}/365 papers — IEEE rows only. Scopus "
        f"venues were never pulled from the API, and the placeholder string 'Scopus' that "
        f"the old harmonisation step wrote into that column has been nulled rather than "
        f"propagated. Real Scopus venues need a re-pull or a Crossref DOI lookup."
    )

    # ---- 3, 4, 5: re-tag --------------------------------------------------------------
    text = (
        df["title"].fillna("") + " " + df["abstract"].fillna("") + " " + df["keywords"].fillna("")
    ).str.lower().str.replace("\xa0", " ", regex=False)

    tags = pd.DataFrame([tag_row(t) for t in text], index=df.index)
    df = pd.concat([df, tags], axis=1)

    old = pd.read_csv(OLDTAGS)
    old["tn"] = norm_title(old["title"])
    df = df.merge(
        old[["tn", "domain", "modality"]].rename(
            columns={"domain": "domain_v2_original", "modality": "modality_v2_original"}
        ),
        on="tn",
        how="left",
    )

    log.append(
        "domain no-match defaults: "
        f"{int((df['domain_rule'] == 'no-match default').sum())}/365 "
        f"(was 170/365 reported as 'General MIR')"
    )
    log.append(
        "modality no-match defaults: "
        f"{int((df['modality_rule'] == 'no-match default').sum())}/365 "
        f"(was 259/365 reported as 'Audio')"
    )

    tags_out = df[[
        "title", "authors", "year", "doi", "source_database", "publication_venue",
        "topic", "cluster_label",
        "domain", "domain_evidence", "domain_rule", "domain_v2_original",
        "ensemble_scope", "ensemble_evidence",
        "modality", "modality_evidence", "modality_rule", "modality_v2_original",
    ]].copy()

    # ---- 6: quality -------------------------------------------------------------------
    q = pd.read_csv(QUALITY)
    q["tn"] = norm_title(q["title"])
    q = q.merge(df[["tn", "domain", "ensemble_scope", "modality"]], on="tn", how="left",
                suffixes=("_old", ""))
    q["quality_total_excl_alignment"] = q["quality_total"] - q["q_alignment"]
    q["quality_pct_excl_alignment"] = (q["quality_total_excl_alignment"] / 40 * 100).round(1)
    log.append(
        "q_alignment scores 5 for "
        f"{int((q['q_alignment'] == 5).sum())}/365 papers; "
        "quality_total_excl_alignment added (max 40) so the near-constant criterion "
        "no longer inflates every total"
    )

    return tags_out, q, log


def crosstabs(tags: pd.DataFrame, q: pd.DataFrame, log: list[str]) -> str:
    L: list[str] = []
    w = L.append

    w("MUTECH SLR — CORRECTED NUMBERS MANIFEST v3")
    w("=" * 78)
    w("")
    w("Corpus frozen at 365 papers (Rayyan-included). No paper added or removed.")
    w("All matching is word-boundary; ML-ensemble phrasing is neutralised before any")
    w("musical-ensemble term is tested. Categories previously reported as 'General MIR'")
    w("and 'Audio' were the tagger's no-match defaults and are now named as such.")
    w("")
    w("REBUILD LOG")
    w("-" * 78)
    for line in log:
        w(f"  - {line}")
    w("")

    w("CORPUS PROVENANCE (recovered — was 'Rayyan' for all 365)")
    w("-" * 78)
    w(tags["source_database"].value_counts().to_string())
    w("")

    w("DOMAIN (corrected; 'Unclassified' = no domain keyword matched)")
    w("-" * 78)
    dv = tags["domain"].value_counts()
    for k, v in dv.items():
        w(f"  {k:<22} {v:>4}  {v / len(tags) * 100:>5.1f}%")
    w("")
    w("  Change vs the v2 tags used in the manuscript drafts:")
    ct = pd.crosstab(tags["domain_v2_original"], tags["domain"])
    w(ct.to_string())
    w("")

    w("ENSEMBLE SCOPE (new orthogonal axis — the v2 'Ensemble' domain was vocal-only)")
    w("-" * 78)
    es = tags["ensemble_scope"].value_counts()
    for k, v in es.items():
        w(f"  {k:<24} {v:>4}  {v / len(tags) * 100:>5.1f}%")
    w("")
    w("  Any multi-performer indication: "
      f"{int((tags['ensemble_scope'] != 'Not indicated').sum())} papers "
      f"({(tags['ensemble_scope'] != 'Not indicated').mean() * 100:.1f}%) — compare the")
    w("  manuscript's 'Ensemble is a 2.7% niche (10 papers)', which counted vocal only.")
    w("")
    w("  Ensemble scope x domain:")
    w(pd.crosstab(tags["ensemble_scope"], tags["domain"]).to_string())
    w("")

    w("MODALITY (corrected; 'Unspecified' = no modality keyword matched)")
    w("-" * 78)
    mv = tags["modality"].value_counts()
    for k, v in mv.items():
        w(f"  {k:<22} {v:>4}  {v / len(tags) * 100:>5.1f}%")
    w("")
    w("  Change vs v2:")
    w(pd.crosstab(tags["modality_v2_original"], tags["modality"]).to_string())
    w("")

    w("YEAR x DOMAIN (corrected)")
    w("-" * 78)
    w(pd.crosstab(tags["year"], tags["domain"], margins=True, margins_name="All").to_string())
    w("")

    w("DOMAIN x MODALITY (corrected)")
    w("-" * 78)
    w(pd.crosstab(tags["domain"], tags["modality"], margins=True, margins_name="All").to_string())
    w("")

    w("CLUSTER x DOMAIN (corrected)")
    w("-" * 78)
    w(pd.crosstab(tags["cluster_label"], tags["domain"], margins=True, margins_name="All").to_string())
    w("")

    w("CLUSTER SIZES (unchanged — K-Means partition is not touched)")
    w("-" * 78)
    for k, v in tags["cluster_label"].value_counts().items():
        w(f"  {k:<45} {v:>4}  {v / len(tags) * 100:>5.1f}%")
    w("")

    # ---- 7: growth --------------------------------------------------------------------
    w("CLUSTER GROWTH — RAW vs PER-YEAR vs SHARE-NORMALISED")
    w("-" * 78)
    w("The manuscript's 6.2x figure compares 2020-2022 (3 years, 123 papers) against")
    w("2023-2026 (4 years, 242 papers, 2026 partial). Raw ratios inherit that asymmetry.")
    w("")
    era = tags["year"].apply(lambda y: "2020-2022" if y <= 2022 else "2023-2026")
    g = pd.crosstab(tags["cluster_label"], era)
    n_early, n_late = 3, 4
    tot_e, tot_l = int(g["2020-2022"].sum()), int(g["2023-2026"].sum())
    g["raw_ratio"] = (g["2023-2026"] / g["2020-2022"]).round(2)
    g["per_year_ratio"] = ((g["2023-2026"] / n_late) / (g["2020-2022"] / n_early)).round(2)
    g["share_early_%"] = (g["2020-2022"] / tot_e * 100).round(1)
    g["share_late_%"] = (g["2023-2026"] / tot_l * 100).round(1)
    g["share_ratio"] = (g["share_late_%"] / g["share_early_%"]).round(2)
    w(g.sort_values("per_year_ratio", ascending=False).to_string())
    w("")
    w(f"  Whole corpus: {tot_e} -> {tot_l} = {tot_l / tot_e:.2f}x raw, "
      f"{(tot_l / n_late) / (tot_e / n_early):.2f}x per year.")
    w("  Music Education & Performance Assessment: 6.18x raw becomes 4.64x per year and")
    w("  3.14x once normalised against corpus growth. The relative ordering of clusters")
    w("  survives all three framings; the headline multiplier does not.")
    w("")

    w("QUALITY SCORES — CORRECTED BINS AND ALIGNMENT-ADJUSTED TOTALS")
    w("-" * 78)
    w("Original bin labels (0-20, 20-25, 25-30, ...) overlap at every boundary. They")
    w("compute correctly only because nine criteria scored 1/3/5 can never sum to an even")
    w("number — quality_total takes only 13 attainable odd values, 17 to 41.")
    w("")
    bins = [16, 20, 25, 30, 35, 40, 45]
    labels = ["17-20", "21-25", "26-30", "31-35", "36-40", "41-45"]
    q["band"] = pd.cut(q["quality_total"], bins=bins, labels=labels)
    b = q["band"].value_counts().reindex(labels)
    w("  Total (max 45, as reported):")
    for k, v in b.items():
        w(f"    {k:<8} {int(v):>4}  {v / len(q) * 100:>5.1f}%")
    w("")
    w(f"  mean {q['quality_total'].mean():.2f}  median {q['quality_total'].median():.0f}  "
      f"range {q['quality_total'].min():.0f}-{q['quality_total'].max():.0f}")
    w(f"  below 30/45: {int((q['quality_total'] < 30).sum())} papers "
      f"({(q['quality_total'] < 30).mean() * 100:.1f}%)")
    w("")
    w("  Alignment-adjusted total (max 40, q_alignment removed — 345/365 papers score 5")
    w("  on it, so it discriminates almost nothing while contributing 11% of the maximum):")
    w(f"    mean {q['quality_total_excl_alignment'].mean():.2f}  "
      f"median {q['quality_total_excl_alignment'].median():.0f}  "
      f"range {q['quality_total_excl_alignment'].min():.0f}-"
      f"{q['quality_total_excl_alignment'].max():.0f}")
    w("")
    w("  Per-criterion means (n=365):")
    for c in ["q_design", "q_data", "q_methods", "q_validation", "q_alignment",
              "q_contribution", "q_applicability", "q_significance", "q_reproducibility"]:
        w(f"    {c:<20} {q[c].mean():.2f}   (=5 for {int((q[c] == 5).sum()):>3} papers)")
    w("")
    w("  Reproducibility caveat: q_reproducibility is scored by looking for code- and")
    w("  data-availability language in abstracts. 47.4% sit at the 1/5 floor, but the")
    w("  instrument cannot distinguish 'no code released' from 'code released, not")
    w("  mentioned in the abstract'. Report as an abstract-reporting-practice measure.")
    w("")

    w("KNOWN DEFECTS THAT CANNOT BE REPAIRED WITHOUT RE-SCREENING")
    w("-" * 78)
    w("Corpus is frozen, so these are recorded for footnoting rather than fixed:")
    w("")
    w("  1. Phase 1-2 screening used substring matching (`term in text`). Bare tokens")
    w("     'mir', 'omr', 'ensemble' and 'instrumental' were in priority_terms, so")
    w("     'mir' matched inside longer words and 'ensemble' matched ensemble LEARNING.")
    w("     15 of 37 'ensemble' hits in the final corpus use ML phrasing; 'ensemble' is")
    w("     the sole qualifying music term for 17 included papers.")
    w("  2. A missing-comma bug in exclude_terms silently concatenated six criteria into")
    w("     three unmatchable strings: artist tagging, semantic tagging, genre tagging,")
    w("     hearing aid, hearing impairment, music generation never ran.")
    w("  3. One verified inclusion error follows from (1) and (2): 'Speech emotion")
    w("     recognition with light weight deep neural ensemble model using hand crafted")
    w("     features' is a speech paper in the final 365.")
    w("  4. PRISMA identification counts Scopus at 8,943, but that file is already")
    w("     post-exclusion (non-Article/Conference types and null-abstract records were")
    w("     dropped in the extraction cell). The true identification count was printed")
    w("     to a cell output that was not captured.")
    w("  5. IEEE returned exactly 1,000 records — an export ceiling, not a result. The")
    w("     notebook's IEEE cell sets max_records=200, which does not match the 1,000-row")
    w("     file, so the checked-in export came from an undocumented route.")
    w("  6. Scopus 'creator' is the FIRST AUTHOR ONLY. All 365 records carry one name.")
    w("     Fixing this needs a Scopus re-pull with author_names, or a Crossref DOI")
    w("     lookup — neither is possible offline. Every 'et al.' in the drafts and 18 of")
    w("     99 citations in challenge_evidence.csv (initials parsed as surnames) depend")
    w("     on it.")
    w("  7. Silhouette for the selected K-Means partition is 0.0389. The clusters are")
    w("     interpretable but weakly separated; cluster-level claims are exploratory.")
    w("  8. Phase 5's modularity 0.53 is computed on a kNN graph built from the same")
    w("     TF-IDF cosine geometry K-Means partitions, so it is not independent")
    w("     validation. Louvain on that graph finds 10 communities, not 7.")
    w("  9. validation_sample_30.xlsx is an empty template (header + 23 blank rows).")
    w("     The 'validated against a manually reviewed sample' claim has no receipt.")
    w(" 10. quality_spotcheck_15.xlsx flags 7 of 15 rows — a 47% human-scorer")
    w("     disagreement rate. No post-fix re-validation sheet exists.")
    w("")

    return "\n".join(L)


def main() -> None:
    tags, q, log = build()

    tags.to_csv(OUT / "domain_modality_tags_v3.csv", index=False)
    tags[["title", "doi", "source_database", "publication_venue"]].to_csv(
        OUT / "corpus_provenance.csv", index=False
    )
    q.drop(columns=["tn"]).to_csv(OUT / "quality_scores_v2.csv", index=False)
    (OUT / "numbers_manifest_v3.txt").write_text(crosstabs(tags, q, log), encoding="utf-8")

    print(f"wrote {OUT}/domain_modality_tags_v3.csv")
    print(f"wrote {OUT}/corpus_provenance.csv")
    print(f"wrote {OUT}/quality_scores_v2.csv")
    print(f"wrote {OUT}/numbers_manifest_v3.txt")


if __name__ == "__main__":
    main()
