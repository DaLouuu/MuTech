# MuTech frontend starter

This is a small TypeScript + Vite frontend for the choir pitch-tracking API. It
uses a plain canvas renderer rather than a charting dependency, so pitch points
can be drawn directly from the API's frame data.

## Run it

From this directory:

```bash
npm install
npm run dev
```

The page is served at `http://localhost:5173`. Start the FastAPI backend
separately on `http://localhost:8000`, or create a `.env` file from
`.env.example` and set `VITE_API_BASE_URL` to the backend's base URL. The backend
must allow the frontend origin through its `CORS_ORIGINS` setting.

Use **Load sample** to view the checked-in `sample_transcription.json` without
starting the backend. For a live analysis, select a WAV, FLAC, OGG, or MP3 file
up to 30 MB and choose **Analyze recording**. The browser sends one request at
a time and intentionally does not impose a short timeout.

## What is included

- Upload controls, drag-and-drop, file-size/type checks, and audio duration
- Sensitivity slider wired to the API's `threshold` query parameter
- Live backend health indicator and API error messages
- Piano-inspired pitch axis with a labelled row for each C1–C7 semitone
- Taller C3–C6 desktop view with the full model pitch range available by scrolling
- Canvas pitch plot with time on x and fractional MIDI/log frequency on y
- Sustained-note segments with a subtle continuity contour
- Optional raw detections layer for frame-level inspection
- Hover details for note, cents, time, and frequency
- Playback, seeking, and a playhead synchronized to the selected audio file
- Notes about unordered pitches and the limits of model precision

The graph shows pitches from C1 through C7, covering the model's reported pitch
range. On a desktop-height viewport the initial scroll window shows C3 through
C6 at readable semitone spacing; the full range remains available by scrolling.
Shorter viewports center around C4 and scroll rather than compressing pitch rows.
Equal semitone spacing means C4 cannot be at the exact vertical center while
C3 and C6 are both visible: C4 is one octave above C3 but two octaves below C6.
The time ruler remains fixed while scrolling vertically. Click a time on the
pitch plot to seek the selected recording.

Adjacent frame detections within 60 cents are grouped into note-like segments.
Segments stop at missing frames, and their displayed duration is limited to the
frame spacing in the response. A secondary contour links detections across
adjacent frames only when the pitch jump is no greater than seven semitones.
The raw frame detections can be toggled on for detail. Since pitches are
unordered sets, contour paths are visual continuity hints, not singer or voice
assignments. The API provides no progress percentage; the interface shows an
indeterminate analysis state instead.

Playback uses the uploaded file's browser object URL; no second upload is
required. The plot timeline uses the longer of the media duration and the
analysis duration, so a small discrepancy at the end of the file does not
compress or truncate the detected pitch frames.
