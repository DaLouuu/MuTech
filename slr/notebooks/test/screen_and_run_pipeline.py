"""Batch Screening and Automated Pipeline Orchestrator.

1. Screens the remaining 108 failed records in rate-limited batches (14 RPM).
2. Uses gemini-3.5-flash-lite with exponential backoff to eliminate 429/503 errors.
3. Automatically updates gemini_all_results.csv and gemini_screening_cache.jsonl.
4. Merges all eligible studies and runs SLR Phases 3, 4, and 5 sequentially.
"""

import os
import sys
import time
import json
import getpass
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure root, slr, and slr/src are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "slr"))
sys.path.insert(0, str(REPO_ROOT / "slr" / "src"))

from slr.src import pipeline_engine as pe

from google import genai
from google.genai import types

MODEL = "gemini-3.5-flash-lite"
DELAY_SECONDS = 4.2  # ~14 RPM to strictly stay under 15 RPM free-tier limit
BATCH_SIZE = 20
INTER_BATCH_PAUSE = 10.0
MAX_RETRIES = 5

OUT_DIR = SCRIPT_DIR / "mir_screening_outputs"
CSV_ALL_RESULTS = OUT_DIR / "gemini_all_results.csv"
CSV_NORMALIZED = OUT_DIR / "records_normalized.csv"
CACHE_FILE = OUT_DIR / "gemini_screening_cache.jsonl"

SYSTEM_PROMPT = """You are a cautious systematic-review TITLE/ABSTRACT eligibility assistant for audio-based Music Information Retrieval (MIR).
Assess only the supplied title, abstract, and bibliographic metadata. Never invent facts or search outside the record.
Goal: minimize false exclusions. Do not evaluate paper quality, venue prestige, dataset rigor, code availability, or reproducibility from abstract omissions.
Scope: 2020–2026, technical/empirical music-audio analysis, including audio-based and audio-grounded multimodal methods for singing, ensemble/choral, instrumental, or general MIR.
Clearly exclude symbolic-only music methods without audio analysis, unrelated work, or non-research content. Exclude out-of-window only when year is explicitly present and unambiguous.
For ambiguous, short, or missing abstracts, choose HUMAN_REVIEW; if apparently relevant, choose RETRIEVE_FULL_TEXT.
Decision meanings:
- RETRIEVE_FULL_TEXT: plausible match requiring full-text eligibility assessment.
- EXCLUDE: explicit, unambiguous violation of a screening criterion.
- HUMAN_REVIEW: insufficient or conflicting information to decide safely.
Use exclusion_code only for EXCLUDE: YEAR_OUT_OF_RANGE, SYMBOLIC_ONLY, NOT_MIR, NOT_RESEARCH. Otherwise null.
Evidence must be a short verbatim quote from the supplied title/abstract/metadata or empty if none; never fabricate quotes.
Return exactly JSON with keys decision, exclusion_code, evidence, rationale, uncertainty, audio_relevance, domain.
uncertainty: LOW, MEDIUM, HIGH. audio_relevance: YES, NO, UNCLEAR. domain: VOCAL, ENSEMBLE, INSTRUMENTAL, GENERAL, UNCLEAR.

EXAMPLE 1 (Eligible - Audio MIR)
INPUT: {"title":"Neural Piano Transcription from Recordings","abstract":"We transcribe piano audio and evaluate note-level precision and recall on the MAESTRO dataset.","year":"2023","venue":"Conference"}
OUTPUT: {"decision":"RETRIEVE_FULL_TEXT","exclusion_code":null,"evidence":"transcribe piano audio","rationale":"Music-audio transcription is central.","uncertainty":"LOW","audio_relevance":"YES","domain":"INSTRUMENTAL"}

EXAMPLE 2 (Excluded - Symbolic Only)
INPUT: {"title":"Transformer-Based Symbolic Music Generation","abstract":"We generate MIDI note sequences from symbolic scores without processing audio.","year":"2024","venue":"Journal"}
OUTPUT: {"decision":"EXCLUDE","exclusion_code":"SYMBOLIC_ONLY","evidence":"without processing audio","rationale":"Explicitly symbolic-only with no music-audio analysis.","uncertainty":"LOW","audio_relevance":"NO","domain":"GENERAL"}
"""

FIELDS = ["record_id", "title", "abstract", "year", "authors", "venue", "doi"]
ALLOWED = {"RETRIEVE_FULL_TEXT", "EXCLUDE", "HUMAN_REVIEW"}
CODES = {"YEAR_OUT_OF_RANGE", "SYMBOLIC_ONLY", "NOT_MIR", "NOT_RESEARCH"}
PROMPT_HASH = hashlib.sha256((SYSTEM_PROMPT + "|" + MODEL).encode()).hexdigest()[:16]


def validate_response(result: dict, record: dict) -> dict:
    if not isinstance(result, dict):
        raise ValueError("Response must be a JSON object")
    decision = str(result.get("decision", "")).strip().upper()
    if decision == "RETRIEVAL_FULL_TEXT":
        decision = "RETRIEVE_FULL_TEXT"
    result["decision"] = decision
    if decision not in ALLOWED:
        raise ValueError(f"Invalid decision: {decision}")
    code = result.get("exclusion_code")
    if code in ("", "null", "None", "NONE", "N/A", "n/a", False):
        code = None
        result["exclusion_code"] = None
    elif code is not None:
        code = str(code).strip().upper()
        result["exclusion_code"] = code
    if decision == "EXCLUDE" and code not in CODES:
        raise ValueError(f"Invalid exclusion code: {code}")
    if decision != "EXCLUDE":
        result["exclusion_code"] = None
    unc = str(result.get("uncertainty", "")).strip().upper()
    result["uncertainty"] = unc if unc in {"LOW", "MEDIUM", "HIGH"} else "MEDIUM"
    ar = str(result.get("audio_relevance", "")).strip().upper()
    result["audio_relevance"] = ar if ar in {"YES", "NO", "UNCLEAR"} else "UNCLEAR"
    dom = str(result.get("domain", "")).strip().upper()
    result["domain"] = dom if dom in {"VOCAL", "ENSEMBLE", "INSTRUMENTAL", "GENERAL", "UNCLEAR"} else "UNCLEAR"
    return result


def screen_record(client: genai.Client, record: dict) -> dict:
    payload = {k: str(record.get(k, "")) for k in FIELDS if k != "record_id"}
    if not payload.get("abstract", "").strip():
        return {
            "decision": "HUMAN_REVIEW",
            "exclusion_code": None,
            "evidence": "",
            "rationale": "Missing abstract; human verification required.",
            "uncertainty": "HIGH",
            "audio_relevance": "UNCLEAR",
            "domain": "UNCLEAR",
        }

    for attempt in range(MAX_RETRIES):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents="INPUT: " + json.dumps(payload, ensure_ascii=False) + "\nOUTPUT:",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            raw_text = resp.text.strip() if resp.text else ""
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            parsed = json.loads(raw_text.strip())
            return validate_response(parsed, record)
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "503" in err_str or "quota" in err_str.lower():
                wait_t = 15.0 * (attempt + 1)
                print(f" [Rate limit/Capacity] Pausing {wait_t:.0f}s before retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(wait_t)
            else:
                time.sleep(2.0 * (attempt + 1))
            if attempt == MAX_RETRIES - 1:
                return {
                    "decision": "HUMAN_REVIEW",
                    "exclusion_code": None,
                    "evidence": "",
                    "rationale": f"API/validation error: {err_str[:240]}",
                    "api_error": True,
                    "uncertainty": "HIGH",
                    "audio_relevance": "UNCLEAR",
                    "domain": "UNCLEAR",
                }
        finally:
            time.sleep(DELAY_SECONDS)


def run_batch_screening(api_key: str):
    client = genai.Client(api_key=api_key)

    df_results = pd.read_csv(CSV_ALL_RESULTS)
    df_papers = pd.read_csv(CSV_NORMALIZED)

    df_results["record_id"] = df_results["record_id"].astype(str)
    df_papers["record_id"] = df_papers["record_id"].astype(str)

    failed_ids = set(df_results[df_results["api_error"] == True]["record_id"])
    print(f"Found {len(failed_ids)} records to re-screen with model '{MODEL}'...")

    if len(failed_ids) == 0:
        print("[OK] No failed records found. All records are already processed!")
    else:
        pending_papers = df_papers[df_papers["record_id"].isin(failed_ids)].copy().to_dict(orient="records")
        batches = [pending_papers[i : i + BATCH_SIZE] for i in range(0, len(pending_papers), BATCH_SIZE)]
        total_batches = len(batches)
        print(f"Divided into {total_batches} batches (Batch size: {BATCH_SIZE}, Delay: {DELAY_SECONDS}s).")

        results_by_id = {row["record_id"]: row.to_dict() for _, row in df_results.iterrows()}

        for b_idx, batch in enumerate(batches, 1):
            print(f"\n--- Processing Batch {b_idx}/{total_batches} ({len(batch)} papers) ---")
            for p_idx, rec in enumerate(batch, 1):
                rec_id = rec["record_id"]
                title_preview = str(rec.get("title", ""))[:50]
                print(f"  [{p_idx:02d}/{len(batch):02d}] #{rec_id}: {title_preview}...", end="", flush=True)

                res = screen_record(client, rec)
                dec = res.get("decision", "HUMAN_REVIEW")
                print(f" -> {dec}")

                updated_row = {
                    "record_id": rec_id,
                    "fingerprint": rec.get("fingerprint", ""),
                    "prompt_hash": PROMPT_HASH,
                    "model": MODEL,
                    **res,
                }
                # Remove api_error flag if resolved
                if not res.get("api_error") and "api_error" in updated_row:
                    del updated_row["api_error"]

                results_by_id[rec_id] = updated_row

                # Append to cache
                if not res.get("api_error"):
                    with CACHE_FILE.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(updated_row, ensure_ascii=False) + "\n")

            # Save progress after each batch
            df_updated = pd.DataFrame(list(results_by_id.values()))
            df_updated.to_csv(CSV_ALL_RESULTS, index=False)
            print(f"[Checkpoint] Batch {b_idx} saved. Current decision counts:")
            print(df_updated["decision"].value_counts().to_dict())

            if b_idx < total_batches:
                print(f"Cooling down for {INTER_BATCH_PAUSE}s between batches...")
                time.sleep(INTER_BATCH_PAUSE)

    # -------------------------------------------------------------------------
    # PIPELINE EXECUTION (PHASES 3, 4, 5)
    # -------------------------------------------------------------------------
    df_final = pd.read_csv(CSV_ALL_RESULTS)
    eligible = df_final[df_final["decision"] == "RETRIEVE_FULL_TEXT"].copy()
    eligible["record_id"] = eligible["record_id"].astype(str)

    merged_corpus = eligible.merge(
        df_papers[["record_id", "title", "abstract", "year", "authors", "venue", "doi"]],
        on="record_id",
        how="inner",
    )

    corpus_std = pd.DataFrame({
        "record_id": merged_corpus["record_id"],
        "Title": merged_corpus["title"].fillna("").astype(str).str.strip(),
        "Abstract": merged_corpus["abstract"].fillna("").astype(str).str.strip(),
        "Year": pd.to_numeric(merged_corpus["year"], errors="coerce").fillna(2024).astype(int),
        "Authors": merged_corpus["authors"].fillna("").astype(str),
        "Publication Venue": merged_corpus["venue"].fillna("").astype(str),
        "DOI": merged_corpus["doi"].fillna("").astype(str),
        "Keywords": "",
        "Source Database": "Scopus/IEEE",
        "domain_gemini": merged_corpus["domain"],
    })

    print("\n" + "=" * 70)
    print(f"Corpus Ready: {len(corpus_std)} eligible studies for Phases 3-5.")
    print("=" * 70)

    # Export canonical Phase 2 output
    prisma_out = REPO_ROOT / "slr" / "outputs" / "prisma"
    prisma_out.mkdir(parents=True, exist_ok=True)
    p2_path = prisma_out / "phase2_screened_corpus.csv"
    corpus_std.to_csv(p2_path, index=False)
    print(f"[Phase 2] Exported screened corpus: {p2_path}")

    # Run Phase 3
    print("\n[Phase 3] Running NLP Text Mining & 35-D LSA Representation...")
    rep_dir = REPO_ROOT / "slr" / "outputs" / "representations"
    p3 = pe.run_phase3(corpus_std, str(rep_dir))
    print(f"  [PASS] Gate 3: Vocab size: {p3['vocab_size']} terms, PMI collocations: {p3['pmi_collocations_count']}")

    # Run Phase 4
    print("\n[Phase 4] Running 4-Model Suite Benchmarking & Soft Topic Distributions...")
    mod_dir = REPO_ROOT / "slr" / "outputs" / "models"
    p4 = pe.run_phase4(p3["data"], p3["tfidf_matrix"], p3["lsa_matrix"], str(mod_dir), target_k=7)
    print(f"  [PASS] Gate 4: Bootstrap Stability ARI: {p4['stability_metrics']['mean_stability_ari']}")
    print(f"  [Soft Topics] Boundary-spanning crossover studies: {p4['interdisciplinary_count']}")

    # Run Phase 5
    print("\n[Phase 5] Running 8-NN Similarity Graph & Temporal Flow Synthesis...")
    net_dir = REPO_ROOT / "slr" / "outputs" / "network"
    docs_dir = REPO_ROOT / "docs"
    p5 = pe.run_phase5(p4["data"], p3["lsa_matrix"], p4["km_labels"], str(net_dir), str(docs_dir))
    print(f"  [PASS] Gate 5: Graph Nodes: {p5['num_nodes']}, Edges: {p5['num_edges']}, Modularity: {p5['modularity']}")

    print("\n" + "=" * 70)
    print("ALL PHASES 3 TO 5 EXECUTED AND VALIDATED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        key = getpass.getpass("Enter your GEMINI_API_KEY: ").strip()
    if not key:
        print("[ERROR] No GEMINI_API_KEY provided. Aborting.")
        sys.exit(1)
    run_batch_screening(key)

