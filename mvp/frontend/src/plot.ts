import { formatCents, hzToNote } from "./music";
import type { PitchFrame, TranscriptionResponse } from "./types";

const MIDI_MIN = 24;
const MIDI_MAX = 96;
const LEFT = 54;
const RIGHT = 18;
const TOP = 18;
const BOTTOM = 36;

interface PlotPoint {
  x: number;
  y: number;
  frame: PitchFrame;
  frequency: number;
  noteName: string;
  cents: number;
}

export function drawPitchChart(
  canvas: HTMLCanvasElement,
  tooltip: HTMLDivElement,
  result: TranscriptionResponse,
): void {
  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser could not create a chart canvas.");

  const bounds = canvas.getBoundingClientRect();
  const width = Math.max(1, bounds.width);
  const height = Math.max(1, bounds.height);
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * pixelRatio);
  canvas.height = Math.round(height * pixelRatio);
  context.scale(pixelRatio, pixelRatio);
  context.clearRect(0, 0, width, height);

  const plotWidth = Math.max(1, width - LEFT - RIGHT);
  const plotHeight = Math.max(1, height - TOP - BOTTOM);
  const duration =
    result.duration_s ??
    Math.max(result.hop_s, (result.frames.at(-1)?.t ?? 0) + result.hop_s);
  const points: PlotPoint[] = [];

  context.font = "11px Inter, ui-sans-serif, system-ui, sans-serif";
  context.textBaseline = "middle";
  for (let midi = MIDI_MIN; midi <= MIDI_MAX; midi += 12) {
    const y = TOP + ((MIDI_MAX - midi) / (MIDI_MAX - MIDI_MIN)) * plotHeight;
    const note = hzToNote(440 * 2 ** ((midi - 69) / 12));
    context.strokeStyle = "#e8eaf0";
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(LEFT, y);
    context.lineTo(width - RIGHT, y);
    context.stroke();
    context.fillStyle = "#777f91";
    context.textAlign = "right";
    context.fillText(note?.name ?? "", LEFT - 10, y);
  }

  for (let second = 0; second <= Math.floor(duration); second += 1) {
    const x = LEFT + (second / duration) * plotWidth;
    context.strokeStyle = "#f0f1f5";
    context.beginPath();
    context.moveTo(x, TOP);
    context.lineTo(x, TOP + plotHeight);
    context.stroke();
    context.fillStyle = "#777f91";
    context.textAlign = "center";
    context.fillText(`${second}s`, x, height - 15);
  }

  for (const frame of result.frames) {
    for (const frequency of frame.f0) {
      const note = hzToNote(frequency);
      if (!note || note.midi < MIDI_MIN || note.midi > MIDI_MAX) continue;
      points.push({
        x: LEFT + (frame.t / duration) * plotWidth,
        y: TOP + ((MIDI_MAX - note.midi) / (MIDI_MAX - MIDI_MIN)) * plotHeight,
        frame,
        frequency,
        noteName: note.name,
        cents: note.cents,
      });
    }
  }

  context.fillStyle = "#635bdb";
  for (const point of points) {
    context.beginPath();
    context.arc(point.x, point.y, 2.4, 0, Math.PI * 2);
    context.fill();
  }

  const onPointerMove = (event: PointerEvent) => {
    const rect = canvas.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    let nearest: PlotPoint | undefined;
    let nearestDistance = 14;

    for (const point of points) {
      const distance = Math.hypot(point.x - pointerX, point.y - pointerY);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    }

    if (!nearest) {
      tooltip.hidden = true;
      return;
    }

    const note = hzToNote(nearest.frequency);
    tooltip.textContent = `${nearest.noteName} · ${formatCents(nearest.cents)} · ${nearest.frame.t.toFixed(2)} s · ${nearest.frequency.toFixed(1)} Hz`;
    tooltip.hidden = false;
    tooltip.style.left = `${Math.min(width - 230, Math.max(8, pointerX + 12))}px`;
    tooltip.style.top = `${Math.max(8, pointerY - 42)}px`;
    canvas.setAttribute(
      "aria-label",
      `Pitch trace. Selected ${note?.name ?? nearest.noteName} ${formatCents(nearest.cents)} at ${nearest.frame.t.toFixed(2)} seconds.`,
    );
  };

  canvas.onpointermove = onPointerMove;
  canvas.onpointerleave = () => {
    tooltip.hidden = true;
    canvas.setAttribute("aria-label", "Pitch trace over time");
  };
}
