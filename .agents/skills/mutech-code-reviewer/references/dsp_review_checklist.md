# DSP & MIR Review Checklist for MuTech

This checklist is used when reviewing audio processing, multi-pitch estimation, contour tracking, harmonic detection, and MIDI synthesis in the MuTech codebase.

---

## 1. Audio Preprocessing (`audio_processor.py`)
- [ ] **Sample Rate Consistency**: Input audio must be consistently resampled to $16,000\text{ Hz}$ or $22,050\text{ Hz}$ depending on model specifications. Check that resampling filters avoid aliasing.
- [ ] **Mono Downmixing**: Multi-channel inputs (Stereo, 5.1) must downmix via mean across channels: $x_{\text{mono}} = \frac{1}{C}\sum_{c=1}^C x_c$. Check that downmixing does not cause clipping (verify max amplitude $\le 1.0$).
- [ ] **DC Bias & Sub-bass Rumble**: 30 Hz Butterworth highpass filter (order $\ge 2$) must be applied to eliminate DC offset, stage rumble, and microphone plosives before spectral analysis.
- [ ] **RMS Normalization**: Peak and RMS scaling must guard against complete silence:
  $$\text{RMS} = \sqrt{\frac{1}{N}\sum x[n]^2 + \epsilon}$$
  If signal RMS is below silence floor (e.g. $-60\text{ dBFS}$), skip normalization to prevent amplifying background noise.

---

## 2. Multi-Pitch Inference & Interpolation (`mf0_service.py`, `dsp_utils.py`)
- [ ] **Parabolic Interpolation Formula**:
  For peak bin $k$ with neighboring bin activations $\alpha = A[k-1]$, $\beta = A[k]$, $\gamma = A[k+1]$:
  $$\text{denom} = 2 \cdot (\alpha - 2\beta + \gamma)$$
  $$\Delta = \frac{\alpha - \gamma}{\text{denom}} \quad \text{where } |\text{denom}| > 10^{-7}$$
  Ensure $\Delta$ is clamped to $[-0.5, 0.5]$ before computing continuous pitch:
  $$f = f_{\text{min}} \cdot 2^{(k + \Delta) / \text{bins\_per\_octave}}$$
- [ ] **Hann Window Overlap-Add**:
  When processing audio in chunks of length $L$ with overlap $M$:
  Ensure cross-fade margins use valid Hann half-windows:
  $$w_{\text{fade\_in}}[m] = \sin^2\left(\frac{\pi m}{2M}\right), \quad w_{\text{fade\_out}}[m] = \cos^2\left(\frac{\pi m}{2M}\right)$$
  Check that $w_{\text{fade\_in}} + w_{\text{fade\_out}} \equiv 1.0$ at all overlap indices.

---

## 3. Trajectory Linking & Voice Assignment (`contour_tracker.py`)
- [ ] **Cents-Time Cost Matrix**:
  Distance between candidate pitch point $(t_j, f_j)$ and existing trajectory tip $(t_i, f_i)$:
  $$\Delta t = t_j - t_i, \quad \Delta c = 1200 \cdot |\log_2(f_j / f_i)|$$
  Cost should reject links where $\Delta t > 25\text{ ms}$ or $\Delta c > 80\text{ cents}$.
- [ ] **Dropout Bridging**:
  Contour linker should allow bridging brief dropouts (e.g. up to 3 consecutive frames / $\sim 30\text{ ms}$) without terminating the voice track prematurely.
- [ ] **SATB Tessitura Partitioning**:
  Typical vocal ranges (in Hz):
  - Soprano: $C4 \approx 261.6\text{ Hz}$ to $C6 \approx 1046.5\text{ Hz}$
  - Alto: $F3 \approx 174.6\text{ Hz}$ to $F5 \approx 698.5\text{ Hz}$
  - Tenor: $C3 \approx 130.8\text{ Hz}$ to $A4 \approx 440.0\text{ Hz}$
  - Bass: $E2 \approx 82.4\text{ Hz}$ to $E4 \approx 329.6\text{ Hz}$
- [ ] **Strict Non-Crossing Invariant**:
  At any discrete frame $t$, if $K$ voices are actively singing, their instantaneous pitches must satisfy:
  $$f_{\text{Bass}}(t) \le f_{\text{Tenor}}(t) \le f_{\text{Alto}}(t) \le f_{\text{Soprano}}(t)$$
  Any assignment that permits voice crossing within the same timestamp must be sorted and re-indexed.

---

## 4. Choral Intonation & Vibrato Analytics (`analytics.py`)
- [ ] **Vibrato Detection**:
  - Modulating rate: $5.0\text{ Hz} \le f_{\text{vib}} \le 7.5\text{ Hz}$.
  - Extent: $20\text{ cents} \le \text{extent} \le 100\text{ cents}$ peak-to-peak.
  - Reject sensor noise: oscillations with frequency $>10\text{ Hz}$ or extent $<10\text{ cents}$ are measurement jitter, not vocal vibrato.
- [ ] **Cumulative Tuning Drift**:
  - Measured relative to initial tonic or rolling reference pitch:
    $$\text{drift}(t) = \text{median}_{k}(c_k(t) - c_k(0))$$
  - Guard against octave jump errors when unwrapping pitch drift.

---

## 5. MIDI Exporter (`midi_exporter.py`)
- [ ] **Type 1 Multi-Track Format**:
  - Track 0: Conductor track (Tempo = 120 BPM, Time Signature = 4/4).
  - Tracks 1–4: Individual voice parts (Soprano, Alto, Tenor, Bass).
- [ ] **Pitch Bend Sensitivity**:
  - Default pitch bend range: $\pm 2$ semitones ($\pm 200$ cents).
  - Raw 14-bit pitch bend value:
    $$\text{bend\_value} = 8192 + \text{round}\left(\frac{\Delta c}{200} \cdot 8191\right)$$
  - Ensure $\text{bend\_value}$ is clamped to $[0, 16383]$.
