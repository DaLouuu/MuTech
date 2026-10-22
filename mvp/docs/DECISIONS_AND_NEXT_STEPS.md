# Decisions and next steps

## 1. Decisions made so far

| # | Decision | Why | Revisit if |
|---|---|---|---|
| 1 | Base the MVP on **multif0** (Cuesta et al., 2020) | Only candidate built for choirs and vocal quartets; MIT license; ships pretrained weights; scored F-measure 0.83 against 0.65 for Timbre-Trap on our tests | Cantoría (unseen data) shows a much smaller or reversed gap |
| 2 | Keep **Timbre-Trap** (Cwitkowitz et al., 2024) as the fallback | MIT, runs unmodified on current Python, about twice as fast, and it is directly one of the studies in the SLR | multif0's port turns out unreliable |
| 3 | **Port** multif0 to Python 3.12 / Keras 3 instead of recreating a Python 3.6 environment | Python 3.6/3.7 and TensorFlow 1.15 are not installable on current systems | Someone can run the original and shows the port differs |
| 4 | Serve through a **FastAPI** web API | Small, auto generates docs, easy for a separate front end to call | Group prefers another stack |
| 5 | MVP scope is **offline analysis** of an uploaded recording, showing pitches and cents offset | Neither model claims real time operation; per singer tracks are not available | Group wants live feedback (a different project) |
| 6 | UMSS (voice separation) is a **later** feature, not the base | Command line only, old PyTorch, unclear license | License is clarified and there is time |

## 2. Open questions (need an answer from someone)

| Question | Who | Why it matters |
|---|---|---|
| Must the MVP's base come from one of the **365 studies** in the SLR? multif0 (2020) is cited by studies in the SLR and is the foundation of Cuesta and Gómez 2022 (in the SLR), but I did not find the 2020 paper itself among the 310 appendix rows I could parse | Project lead / supervisor | If yes, Timbre-Trap qualifies directly and becomes the base, which changes the recommendation |
| May we redistribute the multif0 weights in our product? They are in an MIT repo, but were trained partly on commercial (pgmusic) recordings | Author (Helena Cuesta) via email or GitHub issue | Matters if the MVP is published or shared outside the class |
| UMSS license: the LICENSE file says Apache-2.0, the README says "All rights reserved" | Author (Schulze-Forster) | Needed before using UMSS |
| Where will the back end be hosted, and does it have a GPU? | Back end owner | Decides whether a job queue is mandatory (CPU: about 0.7x real time) |
| What does "done" look like for the MVP: demo on a recording, or something others can use? | Group | Decides how much of the "not built" list in the back end guide is needed |

## 3. Work breakdown

Suggested split (for the group to confirm). Checkboxes show what exists today.

### Back end
- [x] Model port and API prototype ([BACKEND_GUIDE.md](BACKEND_GUIDE.md))
- [ ] Reproduce the prototype on the group's machine / server using the quick start
- [ ] Docker image
- [ ] Process long files in overlapping blocks
- [ ] Job queue or thread pool so requests do not block each other
- [ ] Set `CORS_ORIGINS`, add authentication and a rate limit if public
- [ ] Parabolic interpolation of peaks for finer pitch (test against the DET mixture)
- [ ] Optional: link pitches across frames into tracks
- [ ] Optional: smooth contours (the multif0 authors recommend it)

### Front end
- [ ] Build the pitch trace display from a saved sample response ([FRONTEND_GUIDE.md](FRONTEND_GUIDE.md))
- [ ] Note name and cents tooltip
- [ ] Upload, spinner, sensitivity slider
- [ ] Minimum duration filter for cleaner traces
- [ ] A limits note visible to users (unordered pitches, noise sensitivity, 20 cent grid)

### Research and evaluation
- [x] Candidate search and shortlist ([RESEARCH_REPORT.md](RESEARCH_REPORT.md))
- [x] Evaluation on 14 real choir mixtures ([EVALUATION_GUIDE.md](EVALUATION_GUIDE.md))
- [ ] Download Cantoría and run both models on it (unseen data for multif0)
- [ ] Ask the project lead or supervisor the "must be one of the 365" question
- [ ] Email the multif0 and UMSS authors about licenses
- [ ] Scan the remaining ~55 appendix rows my parser skipped
- [ ] Task 2 (review of the whole SLR) is separate and not covered here

## 4. If something goes wrong

| Problem | Fallback |
|---|---|
| Port misbehaves in some environment | Use Timbre-Trap (`eval/tt_estimate.py` shows how to load and run it, `model.transcribe(audio)`) |
| multif0 weights cannot be redistributed | Keep them out of the repo (already the case) and have users clone the original repo; or switch the base to Timbre-Trap |
| Server too slow | Shorten the allowed upload length, add the queue, or move to a machine with a GPU |
| Group needs per singer lines | Pitch tracking first (link pitches across frames); true voice assignment is the research topic of Cuesta and Gómez 2022 and no code was found for it |

## 5. Handoff checklist (source handed from the research author to the group)

- [x] Source code in this folder: `backend/`, `eval/`
- [x] Documentation: this `docs/` folder
- [x] Pinned requirements
- [ ] Someone other than the author has run the quick start end to end on a clean machine (**not yet done; treat the first person to try it as the test**)
