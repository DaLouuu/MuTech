# Glossary

Plain language definitions of terms used in these docs.

| Term | Meaning |
|---|---|
| **MIR** | Music Information Retrieval: getting information out of music audio with software |
| **SLR** | Systematic literature review. Ours covers 365 studies on intelligent music processing for singing, ensembles and instrumental performance |
| **MVP** | Minimum viable product: the smallest working version that shows the idea |
| **F0 / fundamental frequency** | The lowest frequency of a sung or played note, in Hz. It is what we hear as the pitch |
| **Multi-F0 estimation** | Finding all the fundamental frequencies sounding at the same time (a chord, a choir) |
| **Frame** | A short slice of audio analysed at once. Here one frame every 11.6 ms |
| **Hz** | Cycles per second. A4 is 440 Hz |
| **Cent** | One hundredth of a semitone. 100 cents = 1 semitone, 1200 cents = 1 octave. Singers are normally judged within about ±20 to 50 cents |
| **Semitone** | The smallest step on a piano (C to C#) |
| **Octave error** | The model reports a pitch twice or half the real frequency |
| **SATB** | Soprano, alto, tenor, bass: the four voice parts of a standard choir |
| **Stem** | A recording of one singer or instrument on its own |
| **Mixture** | Several stems added together |
| **Constant-Q transform (CQT)** | A way of turning audio into a picture of energy by pitch over time, with bins spaced evenly in musical pitch |
| **Harmonic CQT (HCQT)** | CQT stacked with versions at 2x, 3x, 4x, 5x frequency, because a note's overtones reinforce its pitch |
| **Phase differential** | A measure of how the phase of each frequency changes over time. It helps the model locate pitch precisely |
| **Salience map / activation** | The model's output: for every frame and pitch bin, a number from 0 to 1 for "how likely is a pitch here" |
| **Threshold** | Minimum activation for a peak to count as a pitch. Higher = stricter |
| **Peak picking** | Choosing the local maxima along the pitch axis of a salience map |
| **Pitch grid / bins** | The model can only say a pitch is in one of 360 slots, 20 cents apart |
| **Interpolation** | Estimating a value between two grid slots, giving finer resolution than the grid |
| **Precision / Recall / F-measure / Accuracy** | See [EVALUATION_GUIDE.md](EVALUATION_GUIDE.md#1-what-is-measured) |
| **mir_eval** | Standard Python library for scoring music analysis outputs |
| **pYIN** | A well known single voice pitch tracker. We use it on solo stems to create reference pitches |
| **Pretrained weights** | The numbers a neural network learned during training, saved so others can use the model without training |
| **Port** | Re-implementing code to run on newer software while keeping the behaviour. Here: Keras 2 / TensorFlow 1.15 to Keras 3 |
| **Keras / TensorFlow / PyTorch** | Software libraries for neural networks |
| **FastAPI** | Python library for building web APIs |
| **CORS** | Browser security rule that blocks a web page from calling a server on another address unless the server allows it |
| **CSD** | Choral Singing Dataset: recordings of choir singers, one at a time |
| **Dagstuhl ChoirSet, ESMUC Choir Dataset, Cantoría** | Other public choir datasets (see the research report) |
| **URMP** | A dataset of instrument ensemble recordings. Timbre-Trap was trained on it |
| **Intonation** | How accurately a singer hits the intended pitch |
| **Voice assignment** | Deciding which detected pitch belongs to which singer. Not solved by our MVP |
| **UMSS** | Unsupervised Music Source Separation: a method that splits a choir recording into separate voices |
| **Real time factor** | Processing time divided by audio length. 0.7 means a 10 second clip takes 7 seconds |
