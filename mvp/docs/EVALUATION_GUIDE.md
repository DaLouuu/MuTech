# Evaluation guide

How the comparison in the [research report](RESEARCH_REPORT.md) was produced, how to re-run it, and how to extend it. Scripts live in [`../eval/`](../eval).

## 1. What is measured

Both models take a choir mixture and output, per time frame, a set of pitches. We compare that set with a **reference** set of pitches for the same frame using the standard multipitch metrics from `mir_eval`.

| Metric | Plain meaning |
|---|---|
| Precision | Of the pitches the model reported, the fraction that were correct. Low = lots of false pitches |
| Recall | Of the pitches really sounding, the fraction the model found. Low = misses notes |
| F-measure | Single number combining precision and recall (we compute it as 2PR / (P+R)) |
| Accuracy | Stricter: correct / (correct + missed + false), per frame, counted together. Always lower than F-measure |
| Chroma accuracy | Same, but a pitch an octave off still counts as right |

A pitch counts as correct if it is within **50 cents** (half a semitone) of a reference pitch in the same frame. Scoring at 100 cents gave the same numbers to two decimals, so almost every matched estimate is already well within 50 cents.

## 2. Test data

### Source audio

The Choral Singing Dataset (CSD): three songs (Locus Iste, El Rossinyol, Nino Dios), each sung by several singers per part (soprano, alto, tenor, bass), recorded one singer at a time. We did not download it separately: the UMSS repository ships the stems under `Datasets/ChoralSingingDataset/<Song>/audio_16kHz/`.

### The 14 test mixtures (built by `eval/prep_data.py`)

All excerpts are 30 seconds, resampled to 22,050 Hz, peak normalised to 0.5. Random choices use a fixed seed (7), so rebuilding gives the same mixtures.

| Name | What it is | Tests |
|---|---|---|
| B01 to B06 | One random singer per part (S, A, T, B) mixed together. Songs: Locus Iste (B01, B04), El Rossinyol (B02, B05), Nino Dios (B03, B06) | Baseline quality |
| N20, N10, N00 | B01 plus white noise at 20, 10 and 0 dB signal to noise ratio | Noise |
| R12, R12b | B01 and B04 plus synthetic reverb, decay time 1.2 s, 40% wet | Reverb |
| DET | B02 with the alto 30 cents sharp and the bass 25 cents flat (references shifted to match) | Does the model follow out of tune singers or snap to the piano grid |
| P2 | B03 with soprano and bass only | Fewer voices |
| P3 | B03 with soprano, tenor and bass | Fewer voices |

### References (ground truth)

For each singer's isolated stem we ran **pYIN** (a single voice pitch tracker, via `librosa.pyin`), range 65 to 1047 Hz, hop 256, keeping frames with voiced probability above 0.7. The reference for a mixture is the set of pYIN pitches of its singers at each frame.

**This is an approximation.** pYIN makes mistakes (octave errors, gaps in breathy or quiet passages) and those become errors in the reference. Where the reference has gaps, the model's correct pitches count as false alarms, so **precision is understated**. Human annotated data (Dagstuhl ChoirSet, Cantoría) would be better.

## 3. How to re-run everything

Needs the three repositories cloned next to each other (or set the environment variables):

```bash
git clone --depth 1 https://github.com/helenacuesta/multif0-estimation-polyvocals   # weights + original code
git clone --depth 1 https://github.com/schufo/umss                                   # carries the CSD stems (868 MB)
git clone --depth 1 https://github.com/sony/timbre-trap                              # only for the Timbre-Trap comparison

export MF0_REPO=$PWD/multif0-estimation-polyvocals
export CSD_DIR=$PWD/umss/Datasets/ChoralSingingDataset
export TT_REPO=$PWD/timbre-trap
export TT_WEIGHTS=$PWD/tt-orig.pt        # download tt-orig.pt (11 MB) from the Files tab of huggingface.co/spaces/cwitkowitz/timbre-trap

python3.12 -m venv .venv && source .venv/bin/activate
pip install -r mvp/requirements.txt
cd mvp/eval && mkdir -p data out
```

Then, in order:

| Step | Command | Output | Time (2 CPU cores) |
|---|---|---|---|
| 1. Build the test set | `python prep_data.py` | `data/*.wav`, `data/tests.pkl` | about 1 minute |
| 2. Run multif0 | `python mf0_estimate.py` | `out/mf0_<name>.npz` | about 5 minutes |
| 3. Run Timbre-Trap | `python tt_estimate.py` (**separate environment**, see below) | `out/tt_<name>.npz` | about 5 minutes |
| 4. Score | `python evaluate.py` | `results.json` and a printed summary | under a minute |

`.npz` files hold the raw activation maps, so step 4 can be repeated with different thresholds without re-running the models.

**Timbre-Trap needs PyTorch.** Use a second environment: `pip install -r mvp/requirements-timbretrap.txt`, plus the dependencies listed in the Timbre-Trap repository's `requirements.txt`. We ran it on the same Python 3.12 with CPU PyTorch.

**Do not run steps 2 and 3 at the same time on a small machine.** They compete for the CPU and the timings in the log become meaningless (we saw 40 to 80 seconds instead of 20 for the same clip).

### Smaller checks

- `port_test.py`: builds the ported multif0 on a synthetic six second chord (C3, G3, C4, E4) and checks every pitch is found. Fastest way to confirm a new environment works.
- `tt_test.py`: the same idea for Timbre-Trap. Run it from the folder holding `tt-orig.pt`, or set `TT_WEIGHTS`.

## 4. How the scoring works (`evaluate.py`)

1. Load the saved activation map. For multif0 the frequency of bin *k* is `librosa.cqt_frequencies(360, fmin=32.7, bins_per_octave=60)[k]`. For Timbre-Trap it is `(11025/2**9) * 2**(k/60)` (540 bins); its activations are max pooled by 4 frames to bring the time step near multif0's.
2. **Peak picking:** in each frame keep bins that are local maxima along frequency and at least the threshold (default 0.5 for both).
3. Build the reference frames from the pYIN output.
4. Call `mir_eval.multipitch.evaluate`. mir_eval resamples whichever time grid differs and prints a warning; this is expected.
5. Also computed: a threshold sweep (multif0: 0.3 to 0.7; Timbre-Trap: 0.3 to 0.9), scoring at 100 cents, and per part cents error: for every reference pitch with an estimate within 100 cents, the signed cents difference to the nearest estimate; the table reports mean absolute error.

Interpretation guide for cents errors: multif0 outputs on a 20 cent grid, so differences under about 10 cents are not resolved.

## 5. Results at a glance

Full tables and discussion are in the [research report](RESEARCH_REPORT.md#test-results). Headline (mean of B01 to B06, threshold 0.5):

| | multif0 | Timbre-Trap |
|---|---|---|
| Precision | 0.75 | 0.67 |
| Recall | 0.92 | 0.65 |
| F-measure | 0.83 | 0.65 |
| Accuracy | 0.71 | 0.48 |

## 6. Known weaknesses of this evaluation

1. **multif0 has seen this data.** CSD is part of its training set. Its scores are optimistic and the true gap to Timbre-Trap is probably smaller. Timbre-Trap was trained only on instrument recordings (URMP).
2. **References come from pYIN**, not humans.
3. **Small and narrow:** six base mixtures, three songs, one 30 second excerpt each.
4. **Synthetic degradations:** noise is white noise, reverb is an exponentially decaying noise impulse response, not real rooms.
5. **P2 and P3 confound** two things (genuinely sparse mixtures and gaps in the reference). The low precision there should not be read as pure model error.
6. Timing numbers are from a 2 core CPU container and will differ on other hardware.

## 7. How to extend it (recommended order)

1. **Cantoría** ([Zenodo record 5878677](https://zenodo.org/record/5878677)): vocal quartet recordings that multif0 did *not* train on. Needs someone to download it manually (the sandbox we used could not reach Zenodo). Convert its annotations into the same "list of Hz per frame" shape and reuse `evaluate.py`'s scoring functions. This is the single most valuable next test.
2. **Dagstuhl ChoirSet** ([Zenodo record 3897181](https://zenodo.org/record/3897181)): has note and F0 annotations by humans, but multif0 trained on it.
3. **Compare against the original TensorFlow 1.15 outputs** for the same file, frame by frame, if anyone can run the original (Python 3.6 or 3.7 only). It proves the port is exact.
4. **Interpolation test:** add parabolic peak refinement and check whether the cents error on the DET mixture drops below the 20 cent grid.
5. **Real recordings:** record the group (or any choir) on phones and see how far the lab numbers hold up.
