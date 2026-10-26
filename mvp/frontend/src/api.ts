import type { TranscriptionResponse } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000")
  .trim()
  .replace(/\/+$/, "");

export async function checkBackend(): Promise<void> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Backend health check failed (${response.status}).`);
  }
}

export async function transcribe(
  file: File,
  threshold: number,
): Promise<TranscriptionResponse> {
  const body = new FormData();
  body.append("file", file);

  const query = new URLSearchParams({
    threshold: threshold.toString(),
    hop: "1",
  });
  const response = await fetch(`${API_BASE}/transcribe?${query}`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const details = await response.text();
    throw new Error(apiErrorMessage(response.status, details));
  }

  const result: unknown = await response.json();
  if (!isTranscriptionResponse(result)) {
    throw new Error("The backend returned an unexpected transcription response.");
  }
  return result;
}

function isTranscriptionResponse(value: unknown): value is TranscriptionResponse {
  if (!isRecord(value)) return false;
  return (
    typeof value.sample_rate === "number" &&
    typeof value.hop_s === "number" &&
    typeof value.threshold === "number" &&
    typeof value.n_frames === "number" &&
    Array.isArray(value.frames) &&
    value.frames.every(isPitchFrame)
  );
}

function isPitchFrame(value: unknown): value is TranscriptionResponse["frames"][number] {
  return (
    isRecord(value) &&
    typeof value.t === "number" &&
    Array.isArray(value.f0) &&
    value.f0.every((frequency) => typeof frequency === "number")
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function apiErrorMessage(status: number, details: string): string {
  switch (status) {
    case 413:
      return "That file is over the backend's 30 MB limit.";
    case 415:
      return "Unsupported audio format. Choose WAV, FLAC, OGG, or MP3.";
    case 422:
      return "The backend rejected the analysis settings or file.";
    default: {
      const message = details.trim();
      return `Analysis failed (${status})${message ? `: ${message}` : "."}`;
    }
  }
}
