import sample from "../sample_transcription.json";
import { checkBackend, transcribe } from "./api";
import { drawPitchChart } from "./plot";
import type { TranscriptionResponse } from "./types";
import "./styles.css";

const MAX_FILE_BYTES = 30_000_000;
const ALLOWED_EXTENSIONS = [".wav", ".flac", ".ogg", ".mp3"];

const fileInput = getElement<HTMLInputElement>("audio-file");
const fileLabel = getElement<HTMLSpanElement>("file-label");
const selectedFilePanel = getElement<HTMLDivElement>("selected-file");
const fileName = getElement<HTMLElement>("file-name");
const fileMeta = getElement<HTMLElement>("file-meta");
const analyzeButton = getElement<HTMLButtonElement>("analyze-button");
const sampleButton = getElement<HTMLButtonElement>("sample-button");
const clearFileButton = getElement<HTMLButtonElement>("clear-file");
const thresholdInput = getElement<HTMLInputElement>("threshold");
const thresholdValue = getElement<HTMLOutputElement>("threshold-value");
const statusMessage = getElement<HTMLParagraphElement>("status-message");
const connectionDot = getElement<HTMLSpanElement>("connection-dot");
const connectionLabel = getElement<HTMLSpanElement>("connection-label");
const chartEmpty = getElement<HTMLDivElement>("chart-empty");
const chartWrap = getElement<HTMLDivElement>("chart-wrap");
const chartCanvas = getElement<HTMLCanvasElement>("pitch-chart");
const chartTooltip = getElement<HTMLDivElement>("chart-tooltip");
const chartLegend = getElement<HTMLDivElement>("chart-legend");
const chartDuration = getElement<HTMLSpanElement>("chart-duration");

let selectedFile: File | null = null;
let busy = false;
let latestResult: TranscriptionResponse | null = null;
let selectedFileDuration: number | null = null;
let audioObjectUrl: string | null = null;
let resizeObserver: ResizeObserver | null = null;

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) selectFile(file);
});

thresholdInput.addEventListener("input", () => {
  thresholdValue.value = Number(thresholdInput.value).toFixed(2);
});

analyzeButton.addEventListener("click", () => {
  if (selectedFile) void analyzeFile(selectedFile);
});

sampleButton.addEventListener("click", () => {
  showResult(sample, "Included sample");
  setStatus("Showing the included sample transcription.", "success");
});

clearFileButton.addEventListener("click", clearSelectedFile);

const dropzone = document.querySelector<HTMLLabelElement>(".dropzone");
dropzone?.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("is-dragging");
});
dropzone?.addEventListener("dragleave", () => dropzone.classList.remove("is-dragging"));
dropzone?.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("is-dragging");
  const file = event.dataTransfer?.files[0];
  if (file) selectFile(file);
});

void checkBackend()
  .then(() => {
    connectionDot.classList.add("is-online");
    connectionLabel.textContent = "Backend connected";
  })
  .catch(() => {
    connectionDot.classList.add("is-offline");
    connectionLabel.textContent = "Backend unavailable";
  });

function selectFile(file: File): void {
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    setStatus("Choose a WAV, FLAC, OGG, or MP3 audio file.", "error");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    setStatus("That file is over the 30 MB upload limit.", "error");
    return;
  }

  clearAudioUrl();
  selectedFile = file;
  selectedFileDuration = null;
  fileName.textContent = file.name;
  fileMeta.textContent = `${formatBytes(file.size)} · reading duration…`;
  fileLabel.textContent = "Audio file selected";
  selectedFilePanel.hidden = false;
  analyzeButton.disabled = false;
  setStatus("Ready to analyze. Longer recordings may take several minutes.", "default");
  void readAudioDuration(file);
}

function clearSelectedFile(): void {
  if (busy) return;
  selectedFile = null;
  selectedFileDuration = null;
  fileInput.value = "";
  fileLabel.textContent = "or drag and drop it here · up to 30 MB";
  selectedFilePanel.hidden = true;
  analyzeButton.disabled = true;
  clearAudioUrl();
  setStatus("Choose an audio file or load the sample to get started.", "default");
}

async function readAudioDuration(file: File): Promise<void> {
  const audio = new Audio();
  audioObjectUrl = URL.createObjectURL(file);
  audio.src = audioObjectUrl;
  try {
    await new Promise<void>((resolve, reject) => {
      audio.addEventListener("loadedmetadata", () => resolve(), { once: true });
      audio.addEventListener("error", () => reject(new Error("Could not read the audio duration.")), {
        once: true,
      });
    });
    if (selectedFile !== file) return;
    selectedFileDuration = audio.duration;
    fileMeta.textContent = `${formatBytes(file.size)} · ${formatDuration(audio.duration)}`;
    setStatus(
      `${formatDuration(audio.duration)} recording selected. Analysis can take about 0.7 seconds per second of audio.`,
      "default",
    );
  } catch {
    if (selectedFile === file) {
      fileMeta.textContent = `${formatBytes(file.size)} · duration unavailable`;
    }
  }
}

async function analyzeFile(file: File): Promise<void> {
  busy = true;
  setControlsDisabled(true);
  setStatus(
    `Analyzing${selectedFileDuration ? ` ${formatDuration(selectedFileDuration)} of audio` : ""}. This may take a while; you can leave this tab open.`,
    "loading",
  );
  try {
    const result = await transcribe(file, Number(thresholdInput.value));
    showResult(result, file.name);
    const processTime =
      typeof result.process_s === "number" ? ` · model time ${result.process_s.toFixed(1)} s` : "";
    setStatus(`Analysis complete${processTime}.`, "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Analysis failed unexpectedly.", "error");
  } finally {
    busy = false;
    setControlsDisabled(false);
  }
}

function showResult(result: TranscriptionResponse, source: string): void {
  latestResult = result;
  chartEmpty.hidden = true;
  chartWrap.hidden = false;
  chartLegend.hidden = false;
  const duration =
    result.duration_s ??
    Math.max(result.hop_s, (result.frames.at(-1)?.t ?? 0) + result.hop_s);
  chartDuration.textContent = `${formatDuration(duration)} · ${source}`;
  renderLatestChart();
  resizeObserver?.disconnect();
  resizeObserver = new ResizeObserver(renderLatestChart);
  resizeObserver.observe(chartCanvas);
}

function renderLatestChart(): void {
  if (!latestResult || chartWrap.hidden) return;
  drawPitchChart(chartCanvas, chartTooltip, latestResult);
}

function setControlsDisabled(disabled: boolean): void {
  fileInput.disabled = disabled;
  analyzeButton.disabled = disabled || selectedFile === null;
  sampleButton.disabled = disabled;
  thresholdInput.disabled = disabled;
  clearFileButton.disabled = disabled;
}

function setStatus(
  message: string,
  state: "default" | "loading" | "success" | "error",
): void {
  statusMessage.textContent = message;
  statusMessage.className = `status-message is-${state}`;
}

function clearAudioUrl(): void {
  if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl);
  audioObjectUrl = null;
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "duration unavailable";
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

function formatBytes(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing required page element: #${id}`);
  return element as T;
}
