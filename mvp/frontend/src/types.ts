export interface PitchFrame {
  t: number;
  f0: number[];
}

export interface TranscriptionResponse {
  sample_rate: number;
  hop_s: number;
  threshold: number;
  n_frames: number;
  process_s?: number;
  duration_s?: number;
  frames: PitchFrame[];
}
