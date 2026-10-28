import sample from "../sample_transcription.json";
import { checkBackend, transcribe } from "./api";
import {
  chartTimeAtClientX,
  drawPitchChart,
  drawTimeAxis,
  getPitchChartHeight,
  getResultDuration,
  playheadXForTime,
  setDefaultPitchView,
} from "./plot";
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
const chartScroll = getElement<HTMLDivElement>("pitch-scroll");
const chartCanvas = getElement<HTMLCanvasElement>("pitch-chart");
const timeAxisCanvas = getElement<HTMLCanvasElement>("time-axis");
const chartTooltip = getElement<HTMLDivElement>("chart-tooltip");
const chartLegend = getElement<HTMLDivElement>("chart-legend");
const rawDetectionsToggle = getElement<HTMLInputElement>("raw-detections-toggle");
const chartDuration = getElement<HTMLSpanElement>("chart-duration");
const playbackControls = getElement<HTMLElement>("playback-controls");
const playButton = getElement<HTMLButtonElement>("play-button");
const playIcon = getElement<HTMLSpanElement>("play-icon");
const playbackSeek = getElement<HTMLInputElement>("playback-seek");
const playbackTime = getElement<HTMLOutputElement>("playback-time");
const axisPlayhead = getElement<HTMLSpanElement>("axis-playhead");
const pitchPlayhead = getElement<HTMLSpanElement>("pitch-playhead");

let selectedFile: File | null = null;
let busy = false;
let latestResult: TranscriptionResponse | null = null;
let resultSourceFile: File | null = null;
let selectedFileDuration: number | null = null;
let audioObjectUrl: string | null = null;
let audioElement: HTMLAudioElement | null = null;
let audioEventController: AbortController | null = null;
let resizeObserver: ResizeObserver | null = null;
let playheadAnimationFrame: number | null = null;

window.addEventListener("pagehide", resetAudioSource, { once: true });

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) selectFile(file);
});

thresholdInput.addEventListener("input", () => {
  thresholdValue.value = Number(thresholdInput.value).toFixed(2);
});

rawDetectionsToggle.addEventListener("change", () => renderLatestChart(false));

analyzeButton.addEventListener("click", () => {
  if (selectedFile) void analyzeFile(selectedFile);
});

sampleButton.addEventListener("click", () => {
  if (busy) return;
  clearSelectedFile();
  showResult(sample, "Included sample");
  setStatus("Showing the included sample transcription.", "success");
});

clearFileButton.addEventListener("click", clearSelectedFile);

playButton.addEventListener("click", () => {
  void togglePlayback();
});

playbackSeek.addEventListener("input", () => {
  if (!audioElement || !Number.isFinite(audioElement.duration)) return;
  audioElement.currentTime = Number(playbackSeek.value);
  updatePlaybackDisplay();
  renderPlayhead();
});

chartCanvas.addEventListener("click", (event) => {
  if (
    !audioElement ||
    !Number.isFinite(audioElement.duration) ||
    !latestResult ||
    resultSourceFile !== selectedFile
  ) return;
  const duration = getTimelineDuration();
  const seekTime = chartTimeAtClientX(chartCanvas, event.clientX, duration);
  if (seekTime === null) return;
  audioElement.currentTime = Math.min(seekTime, audioElement.duration);
  updatePlaybackDisplay();
  renderPlayhead();
});

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
  if (busy) return;
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    setStatus("Choose a WAV, FLAC, OGG, or MP3 audio file.", "error");
    return;
  }
  if (file.size > MAX_FILE_BYTES) {
    setStatus("That file is over the 30 MB upload limit.", "error");
    return;
  }

  resetAudioSource();
  selectedFile = file;
  selectedFileDuration = null;
  fileName.textContent = file.name;
  fileMeta.textContent = `${formatBytes(file.size)} · reading duration…`;
  fileLabel.textContent = "Audio file selected";
  selectedFilePanel.hidden = false;
  playbackControls.hidden = false;
  analyzeButton.disabled = false;
  clearChart("Analyze this recording to see its pitch trace.");
  setStatus("Ready to analyze. Longer recordings may take several minutes.", "default");
  loadAudioFile(file);
}

function clearSelectedFile(): void {
  if (busy) return;
  resetAudioSource();
  selectedFile = null;
  selectedFileDuration = null;
  fileInput.value = "";
  fileLabel.textContent = "or drag and drop it here · up to 30 MB";
  selectedFilePanel.hidden = true;
  playbackControls.hidden = true;
  analyzeButton.disabled = true;
  clearChart("Your pitch trace will appear here.");
  setStatus("Choose an audio file or load the sample to get started.", "default");
}

function loadAudioFile(file: File): void {
  audioObjectUrl = URL.createObjectURL(file);
  audioElement = new Audio();
  audioElement.preload = "metadata";
  audioEventController = new AbortController();
  const { signal } = audioEventController;

  audioElement.addEventListener("loadedmetadata", onAudioMetadata, { signal });
  audioElement.addEventListener("durationchange", onAudioMetadata, { signal });
  audioElement.addEventListener("timeupdate", updatePlaybackDisplay, { signal });
  audioElement.addEventListener("play", onAudioPlay, { signal });
  audioElement.addEventListener("pause", onAudioPause, { signal });
  audioElement.addEventListener("ended", onAudioEnded, { signal });
  audioElement.addEventListener(
    "error",
    () => {
      playButton.disabled = true;
      playbackSeek.disabled = true;
      setStatus("This browser could not decode the selected audio file for playback.", "error");
    },
    { signal },
  );
  audioElement.src = audioObjectUrl;
  audioElement.load();
  updatePlaybackDisplay();
}

function onAudioMetadata(): void {
  if (!audioElement || !Number.isFinite(audioElement.duration)) return;
  selectedFileDuration = audioElement.duration;
  fileMeta.textContent = `${formatBytes(selectedFile?.size ?? 0)} · ${formatDuration(audioElement.duration)}`;
  playbackSeek.min = "0";
  playbackSeek.max = String(audioElement.duration);
  playbackSeek.step = "0.01";
  playbackSeek.disabled = audioElement.duration <= 0;
  playButton.disabled = audioElement.duration <= 0;
  updatePlaybackDisplay();
  if (latestResult && resultSourceFile === selectedFile) renderLatestChart(false);
  setStatus(
    `${formatDuration(audioElement.duration)} recording selected. Analysis can take about 0.7 seconds per second of audio.`,
    "default",
  );
}

async function togglePlayback(): Promise<void> {
  if (!audioElement || playButton.disabled) return;
  if (!audioElement.paused) {
    audioElement.pause();
    return;
  }

  if (audioElement.ended || audioElement.currentTime >= audioElement.duration) {
    audioElement.currentTime = 0;
  }
  try {
    await audioElement.play();
  } catch (error) {
    setStatus(
      error instanceof Error ? `Could not play audio: ${error.message}` : "Could not play this audio.",
      "error",
    );
  }
}

function onAudioPlay(): void {
  playIcon.textContent = "Ⅱ";
  playButton.setAttribute("aria-label", "Pause audio");
  startPlayheadAnimation();
}

function onAudioPause(): void {
  playIcon.textContent = "▶";
  playButton.setAttribute("aria-label", "Play audio");
  stopPlayheadAnimation();
  updatePlaybackDisplay();
  renderPlayhead();
}

function onAudioEnded(): void {
  playIcon.textContent = "▶";
  playButton.setAttribute("aria-label", "Play audio");
  stopPlayheadAnimation();
  updatePlaybackDisplay();
  renderPlayhead();
}

function startPlayheadAnimation(): void {
  if (playheadAnimationFrame !== null) return;
  const tick = () => {
    renderPlayhead();
    if (audioElement && !audioElement.paused && !audioElement.ended) {
      playheadAnimationFrame = requestAnimationFrame(tick);
    } else {
      playheadAnimationFrame = null;
    }
  };
  playheadAnimationFrame = requestAnimationFrame(tick);
}

function stopPlayheadAnimation(): void {
  if (playheadAnimationFrame !== null) {
    cancelAnimationFrame(playheadAnimationFrame);
    playheadAnimationFrame = null;
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
    showResult(result, file.name, file);
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

function showResult(
  result: TranscriptionResponse,
  source: string,
  sourceFile: File | null = null,
): void {
  latestResult = result;
  resultSourceFile = sourceFile;
  chartEmpty.hidden = true;
  chartWrap.hidden = false;
  chartLegend.hidden = false;
  chartDuration.textContent = `${formatDuration(getTimelineDuration())} · ${source}`;
  renderLatestChart(true);
  resizeObserver?.disconnect();
  let observedHeight = chartScroll.clientHeight;
  resizeObserver = new ResizeObserver(() => {
    const heightChanged = observedHeight !== chartScroll.clientHeight;
    observedHeight = chartScroll.clientHeight;
    renderLatestChart(heightChanged);
  });
  resizeObserver.observe(chartScroll);
}

function clearChart(message: string): void {
  latestResult = null;
  resultSourceFile = null;
  resizeObserver?.disconnect();
  resizeObserver = null;
  chartWrap.hidden = true;
  chartLegend.hidden = true;
  chartEmpty.hidden = false;
  chartEmpty.querySelector("p")!.textContent = message;
  chartDuration.textContent = "No analysis yet";
  axisPlayhead.hidden = true;
  pitchPlayhead.hidden = true;
}

function renderLatestChart(resetPitchView = false): void {
  if (!latestResult || chartWrap.hidden) return;
  const duration = getTimelineDuration();
  chartDuration.textContent = `${formatDuration(duration)} · ${
    resultSourceFile ? resultSourceFile.name : "Included sample"
  }`;
  timeAxisCanvas.style.width = `${chartCanvas.clientWidth}px`;
  drawTimeAxis(timeAxisCanvas, duration);
  drawPitchChart(chartCanvas, chartTooltip, latestResult, duration, rawDetectionsToggle.checked);
  chartCanvas.style.height = `${getPitchChartHeight()}px`;
  if (resetPitchView) setDefaultPitchView(chartScroll);
  renderPlayhead();
}

function renderPlayhead(): void {
  if (
    !latestResult ||
    !audioElement ||
    resultSourceFile !== selectedFile ||
    chartWrap.hidden
  ) {
    axisPlayhead.hidden = true;
    pitchPlayhead.hidden = true;
    return;
  }
  const duration = getTimelineDuration();
  const x = playheadXForTime(chartCanvas.clientWidth, audioElement.currentTime, duration);
  axisPlayhead.hidden = false;
  pitchPlayhead.hidden = false;
  axisPlayhead.style.left = `${x}px`;
  pitchPlayhead.style.left = `${x}px`;
}

function getTimelineDuration(): number {
  const resultDuration = latestResult ? getResultDuration(latestResult) : 0;
  const mediaDuration =
    resultSourceFile && resultSourceFile === selectedFile ? (selectedFileDuration ?? 0) : 0;
  return Math.max(resultDuration, mediaDuration, 0.01);
}

function updatePlaybackDisplay(): void {
  if (!audioElement) {
    playbackTime.value = "0:00 / 0:00";
    return;
  }
  const duration = Number.isFinite(audioElement.duration) ? audioElement.duration : 0;
  const currentTime = Math.min(audioElement.currentTime, duration || audioElement.currentTime);
  playbackSeek.value = String(currentTime);
  playbackTime.value = `${formatDuration(currentTime)} / ${formatDuration(duration)}`;
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

function resetAudioSource(): void {
  stopPlayheadAnimation();
  audioEventController?.abort();
  audioEventController = null;
  if (audioElement) {
    audioElement.pause();
    audioElement.removeAttribute("src");
    audioElement.load();
  }
  audioElement = null;
  if (audioObjectUrl) URL.revokeObjectURL(audioObjectUrl);
  audioObjectUrl = null;
  playButton.disabled = true;
  playButton.setAttribute("aria-label", "Play audio");
  playIcon.textContent = "▶";
  playbackSeek.value = "0";
  playbackSeek.min = "0";
  playbackSeek.max = "0";
  playbackSeek.disabled = true;
  playbackTime.value = "0:00 / 0:00";
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "duration unavailable";
  const totalSeconds = Math.floor(seconds);
  const minutes = Math.floor(totalSeconds / 60);
  const remainder = totalSeconds % 60;
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
