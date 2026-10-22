# MVP base candidates: open source shortlist from the MIR SLR

*Task 1 report. Written 2026-10-21. Companion docs: [back end guide](BACKEND_GUIDE.md), [front end guide](FRONTEND_GUIDE.md), [evaluation guide](EVALUATION_GUIDE.md), [decisions and next steps](DECISIONS_AND_NEXT_STEPS.md), [glossary](GLOSSARY.md).*

## Summary

Two repositories from studies in our SLR are viable MVP bases: Cuesta et al.'s multi-F0 estimator for vocal ensembles (MIT, pretrained weights, runs after a small port) and Sony's Timbre-Trap (MIT, PyTorch, runs as is). Both were run on 14 real choir test mixtures, and multif0 was wrapped in a working web API. **Build on multif0 and keep Timbre-Trap as the fallback.**

## Recommendation

Build the MVP on **multif0-estimation-polyvocals** (Cuesta, McFee and Gómez, ISMIR 2020). It is the only candidate built specifically for choir and vocal quartet audio, it is MIT licensed, and it ships five pretrained models. Its weakness is age: the last commit is 2021-03-04 and it pins TensorFlow 1.15 and Python 3.6. The model was ported to Keras 3 on Python 3.12, run on real choir audio, and served through a FastAPI endpoint, so that risk is now mostly retired (see [Backend prototype](#backend-prototype)).

Keep **Timbre-Trap** (Cwitkowitz et al., ICASSP 2024) as the fallback. It is MIT licensed, runs unmodified on Python 3.12 with PyTorch, and is about twice as fast. On the choir tests it scored clearly lower, which fits its training on instrument recordings only.

The other candidates (UMSS, MusicYOLO, YourMT3+, score following) are not good first bases. Reasons are in [Other candidates](#other-candidates).

## Headline results

Six real choir mixtures (30 seconds each, three songs, four singers each: one per part), scored with mir_eval multipitch at 50 cents. Values are means over the six clean mixtures at the default threshold of 0.5.

| Metric | multif0 | Timbre-Trap |
|---|---|---|
| Precision | 0.75 | 0.67 |
| Recall | 0.92 | 0.65 |
| F-measure | 0.83 | 0.65 |
| Accuracy | 0.71 | 0.48 |

Three caveats apply to every number in this document. First, the Choral Singing Dataset is part of multif0's training data, so its scores are optimistic and the gap is probably overstated (the next test should use Cantoría, which was not in training). Second, reference pitches come from running pYIN on isolated singer stems, so they contain tracker errors. Third, six mixtures from three songs is a small sample. Treat the results as a ranking signal, not as accuracy claims.

## Shortlist at a glance

License and last commit dates are from cloned repos (2026-10-21), not from README text.

| Candidate | Study in the SLR | License | Last commit | Stack | Pretrained weights | Fit for vocal ensembles | Verdict |
|---|---|---|---|---|---|---|---|
| [multif0-estimation-polyvocals](https://github.com/helenacuesta/multif0-estimation-polyvocals) | Cuesta 2020, cited by Schulze-Forster 2023 (Appendix A #255). Not itself in the 310 rows scanned | MIT | 2021-03-04 | Keras 2.3.1, TensorFlow 1.15, Python 3.6 (ported to Keras 3.15, Python 3.12) | Yes, 5 models in the repo (61 MB) | Built for choir and quartet audio. F-measure 0.83 on our tests | **First choice** |
| [timbre-trap](https://github.com/sony/timbre-trap) | Cwitkowitz 2024 (Appendix A #58) | MIT | 2024-05-05 | PyTorch, Python 3.10 or newer | Yes, 11 MB, on the Hugging Face Space | Instrument agnostic, vocals not evaluated. F-measure 0.65 on our tests | **Fallback** |
| [umss](https://github.com/schufo/umss) | Schulze-Forster 2023 (#255) | Apache-2.0 LICENSE file, but README says "All rights reserved" | 2023-03-19 | PyTorch 1.6, Python 3.7 or 3.8, conda | Yes, 2 models (171 MB) | Separates SATB voices, command line only | Stage 2 feature, clarify license |
| [MusicYOLO](https://github.com/itec-hust/MusicYOLO) | Wang 2023a (#305) | Apache-2.0 | 2022-01-29 | PyTorch 1.8, CUDA 10.2, YOLOX | Yes, but hosted on BaiduYun | Solo singing only | Not for ensembles |
| [YourMT3](https://github.com/mimbres/YourMT3) | Chang 2024 (#37) | GPL-3.0 | Not checked, last news item 2024-11 | PyTorch | Hugging Face demo and Colab | Transcribes vocals per the abstract | Copyleft, note output only |
| [cyolo_score_following](https://github.com/CPJKU/cyolo_score_following) | Henkel 2021 (#98, #99) | MIT | Not checked | PyTorch, conda | Yes | Not vocal, follows scores | Later, if we add score following |

## How the candidates were found

1. Located the SLR (*Intelligent Music Processing for Singing, Ensembles, and Instrumental Performance*, 365 studies) and parsed the Appendix A table of studies, which labels each with a domain, modality and topic cluster. 310 of the 365 rows parsed; about 55 multi line rows were skipped by my parser.
2. Filtered for ensemble and singing studies, then checked each for a code link on its paper page.
3. For every repository: cloned it, read the LICENSE file (not the README claim), took the last commit date from `git log`, checked whether pretrained weights are included, and read the dependency pins.
4. Ran the two viable ones (see [Test method](#test-method)).

## Candidate 1: multif0 (Cuesta et al., 2020)

**What it does.** It estimates every fundamental frequency (F0) sounding at each moment in a vocal ensemble recording. It does not say which singer is which.

**Method.** The input is a harmonic constant-Q transform (5 harmonics, 60 bins per octave so 20 cents per bin, 6 octaves from 32.7 Hz) plus its phase differentials, at 22,050 Hz with a 256 sample hop (about 11.6 ms per frame). A convolutional network outputs a pitch salience map of 360 bins per frame, and local peaks above a threshold become F0s. There are three variants: Early/Shallow, Early/Deep and Late/Deep. The authors recommend Late/Deep ("model3", threshold 0.5), which has about 1.25 million parameters. The pitch grid is 20 cents wide, so the output cannot resolve intonation finer than that without extra interpolation.

**Training data.** Mixtures of individual singers built from the Choral Singing Dataset (public), Dagstuhl ChoirSet (public), ESMUC Choir Dataset (now public under CC BY 4.0), Bach Chorales and Barbershop Quartets (both commercial, from pgmusic). Pitch shifting by up to 2 semitones and added reverb gave 22,910 files.

**Reported results (paper).**

| Test | Late/Deep | Best baseline |
|---|---|---|
| Barbershop Quartets, F-measure at 100 cents | 0.846 | 0.757 (VOCAL4-VA) |
| Barbershop Quartets, F-measure at 20 cents | 0.831 | 0.537 (MSINGERS) |
| Small outside choir dataset, F-measure | 0.704 | 0.653 |

Training with reverb improved F-measure by a little over 10% on reverberant test files. The authors say the outside choir set is very small and that unison and high reverb robustness need more data.

**Results on our real choir tests.** Mean over six clean mixtures: precision 0.75, recall 0.92, F-measure 0.83, accuracy 0.71. Range of F-measure per mixture: 0.78 to 0.89. It tends to report slightly more pitches than the references contain (about 2.6 to 3.3 per frame against 2.2 to 3.1), which explains precision being lower than recall. Details are in [Test results](#test-results).

**The repo.** MIT license, 184 commits, last commit 2021-03-04, 114 MB with weights. `predict_on_audio.py` takes one file or a folder and writes a tab separated file: one row per frame, with the time first and then the F0 values in Hz. The README does not document that format; it was read from the code. The per model thresholds in that script are 0.4, 0.5, 0.5 and 0.4 for models 1 to 4.

**What it needs.** The pinned stack (TensorFlow 1.15.4, Keras 2.3.1, NumPy 1.16.4) only runs on Python 3.7 or older. Our port avoids that; see [Backend prototype](#backend-prototype). The training scripts depend on data that is not public, so retraining is not reproducible. Inference only needs the shipped weights.

**Gaps for an MVP.** No per singer assignment (the paper lists it as future work), no real time mode, and fixed thresholds. The authors note that smoothing the output F0 contours improves continuity, which is easy to add.

## Candidate 2: Timbre-Trap (Cwitkowitz et al., 2024)

**What it does.** Instrument agnostic multipitch estimation: it finds which pitches are active over time without naming the instrument.

**Method.** A fully convolutional autoencoder, inspired by SoundStream, works on a complex constant-Q transform (60 bins per octave, 9 octaves starting near 21.5 Hz, 22,050 Hz, 3 second blocks). A switch channel in the latent space selects reconstruction or transcription. Training combines a transcription loss, a reconstruction loss and a consistency loss.

**Training data.** URMP only: 35 training pieces from a set of 44 (about 1.3 hours), which is instrument ensemble music, not choirs.

**Reported results (paper), frame level F1.**

| Test set | Timbre-Trap | Basic Pitch | Deep Salience |
|---|---|---|---|
| Bach10 | 82.6 | 82.9 | 71.3 |
| Su | 51.4 | 48.9 | 57.1 |
| GuitarSet | 60.2 | 76.2 | 72.7 |

The authors do not claim it beats existing methods, warn that the baselines are not directly comparable, and say it generalizes less well to guitar. Vocals are not addressed in the paper.

**Results on our real choir tests.** Mean over six clean mixtures: precision 0.67, recall 0.65, F-measure 0.65, accuracy 0.48. It misses more pitches than multif0 (it reports about 1.6 to 3.0 per frame against 2.2 to 3.1 in the references) and its score did not move when the threshold changed from 0.3 to 0.9. It degraded more gently under noise than multif0 at first (B01 F-measure 0.58 clean, 0.55 at 10 dB) but still fell to 0.44 at 0 dB.

**The repo.** MIT license, 60 commits, last commit 2024-05-05, 712 KB of code. `setup.py` requires Python 3.10 or newer. The base weights (`tt-orig.pt`, 11 MB) are in the project's [Hugging Face Space](https://huggingface.co/spaces/cwitkowitz/timbre-trap). Inference is `model.transcribe(audio)`. Output is 540 pitch bins at a much finer time step than multif0 (pooled by 4 frames before scoring). Speed on 2 CPU cores: 10 to 12 seconds for 30 seconds of audio when it ran alone.

**Gaps for an MVP.** No vocal evaluation and no choir training data. `requirements.txt` also lists `basic-pitch` and `tensorflow`, which were not needed for inference. It could be fine tuned on choir data, but that needs a labeled dataset and GPU time.

## Other candidates

**UMSS (Schulze-Forster et al., 2023).** Unsupervised separation of choir voices using differentiable source-filter models, trained without isolated stems. It takes F0 tracks as guidance, and the repo includes `preprocessing_multif0_cuesta.py` to get them from multif0. The code is PyTorch 1.6 with Python 3.7 or 3.8, run from the command line with no GUI, last commit 2023-03-19. The repo is 868 MB including a 339 MB Datasets folder and 171 MB of trained models. The license is unclear: the LICENSE file is Apache-2.0 but the README says "All rights reserved", so ask the author before reusing. It fits as a later feature (separating voices) once pitch tracking works. Its Datasets folder also contains the Choral Singing Dataset stems used for the real audio tests in this report.

**MusicYOLO (Wang et al., 2022).** Detects sung note onsets and offsets by treating the spectrogram as an image for a YOLOX object detector. It is Apache-2.0 but has only 4 commits, pins PyTorch 1.8 with CUDA 10.2, and hosts its weights on BaiduYun. The README tells you to clone `xk-wang/MusicYOLO`, a different account from the one hosting the repo. It handles solo singing, so it does not fit an ensemble MVP.

**YourMT3+ (Chang et al., 2024).** Multi-instrument transcription that, per its abstract, transcribes vocals directly. The repo has a Hugging Face demo and a Colab. The license is GPL-3.0, which would require anything derived from it to be GPL too. It outputs notes, not the per frame pitch tracks that intonation analysis needs. Not tested.

**cyolo_score_following (Henkel et al., 2021).** MIT licensed code that follows a performance through score sheet images, with pretrained models and no live demo. It is not vocal and not needed until we add score-informed features, which the SLR lists as a gap. Not tested.

## Test method

The comparison uses real singing, not synthetic tones. The UMSS repo ships Choral Singing Dataset (CSD) stems: one clean recording per singer for three songs (Locus Iste, El Rossinyol, Nino Dios). The test set was built from those. Scripts: [`eval/`](../eval). Step by step instructions: [EVALUATION_GUIDE.md](EVALUATION_GUIDE.md).

- **Mixtures.** B01 to B06 each combine one randomly chosen singer per part (soprano, alto, tenor, bass) from one song, a 30 second excerpt, resampled to 22,050 Hz and peak normalized. Songs: Locus Iste (B01, B04), El Rossinyol (B02, B05), Nino Dios (B03, B06).
- **References.** pYIN (librosa) on each isolated stem, 65 to 1047 Hz, hop 256, frames kept only if voiced probability was above 0.7. Where pYIN fails, the reference has gaps, which lowers measured precision.
- **Stress variants of B01.** White noise at 20, 10 and 0 dB signal to noise ratio (N20, N10, N00); reverb with a 1.2 second decay time (R12, and R12b on B04); and a detune test (DET, built from B02) with the alto 30 cents sharp and the bass 25 cents flat, with the references shifted to match.
- **Fewer voices.** P2 is soprano plus bass only, P3 is soprano, tenor and bass, both from B03.
- **Scoring.** mir_eval multipitch metrics at 50 cents, threshold 0.5 for both models. Timbre-Trap output was max pooled by 4 frames to bring it near the same time grid; mir_eval resampled the remaining difference.

An earlier, smaller check used one synthetic 6 second clip of four harmonic voices with vibrato at C3, G3, C4 and E4 (130.81, 196.00, 261.63, 329.63 Hz). Both models ran and found the pitches (multif0: every target detected in 100% of frames within 50 cents; Timbre-Trap: activation about 0.99 near each target). That only proves they run; it says nothing about accuracy on real choirs.

## Test results

**Clean mixtures (50 cent tolerance, threshold 0.5).**

| Mixture | multif0 P / R / F / Acc | Timbre-Trap P / R / F / Acc |
|---|---|---|
| B01 | 0.77 / 0.85 / 0.81 / 0.68 | 0.72 / 0.49 / 0.58 / 0.41 |
| B02 | 0.82 / 0.94 / 0.88 / 0.78 | 0.71 / 0.67 / 0.69 / 0.53 |
| B03 | 0.66 / 0.96 / 0.78 / 0.64 | 0.58 / 0.77 / 0.66 / 0.49 |
| B04 | 0.72 / 0.91 / 0.80 / 0.67 | 0.69 / 0.61 / 0.65 / 0.48 |
| B05 | 0.87 / 0.92 / 0.89 / 0.81 | 0.76 / 0.60 / 0.67 / 0.50 |
| B06 | 0.67 / 0.97 / 0.79 / 0.65 | 0.56 / 0.77 / 0.65 / 0.48 |

multif0 won every mixture. Scoring at 100 cents gave identical values to two decimals, so almost all matched estimates are already within 50 cents.

**Robustness (F-measure, with accuracy in brackets).**

| Condition | multif0 | Timbre-Trap |
|---|---|---|
| B01 clean | 0.81 (0.68) | 0.58 (0.41) |
| B01 with noise at 20 dB | 0.76 (0.62) | 0.58 (0.41) |
| B01 with noise at 10 dB | 0.67 (0.51) | 0.55 (0.38) |
| B01 with noise at 0 dB | 0.59 (0.41) | 0.44 (0.28) |
| B01 with reverb, 1.2 s | 0.81 (0.68) | 0.58 (0.41) |
| B04 clean | 0.80 (0.67) | 0.65 (0.48) |
| B04 with reverb, 1.2 s | 0.80 (0.66) | 0.61 (0.43) |
| B02 clean | 0.88 (0.78) | 0.69 (0.53) |
| B02 detuned (alto +30, bass -25 cents) | 0.88 (0.78) | 0.65 (0.48) |
| B03 soprano and bass only | 0.60 (0.43) | 0.48 (0.31) |
| B03 soprano, tenor and bass | 0.72 (0.56) | 0.58 (0.41) |

What this shows:

- **Noise.** multif0 loses recall first (0.85 clean to 0.42 at 0 dB) while precision rises, so it goes quiet rather than inventing pitches. The MVP should warn users about noisy recordings.
- **Reverb.** multif0 was essentially unaffected, consistent with its reverb augmented training. Timbre-Trap lost up to 0.04.
- **Detuning.** Neither model snapped to equal temperament. multif0's score did not change on the detuned mixture.
- **Fewer voices.** Both models over detect on sparse mixtures. For P2 the references average only 0.76 pitches per frame while multif0 reports 1.57, so precision (0.45) is low. Part of that is pYIN gaps in the references and part may be real false alarms such as octave errors; the two were not separated.

**Pitch accuracy of matched estimates (B01, multif0, mean absolute error in cents).** Soprano 11.8, alto 10.5, tenor 7.0, bass 5.9. For the detuned B02 variant the errors were 7.5, 7.3, 8.1 and 8.7 against the shifted references, so the model follows the actual pitch of an out of tune singer. Timbre-Trap's errors were larger on the same material (B01: 15.7, 15.6, 10.5, 14.0). Because multif0 outputs on a 20 cent grid, treat errors below about 10 cents as unresolved. An intonation display needs interpolation between bins first.

**Threshold sweep (mean F-measure over B01 to B06).**

| Threshold | multif0 F / P / R | Timbre-Trap F |
|---|---|---|
| 0.3 | 0.81 / 0.72 / 0.94 | 0.65 |
| 0.5 | 0.83 / 0.75 / 0.92 | 0.65 |
| 0.7 | 0.83 / 0.78 / 0.90 | 0.65 |

Raising multif0's threshold trades a little recall for precision. 0.5 to 0.7 is a sensible range and should be a user setting. Timbre-Trap is insensitive to it in this range.

**Speed (2 CPU cores, 30 second clips).** multif0 takes about 20 to 22 seconds when running alone (feature extraction 2 seconds, network the rest), so roughly 0.7 times real time. Timbre-Trap takes 10 to 12 seconds alone. Some timings of 40 to 80 seconds came from both models competing for the same two cores and should be ignored. A GPU would cut both sharply.

**Limits of these tests.** Six mixtures from three songs; the references are pYIN output, not human annotation; the noise and reverb are synthetic (the reverb is an exponentially decaying noise impulse response); the CSD recordings are in multif0's training data but not in Timbre-Trap's.

## Datasets for further testing

| Dataset | What it is | Licence and access | Note for us |
|---|---|---|---|
| [Choral Singing Dataset](https://zenodo.org/record/1286485) | Three SATB pieces, one recording per singer | Licence not confirmed | Used for our tests. In multif0's training data |
| [Dagstuhl ChoirSet](https://zenodo.org/record/3897181) | Multitrack choir recordings with annotations | Public on Zenodo | In multif0's training data |
| [ESMUC Choir Dataset](https://zenodo.org/record/5848989) | Choir recordings | CC BY 4.0, public since January 2022 (the multif0 paper called it proprietary at the time) | In multif0's training data |
| [Cantoría](https://zenodo.org/record/5878677) | Vocal quartet recordings | Licence not stated on the page read | Not in multif0's training data, so the fairest next test |

Zenodo blocked downloads from the environment used for these tests, so the next test needs someone to download Cantoría on their own machine. Record numbers come from the Chandna et al. data availability statement; the paper's footnotes give different numbers for ESMUC and Cantoría, so check each link.

## Backend prototype

The port was turned into a small service so the back end work starts from something that runs. See [BACKEND_GUIDE.md](BACKEND_GUIDE.md) for setup and the full API. It has two files: a module that builds the Keras 3 model, loads the shipped weights by layer name, computes the features with pumpp, and picks peaks; and a FastAPI app with `GET /health` and `POST /transcribe`.

- **Request.** `POST /transcribe?threshold=0.5` with the audio file as multipart form data.
- **Response.** JSON with `sample_rate`, `hop_s`, `threshold`, `n_frames`, `process_s` and a `frames` list of `{t, f0: [Hz, ...]}`. A 30 second clip is 2,583 frames and about 100 KB of JSON.
- **Tested.** Model loads in about 5 seconds at startup. One 30 second request took 22 seconds end to end on 2 CPU cores. A text file upload correctly returned 415. A cross origin preflight request returned the expected CORS header.
- **Not done.** No Docker image, no chunking of long files (the model runs in 5,000 frame blocks, about 58 seconds each, without overlap, so boundary effects are untested), no authentication, no concurrency handling, and no check against the original TensorFlow 1.15 outputs. The port agreed with ground truth on real audio, which is the evidence that the weights loaded correctly.

## On-topic studies with no released code found

These ensemble studies in the SLR have no code link on the pages that were opened. That does not prove no repo exists: paper pages were read, not authors' full GitHub lists, and GitHub's own listing pages blocked the fetches.

| Study | Task | What I found |
|---|---|---|
| Chandna et al. 2022, choral source separation (#36) | Separating choir voices | Data availability statement lists datasets only, no code |
| Cuesta and Gómez 2022, voice assignment in vocal quartets (#57) | Assigning detected pitches to singers | No code link on the journal page that could be opened |
| Sarkar et al. 2021, vocal harmony separation (#247) | Separating four part a cappella | Interspeech page has no code or demo link |
| Lanzendörfer et al. 2026, SepACap (#150) | Separating a cappella singers | Links only the Mel-Band RoFormer baseline, not its own code |

## MVP build outline

The MVP lets a user upload a choir recording and see every sung pitch over time, with how far each is from the nearest note in cents. It is offline analysis, not live.

1. **Upload.** The front end sends an audio file to the back end.
2. **Prepare.** The back end resamples to 22,050 Hz. For long files it should run the model in blocks of about 30 seconds with a few seconds of overlap (not built yet).
3. **Estimate.** multif0 returns a 360 bin salience map per frame.
4. **Pick peaks.** Keep peaks above a threshold (default 0.5, user adjustable up to about 0.7), then smooth the contours, as the paper's authors suggest.
5. **Refine pitch.** Interpolate around each peak bin to get below the 20 cent grid. This is untested and is the first thing to try if the cents display looks jumpy.
6. **Return.** The back end sends JSON: a time and a list of F0 values in Hz for each frame.
7. **Display.** The front end draws pitch tracks on a scrolling canvas and shows note name and cents offset.

**Suggested split (for the group to confirm).** Back end: wrap the prototype in Docker, add block processing with overlap, add a job queue because one 30 second clip takes about 22 seconds on 2 CPU cores. Front end: the pitch trace display and the threshold control. Source handoff (research author): the ported model, the API code and the test scripts, plus the Cantoría test and the UMSS license question. See [DECISIONS_AND_NEXT_STEPS.md](DECISIONS_AND_NEXT_STEPS.md) for the full checklist.

**Reusable front end code.** The group's own MuTech dashboard already has a canvas renderer, a frequency to screen mapping and a frequency to note and cents function in TypeScript, so it could be reused if the group agrees.

**Limits to state up front.** The output is an unordered set of pitches per frame, not one track per singer. Per singer tracks would need voice assignment (no code found) or UMSS separation. Neither repo claims real time operation. Quality drops on noisy recordings (F-measure 0.59 at 0 dB noise against 0.81 clean).

## Risks and open questions

- **Does multif0 count as "from the studies in the paper"?** It is the companion model cited by Schulze-Forster 2023 (in the SLR) and the basis of Cuesta and Gómez 2022 (in the SLR), but the 2020 paper itself was not among the 310 table rows scanned. If it must be one of the 365, Timbre-Trap qualifies directly. Ask the project lead or supervisor.
- **The accuracy numbers are optimistic for multif0.** The Choral Singing Dataset is in its training data. Run both models on Cantoría before presenting a number to anyone as the MVP's accuracy.
- **Reference quality.** Test references come from pYIN, not human annotation, so some "errors" are the reference's. Dagstuhl ChoirSet and Cantoría have annotations that would be better.
- **The port is not verified against the original.** It loads all 33 layers and works on real audio, but the original TensorFlow 1.15 code could not be run to compare outputs frame by frame.
- **Pitch resolution.** The model outputs a 20 cent grid. Intonation work finer than about 10 cents needs interpolation, and that is untested.
- **Noise.** Recall drops fast with background noise (0.85 clean, 0.42 at 0 dB for B01). Tell users to upload clean recordings.
- **Over detection on few voices.** With two or three singers the model reports extra pitches, so precision falls (0.45 on the two voice test, partly due to reference gaps).
- **Compute.** About 22 seconds of CPU time per 30 second clip. Hosting needs a queue or a GPU.
- **Training data is partly commercial.** The weights are in an MIT repo, but they were trained on pgmusic (commercial) material along with public sets. Confirm with the author before redistributing the weights in a product. ESMUC, earlier described as proprietary, is now CC BY 4.0.
- **Licenses.** UMSS has conflicting LICENSE and README text. YourMT3 is GPL-3.0.
- **Scope of the scan.** 310 of the 365 rows of the SLR's appendix table were read (the parser skipped about 55 multi line rows) and not every paper's full text was read, which the SLR itself says is needed to find released artifacts.
- **Maintenance.** multif0 has had no commits since March 2021 and Timbre-Trap none since May 2024. Neither should be expected to receive fixes.

## Sources

Repos were cloned and inspected on 2026-10-21. Papers and pages below were opened.

- [multif0-estimation-polyvocals (GitHub)](https://github.com/helenacuesta/multif0-estimation-polyvocals)
- [Cuesta, McFee, Gómez 2020, Multiple F0 Estimation in Vocal Ensembles using CNNs (arXiv)](https://arxiv.org/abs/2009.04172)
- [timbre-trap (GitHub)](https://github.com/sony/timbre-trap)
- [Cwitkowitz et al. 2024, Timbre-Trap (arXiv)](https://arxiv.org/abs/2309.15717)
- [Timbre-Trap weights and demo (Hugging Face Space)](https://huggingface.co/spaces/cwitkowitz/timbre-trap)
- [umss (GitHub)](https://github.com/schufo/umss)
- [Schulze-Forster et al., Unsupervised Music Source Separation (arXiv)](https://arxiv.org/abs/2201.09592)
- [MusicYOLO (GitHub)](https://github.com/itec-hust/MusicYOLO)
- [YourMT3 (GitHub)](https://github.com/mimbres/YourMT3)
- [YourMT3+ (arXiv)](https://arxiv.org/abs/2407.04822)
- [cyolo_score_following (GitHub)](https://github.com/CPJKU/cyolo_score_following)
- [Chandna et al. 2022, choral ensembles (Frontiers)](https://www.frontiersin.org/journals/signal-processing/articles/10.3389/frsip.2022.808594/full)
- [Sarkar et al. 2021 (Interspeech)](https://www.isca-archive.org/interspeech_2021/sarkar21_interspeech.html)
- [Lanzendörfer et al. 2026, SepACap (arXiv)](https://arxiv.org/abs/2509.26580)
- [Dagstuhl ChoirSet (arXiv 1904.05086)](https://arxiv.org/abs/1904.05086)
- [mir_eval multipitch metrics (documentation)](https://mir-eval.readthedocs.io/latest/api/multipitch.html)
- [librosa pYIN (documentation)](https://librosa.org/doc/latest/generated/librosa.pyin.html)
- The four dataset pages linked in "Datasets for further testing"
