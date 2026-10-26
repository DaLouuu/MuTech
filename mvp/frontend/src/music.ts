const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

export interface NotePitch {
  name: string;
  cents: number;
  midi: number;
}

export function hzToNote(hz: number, a4 = 440): NotePitch | null {
  if (!Number.isFinite(hz) || hz <= 0) return null;
  const midi = 69 + 12 * Math.log2(hz / a4);
  const nearest = Math.round(midi);
  const noteIndex = ((nearest % 12) + 12) % 12;
  return {
    name: `${NOTE_NAMES[noteIndex]}${Math.floor(nearest / 12) - 1}`,
    cents: Math.round(100 * (midi - nearest)),
    midi,
  };
}

export function formatCents(cents: number): string {
  return `${cents > 0 ? "+" : ""}${cents} cents`;
}
