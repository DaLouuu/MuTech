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
- Canvas pitch plot with time on x and fractional MIDI/log frequency on y
- Hover details for note, cents, time, and frequency
- Notes about unordered pitches and the limits of model precision

The graph currently shows pitches from C1 through C7, covering the model's
reported pitch range. The response is an unordered set of pitches per frame,
so dots are not labelled by singer. The API provides no progress percentage;
the interface shows an indeterminate analysis state instead.
