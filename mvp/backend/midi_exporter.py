"""Standard MIDI File (Type 1) Export Pipeline.

Implements Checklist Phase 3:
- 3.4.2 Standard MIDI File (Type 1) Export with multi-track SATB separation
  and continuous pitch bend intonation messages using mido.
"""

import io
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

DEFAULT_TICKS_PER_BEAT = 480
DEFAULT_TEMPO_US = 500000  # 120 BPM (0.5 s per beat) -> 960 ticks per second


def _seconds_to_ticks(sec: float, ticks_per_beat: int = DEFAULT_TICKS_PER_BEAT, tempo_us: int = DEFAULT_TEMPO_US) -> int:
    """Convert time in seconds to MIDI ticks."""
    return int(round(sec * (ticks_per_beat * 1_000_000.0 / tempo_us)))


def _cents_to_pitchwheel(cents: int, pitch_range_cents: float = 200.0) -> int:
    """Convert signed cents deviation [-50, +50] to MIDI pitchwheel value [-8192, 8191]."""
    clamped_cents = max(-pitch_range_cents, min(pitch_range_cents, float(cents)))
    wheel = int(round((clamped_cents / pitch_range_cents) * 8191.0))
    return max(-8192, min(8191, wheel))


def generate_midi_type1(
    contours: list[dict],
    tempo_bpm: int = 120,
) -> bytes:
    """Generate a multi-track Standard MIDI File (Type 1) from vocal contours.

    Each voice part (Soprano, Alto, Tenor, Bass, etc.) is rendered into an
    independent MIDI track with Note On/Off events and pitch bend automation.

    Args:
        contours: List of ContourTrajectory dicts
        tempo_bpm: Playback tempo in beats per minute

    Returns:
        Binary bytes of the .mid file
    """
    mid = MidiFile(type=1, ticks_per_beat=DEFAULT_TICKS_PER_BEAT)
    tempo_us = mido.bpm2tempo(tempo_bpm)

    # 1. Master Tempo & Conductor Track (Track 0)
    master_track = MidiTrack()
    master_track.append(MetaMessage("track_name", name="Conductor / Tempo", time=0))
    master_track.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))
    master_track.append(MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    master_track.append(MetaMessage("end_of_track", time=0))
    mid.tracks.append(master_track)

    # Group trajectories by voice part
    voice_groups: dict[str, list[dict]] = {
        "Soprano": [],
        "Alto": [],
        "Tenor": [],
        "Bass": [],
        "Unassigned": [],
    }

    for c in contours:
        part = c.get("voice_part", "Unassigned")
        if part not in voice_groups:
            voice_groups[part] = []
        voice_groups[part].append(c)

    # MIDI Channel assignment: 0: Soprano, 1: Alto, 2: Tenor, 3: Bass, 4: Unassigned
    part_channels = {
        "Soprano": 0,
        "Alto": 1,
        "Tenor": 2,
        "Bass": 3,
        "Unassigned": 4,
    }

    # Standard Choral/Vocal General MIDI Instrument: Choir Aahs (Program 52)
    CHOIR_PROGRAM = 52

    for part_name, tracks in voice_groups.items():
        if not tracks:
            continue

        track = MidiTrack()
        track.append(MetaMessage("track_name", name=f"Choir - {part_name}", time=0))
        ch = part_channels.get(part_name, 0)
        track.append(Message("program_change", program=CHOIR_PROGRAM, channel=ch, time=0))

        # Collect raw timed events: (tick, priority, message)
        # Priority ensures PitchWheel / NoteOff happen before NoteOn at identical tick
        raw_events: list[tuple[int, int, Message]] = []

        for contour in tracks:
            pts = contour.get("points", [])
            if not pts:
                continue

            # Continuous segment processing
            seg_start_t = pts[0]["t"]
            seg_end_t = pts[-1]["t"]
            # Estimate MIDI note from median or primary note
            midi_notes = []
            for p in pts:
                hz = p.get("hz", 0)
                if hz > 0:
                    import math
                    m = int(round(69 + 12 * math.log2(hz / 440.0)))
                    midi_notes.append(m)

            if not midi_notes:
                continue

            # Use primary MIDI note
            primary_midi = max(0, min(127, int(round(sum(midi_notes) / len(midi_notes)))))
            start_tick = _seconds_to_ticks(seg_start_t, DEFAULT_TICKS_PER_BEAT, tempo_us)
            end_tick = _seconds_to_ticks(seg_end_t, DEFAULT_TICKS_PER_BEAT, tempo_us)

            # Ensure note has minimum duration of at least 24 ticks (~25ms)
            if end_tick <= start_tick:
                end_tick = start_tick + 24

            # Initial pitch bend
            init_cents = pts[0].get("cents", 0)
            init_wheel = _cents_to_pitchwheel(init_cents)
            raw_events.append((start_tick, 1, Message("pitchwheel", pitch=init_wheel, channel=ch)))
            # Note On (Velocity 80)
            raw_events.append((start_tick, 2, Message("note_on", note=primary_midi, velocity=80, channel=ch)))

            # Pitch bend automation throughout the contour
            # Sub-sample every ~30ms to avoid overwhelming MIDI stream
            last_bend_tick = start_tick
            for pt in pts[1:-1]:
                pt_tick = _seconds_to_ticks(pt["t"], DEFAULT_TICKS_PER_BEAT, tempo_us)
                if pt_tick - last_bend_tick >= 24:
                    cents = pt.get("cents", 0)
                    wheel = _cents_to_pitchwheel(cents)
                    raw_events.append((pt_tick, 1, Message("pitchwheel", pitch=wheel, channel=ch)))
                    last_bend_tick = pt_tick

            # Note Off
            raw_events.append((end_tick, 0, Message("note_off", note=primary_midi, velocity=64, channel=ch)))
            # Reset pitch bend to 0
            raw_events.append((end_tick, 1, Message("pitchwheel", pitch=0, channel=ch)))

        # Sort all events chronologically by tick, then by priority
        raw_events.sort(key=lambda x: (x[0], x[1]))

        # Convert absolute ticks to delta ticks
        current_tick = 0
        for ev_tick, _, msg in raw_events:
            delta = max(0, ev_tick - current_tick)
            msg.time = delta
            track.append(msg)
            current_tick = ev_tick

        track.append(MetaMessage("end_of_track", time=0))
        mid.tracks.append(track)

    # Save to in-memory bytes buffer
    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()
