import { formatCents, hzToNote } from "./music";
import type { PitchFrame, TranscriptionResponse } from "./types";

export const MIDI_MIN = 24;
export const MIDI_MAX = 96;
export const ROW_HEIGHT = 24;
export const DEFAULT_MIDI_TOP = 84;
export const DEFAULT_MIDI_BOTTOM = 48;
export const DEFAULT_VIEW_HEIGHT = (DEFAULT_MIDI_TOP - DEFAULT_MIDI_BOTTOM + 1) * ROW_HEIGHT;
const LEFT = 94;
const RIGHT = 18;
const TOP = 12;
const BOTTOM = 12;
const SHARP_NOTES = new Set([1, 3, 6, 8, 10]);

interface PlotPoint {
  x: number;
  y: number;
  frame: PitchFrame;
  frequency: number;
  noteName: string;
  cents: number;
}

interface DetectedPitch extends PlotPoint {
  midi: number;
  time: number;
}

interface NoteSegment {
  noteMidi: number;
  start: number;
  end: number;
}

interface ActiveNoteSegment extends NoteSegment {
  meanMidi: number;
  lastTime: number;
  count: number;
}

interface ContourPoint {
  midi: number;
  time: number;
}

interface PitchContour {
  points: ContourPoint[];
}

export function getResultDuration(result: TranscriptionResponse): number {
  const lastFrameTime = result.frames.at(-1)?.t ?? 0;
  return Math.max(
    result.duration_s ?? 0,
    result.n_frames * result.hop_s,
    lastFrameTime + result.hop_s,
    result.hop_s,
  );
}

export function getPitchChartHeight(): number {
  return TOP + (MIDI_MAX - MIDI_MIN + 1) * ROW_HEIGHT + BOTTOM;
}

export function setDefaultPitchView(scroll: HTMLElement): void {
  if (scroll.clientHeight >= DEFAULT_VIEW_HEIGHT) {
    scroll.scrollTop = rowTop(DEFAULT_MIDI_TOP);
  } else {
    centerMidiInScroll(scroll, 60);
  }
}

export function centerMidiInScroll(scroll: HTMLElement, midi: number): void {
  const midiY = TOP + (MIDI_MAX - midi) * ROW_HEIGHT + ROW_HEIGHT / 2;
  scroll.scrollTop = Math.max(0, midiY - scroll.clientHeight / 2);
}

export function playheadXForTime(width: number, time: number, duration: number): number {
  const plotWidth = Math.max(1, width - LEFT - RIGHT);
  return LEFT + (Math.max(0, Math.min(time, duration)) / duration) * plotWidth;
}

export function chartTimeAtClientX(
  canvas: HTMLCanvasElement,
  clientX: number,
  duration: number,
): number | null {
  const rect = canvas.getBoundingClientRect();
  const x = clientX - rect.left;
  const plotWidth = rect.width - LEFT - RIGHT;
  if (x < LEFT || x > LEFT + plotWidth || plotWidth <= 0 || duration <= 0) return null;
  return ((x - LEFT) / plotWidth) * duration;
}

export function drawTimeAxis(
  canvas: HTMLCanvasElement,
  duration: number,
): void {
  const context = prepareCanvas(canvas, 44);
  const width = canvas.clientWidth;
  const height = 44;
  const plotWidth = Math.max(1, width - LEFT - RIGHT);
  const tickStep = getTimeTickStep(duration, plotWidth);
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#f4f3ef";
  context.fillRect(0, 0, LEFT, height);
  context.fillStyle = "#faf9f6";
  context.fillRect(LEFT, 0, plotWidth, height);
  context.fillStyle = "#34384b";
  context.font = "600 10px 'DM Sans', sans-serif";
  context.textBaseline = "middle";

  for (let time = 0; time <= duration; time += tickStep) {
    const x = playheadXForTime(width, time, duration);
    context.strokeStyle = "#d9d8d1";
    context.beginPath();
    context.moveTo(x, 0);
    context.lineTo(x, height);
    context.stroke();
    context.fillStyle = "#6e7180";
    context.textAlign = time === 0 ? "left" : "center";
    context.fillText(formatTime(time), time === 0 ? x + 3 : x, height / 2);
  }
  context.strokeStyle = "#c8c7c1";
  context.beginPath();
  context.moveTo(LEFT - 1, 0);
  context.lineTo(LEFT - 1, height);
  context.stroke();
}

export function drawPitchChart(
  canvas: HTMLCanvasElement,
  tooltip: HTMLDivElement,
  result: TranscriptionResponse,
  duration: number,
  showRawDetections: boolean,
): void {
  const contentHeight = getPitchChartHeight();
  const context = prepareCanvas(canvas, contentHeight);
  const width = canvas.clientWidth;
  const plotWidth = Math.max(1, width - LEFT - RIGHT);
  const plotHeight = contentHeight - TOP - BOTTOM;
  const tickStep = getTimeTickStep(duration, plotWidth);
  const pitchScroll = canvas.closest<HTMLElement>(".pitch-scroll");
  const chartWrap = canvas.closest<HTMLElement>(".chart-wrap");
  const { detections, segments, contours } = preparePitchData(result, duration, width);

  context.clearRect(0, 0, width, contentHeight);
  context.fillStyle = "#f4f3ef";
  context.fillRect(0, 0, LEFT, contentHeight);
  context.fillStyle = "#fbfaf7";
  context.fillRect(LEFT, TOP, plotWidth, plotHeight);

  for (let midi = MIDI_MIN; midi <= MIDI_MAX; midi += 1) {
    const y = midiY(midi);
    const pitchClass = midi % 12;
    const isSharp = SHARP_NOTES.has(pitchClass);
    const rowTop = y - ROW_HEIGHT / 2;
    context.fillStyle = isSharp ? "#ececf0" : "#fbfaf7";
    context.fillRect(LEFT, rowTop, plotWidth, ROW_HEIGHT);

    context.fillStyle = "#fff";
    context.fillRect(5, rowTop, LEFT - 12, ROW_HEIGHT);
    context.strokeStyle = "#c9c8c3";
    context.lineWidth = 0.7;
    context.strokeRect(5, rowTop, LEFT - 12, ROW_HEIGHT);

    const label = hzToNote(440 * 2 ** ((midi - 69) / 12))?.name.replace("#", "♯") ?? "";
    if (isSharp) {
      context.fillStyle = "#34384b";
      context.beginPath();
      context.roundRect(5, rowTop + 1, LEFT - 23, ROW_HEIGHT - 2, 3);
      context.fill();
      context.fillStyle = "#fff";
    } else {
      context.fillStyle = "#424656";
    }
    context.font = "600 10px 'DM Sans', sans-serif";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(label, (LEFT - 2) / 2, y);

    context.strokeStyle = isSharp ? "#d7d7de" : "#e6e4de";
    context.beginPath();
    context.moveTo(LEFT, rowTop);
    context.lineTo(width - RIGHT, rowTop);
    context.stroke();
  }

  for (let time = 0; time <= duration; time += tickStep) {
    const x = playheadXForTime(width, time, duration);
    context.strokeStyle = "#e3e1dc";
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(x, TOP);
    context.lineTo(x, contentHeight - BOTTOM);
    context.stroke();
  }

  if (showRawDetections) drawRawDetections(context, detections);
  drawContours(context, contours, width, duration);
  drawNoteSegments(context, segments, width, duration);

  canvas.onpointermove = (event: PointerEvent) => {
    const rect = canvas.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top + (pitchScroll?.scrollTop ?? 0);
    let nearest: PlotPoint | undefined;
    let nearestDistance = 16;

    for (const point of detections) {
      const distance = Math.hypot(point.x - pointerX, point.y - pointerY);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    }

    if (!nearest || !chartWrap) {
      tooltip.hidden = true;
      return;
    }

    tooltip.textContent = `${nearest.noteName} · ${formatCents(nearest.cents)} · ${nearest.frame.t.toFixed(2)} s · ${nearest.frequency.toFixed(1)} Hz`;
    tooltip.hidden = false;
    const wrapRect = chartWrap.getBoundingClientRect();
    tooltip.style.left = `${Math.min(wrapRect.width - 230, Math.max(8, event.clientX - wrapRect.left + 12))}px`;
    tooltip.style.top = `${Math.max(50, event.clientY - wrapRect.top - 42)}px`;
    canvas.setAttribute(
      "aria-label",
      `Pitch trace. Selected ${nearest.noteName} ${formatCents(nearest.cents)} at ${nearest.frame.t.toFixed(2)} seconds.`,
    );
  };

  canvas.onpointerleave = () => {
    tooltip.hidden = true;
    canvas.setAttribute("aria-label", "Pitch trace over time");
  };
}

function preparePitchData(
  result: TranscriptionResponse,
  duration: number,
  width: number,
): { detections: DetectedPitch[]; segments: NoteSegment[]; contours: PitchContour[] } {
  const orderedFrames = result.frames
    .filter((frame) => Number.isFinite(frame.t) && frame.t >= 0 && frame.t <= duration)
    .sort((left, right) => left.t - right.t);
  const times = orderedFrames.map((frame) => frame.t);
  const nominalStep = medianPositiveDelta(times) || result.hop_s;
  const frames = orderedFrames.map((frame, orderedIndex) => {
    const nextTime = times[orderedIndex + 1];
    const frameDuration =
      nextTime !== undefined && nextTime > frame.t
        ? Math.min(nextTime - frame.t, nominalStep * 1.5)
        : nominalStep;
    return { frame, frameDuration };
  });
  const detections: DetectedPitch[] = [];

  for (const { frame } of frames) {
    for (const frequency of frame.f0) {
      const note = hzToNote(frequency);
      if (!note || note.midi < MIDI_MIN || note.midi > MIDI_MAX) continue;
      detections.push({
        x: playheadXForTime(width, frame.t, duration),
        y: midiY(note.midi),
        frame,
        frequency,
        noteName: note.name.replace("#", "♯"),
        cents: note.cents,
        midi: note.midi,
        time: frame.t,
      });
    }
  }

  return {
    detections,
    segments: buildNoteSegments(frames, duration, nominalStep),
    contours: buildPitchContours(frames, nominalStep),
  };
}

function buildNoteSegments(
  frames: Array<{ frame: PitchFrame; frameDuration: number }>,
  duration: number,
  nominalStep: number,
): NoteSegment[] {
  const segments: NoteSegment[] = [];
  let active = new Map<string, ActiveNoteSegment>();
  const toleranceSemitones = 0.6;

  for (const { frame, frameDuration } of frames) {
    const framePitches = frame.f0
      .map((frequency) => {
        const note = hzToNote(frequency);
        return note && note.midi >= MIDI_MIN && note.midi <= MIDI_MAX ? note : null;
      })
      .filter((pitch): pitch is NonNullable<typeof pitch> => pitch !== null);
    const available = new Set(framePitches.map((_, index) => index));
    const nextActive = new Map<string, ActiveNoteSegment>();
    const pairs = [...active.entries()]
      .flatMap(([key, segment]) =>
        framePitches.map((pitch, pitchIndex) => ({
          key,
          pitchIndex,
          distance: Math.abs(pitch.midi - segment.meanMidi),
          segment,
          pitchMidi: pitch.midi,
        })),
      )
      .filter(
        ({ distance, segment }) =>
          distance <= toleranceSemitones &&
          framesAreAdjacent(segment.lastTime, frame.t, nominalStep),
      )
      .sort((left, right) => left.distance - right.distance);

    for (const pair of pairs) {
      if (nextActive.has(pair.key) || !available.has(pair.pitchIndex)) continue;
      const { count } = pair.segment;
      available.delete(pair.pitchIndex);
      const pitchMidi = pair.pitchMidi;
      const nextCount = count + 1;
      nextActive.set(pair.key, {
        ...pair.segment,
        end: Math.min(duration, frame.t + frameDuration),
        meanMidi: pair.segment.meanMidi + (pitchMidi - pair.segment.meanMidi) / nextCount,
        lastTime: frame.t,
        count: nextCount,
      });
    }

    for (let pitchIndex = 0; pitchIndex < framePitches.length; pitchIndex += 1) {
      if (!available.has(pitchIndex)) continue;
      const pitchMidi = framePitches[pitchIndex].midi;
      const segment = {
        noteMidi: Math.round(pitchMidi),
        start: frame.t,
        end: Math.min(duration, frame.t + frameDuration),
        meanMidi: pitchMidi,
        lastTime: frame.t,
        count: 1,
      };
      const key = `${segment.noteMidi}:${frame.t}:${pitchIndex}`;
      nextActive.set(key, segment);
      active.set(key, segment);
    }

    for (const [key, segment] of active) {
      if (!nextActive.has(key)) {
        segments.push({
          noteMidi: segment.noteMidi,
          start: segment.start,
          end: segment.end,
        });
        active.delete(key);
      }
    }
    active = nextActive;
  }

  for (const segment of active.values()) {
    segments.push({
      noteMidi: segment.noteMidi,
      start: segment.start,
      end: segment.end,
    });
  }

  return segments;
}

function buildPitchContours(
  frames: Array<{ frame: PitchFrame; frameDuration: number }>,
  nominalStep: number,
): PitchContour[] {
  let active: PitchContour[] = [];
  const completed: PitchContour[] = [];
  const maximumJumpSemitones = 7;

  for (const { frame } of frames) {
    const current = frame.f0
      .map((frequency): ContourPoint | null => {
        const note = hzToNote(frequency);
        if (!note || note.midi < MIDI_MIN || note.midi > MIDI_MAX) return null;
        return {
          midi: note.midi,
          time: frame.t,
        };
      })
      .filter((pitch): pitch is ContourPoint => pitch !== null);
    const usedTracks = new Set<number>();
    const usedPitches = new Set<number>();
    const candidates = active.flatMap((track, trackIndex) => {
      const last = track.points.at(-1);
      if (!last || !framesAreAdjacent(last.time, frame.t, nominalStep)) return [];
      return current
        .map((pitch, pitchIndex) => ({
          trackIndex,
          pitchIndex,
          distance: Math.abs(pitch.midi - last.midi),
        }))
        .filter(({ distance }) => distance <= maximumJumpSemitones)
        .sort((left, right) => left.distance - right.distance);
    });
    candidates.sort((left, right) => left.distance - right.distance);
    const nextActive: PitchContour[] = [];

    for (const candidate of candidates) {
      if (usedTracks.has(candidate.trackIndex) || usedPitches.has(candidate.pitchIndex)) continue;
      usedTracks.add(candidate.trackIndex);
      usedPitches.add(candidate.pitchIndex);
      active[candidate.trackIndex].points.push(current[candidate.pitchIndex]);
      nextActive.push(active[candidate.trackIndex]);
    }

    active.forEach((track, index) => {
      if (!usedTracks.has(index)) completed.push(track);
    });
    current.forEach((pitch, index) => {
      if (!usedPitches.has(index)) nextActive.push({ points: [pitch] });
    });
    active = nextActive;
  }

  completed.push(...active);
  return completed.filter((contour) => contour.points.length > 1);
}

function framesAreAdjacent(previousTime: number, currentTime: number, nominalStep: number): boolean {
  const delta = currentTime - previousTime;
  return delta > 0 && delta <= nominalStep * 1.5;
}

function medianPositiveDelta(times: number[]): number {
  const deltas = times
    .slice(1)
    .map((time, index) => time - times[index])
    .filter((delta) => delta > 0)
    .sort((left, right) => left - right);
  if (deltas.length === 0) return 0;
  return deltas[Math.floor(deltas.length / 2)];
}

function drawContours(
  context: CanvasRenderingContext2D,
  contours: PitchContour[],
  width: number,
  duration: number,
): void {
  context.save();
  context.strokeStyle = "rgba(77, 74, 139, 0.42)";
  context.lineWidth = 1.4;
  context.lineCap = "round";
  context.lineJoin = "round";
  for (const contour of contours) {
    context.beginPath();
    contour.points.forEach((point, index) => {
      const x = playheadXForTime(width, point.time, duration);
      const y = midiY(point.midi);
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
  }
  context.restore();
}

function drawNoteSegments(
  context: CanvasRenderingContext2D,
  segments: NoteSegment[],
  width: number,
  duration: number,
): void {
  context.save();
  context.fillStyle = "#635bdb";
  for (const segment of segments) {
    const x = playheadXForTime(width, segment.start, duration);
    const endX = playheadXForTime(width, segment.end, duration);
    const y = midiY(segment.noteMidi);
    const barHeight = 8;
    context.beginPath();
    context.roundRect(x, y - barHeight / 2, Math.max(2, endX - x), barHeight, 3);
    context.fill();
  }
  context.restore();
}

function drawRawDetections(context: CanvasRenderingContext2D, points: DetectedPitch[]): void {
  context.save();
  context.fillStyle = "rgba(49, 48, 75, 0.28)";
  for (const point of points) {
    context.beginPath();
    context.arc(point.x, point.y, 1.15, 0, Math.PI * 2);
    context.fill();
  }
  context.restore();
}

function prepareCanvas(canvas: HTMLCanvasElement, height: number): CanvasRenderingContext2D {
  const width = Math.max(1, canvas.clientWidth);
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.style.height = `${height}px`;
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser could not create a chart canvas.");
  context.scale(pixelRatio, pixelRatio);
  context.font = "11px 'DM Sans', sans-serif";
  return context;
}

function midiY(midi: number): number {
  return TOP + (MIDI_MAX - midi) * ROW_HEIGHT + ROW_HEIGHT / 2;
}

function rowTop(midi: number): number {
  return TOP + (MIDI_MAX - midi) * ROW_HEIGHT;
}

function getTimeTickStep(duration: number, plotWidth: number): number {
  const rawStep = (duration * 90) / Math.max(100, plotWidth);
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, rawStep)));
  const normalized = rawStep / magnitude;
  const niceStep = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return niceStep * magnitude;
}

function formatTime(seconds: number): string {
  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  return `${minutes}:${(totalSeconds % 60).toString().padStart(2, "0")}`;
}
