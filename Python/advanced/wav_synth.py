"""Synthesize real 16-bit mono WAV files with the standard ``wave`` module.

Supports sine, square, sawtooth, triangle, and noise oscillators, multiple
simultaneous frequencies (chords), and ADSR envelopes. The default demo
renders a short arpeggio followed by a sustained chord.

Usage:
    python wav_synth.py                          # writes wav_demo.wav
    python wav_synth.py --note A4 --duration 2 --waveform sine
    python wav_synth.py --chord C4,E4,G4 --duration 1.5 --output chord.wav
    python wav_synth.py --sequence "C4:0.2,E4:0.2,G4:0.2,R:0.1,C5:0.8"

Notes use scientific pitch notation (C4, F#3, Bb5); ``R`` is a rest. A chord
inside a sequence is written with ``+`` (for example ``C4+E4+G4:0.8``).
"""

from __future__ import annotations

import argparse
import math
import random
import re
import sys
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

SAMPLE_RATE = 44_100
WAVEFORMS = ("sine", "square", "saw", "triangle", "noise")
NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d+)$")
SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


@dataclass(frozen=True, slots=True)
class ADSR:
    """Envelope times in seconds plus a sustain level from 0 to 1."""

    attack: float = 0.02
    decay: float = 0.10
    sustain: float = 0.70
    release: float = 0.20

    def validate(self) -> None:
        if min(self.attack, self.decay, self.release) < 0:
            raise ValueError("ADSR times cannot be negative")
        if not 0 <= self.sustain <= 1:
            raise ValueError("sustain must be between 0 and 1")


def note_to_frequency(note: str) -> float:
    """Convert a note such as ``A4`` or ``C#5`` to its frequency in Hz."""
    text = note.strip()
    if text.upper() == "R":
        return 0.0
    match = NOTE_RE.match(text)
    if not match:
        raise ValueError(f"invalid note {note!r}")
    letter, accidental, octave_text = match.groups()
    midi = (int(octave_text) + 1) * 12 + SEMITONES[letter.upper()]
    midi += 1 if accidental == "#" else -1 if accidental == "b" else 0
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def envelope_value(t: float, duration: float, adsr: ADSR) -> float:
    """Evaluate an ADSR envelope at time ``t``."""
    if duration <= 0:
        return 0.0
    attack = min(adsr.attack, duration)
    decay = min(adsr.decay, max(0.0, duration - attack))
    release = min(adsr.release, max(0.0, duration - attack - decay))
    release_start = duration - release
    if t < 0:
        return 0.0
    if attack > 0 and t < attack:
        return t / attack
    if t < attack + decay and decay > 0:
        progress = (t - attack) / decay
        return 1.0 + (adsr.sustain - 1.0) * progress
    if t < release_start:
        return adsr.sustain
    if release > 0:
        return adsr.sustain * max(0.0, (duration - t) / release)
    return 0.0


def _oscillator(waveform: str, phase: float, rng: random.Random) -> float:
    if waveform == "sine":
        return math.sin(2.0 * math.pi * phase)
    if waveform == "square":
        return 1.0 if phase < 0.5 else -1.0
    if waveform == "saw":
        return 2.0 * phase - 1.0
    if waveform == "triangle":
        return 4.0 * abs(phase - 0.5) - 1.0
    if waveform == "noise":
        return rng.uniform(-1.0, 1.0)
    raise ValueError(f"unknown waveform {waveform!r}")


def synthesize(
    frequencies: Sequence[float],
    duration: float,
    *,
    waveform: str = "sine",
    amplitude: float = 0.28,
    adsr: ADSR = ADSR(),
    sample_rate: int = SAMPLE_RATE,
    seed: int = 0,
) -> list[float]:
    """Render one tone or chord as floating-point samples in [-1, 1]."""
    if duration <= 0:
        raise ValueError("duration must be positive")
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    if not 0 < amplitude <= 1:
        raise ValueError("amplitude must be in (0, 1]")
    if waveform not in WAVEFORMS:
        raise ValueError(f"waveform must be one of {WAVEFORMS}")
    adsr.validate()
    active = [frequency for frequency in frequencies if frequency > 0]
    count = int(round(duration * sample_rate))
    if not active:
        return [0.0] * count
    rng = random.Random(seed)
    phases = [0.0] * len(active)
    scale = amplitude / math.sqrt(len(active))
    samples: list[float] = []
    for index in range(count):
        t = index / sample_rate
        env = envelope_value(t, duration, adsr)
        value = 0.0
        for voice, frequency in enumerate(active):
            value += _oscillator(waveform, phases[voice], rng) * scale
            phases[voice] = (phases[voice] + frequency / sample_rate) % 1.0
        samples.append(max(-1.0, min(1.0, value * env)))
    return samples


def parse_sequence(text: str) -> list[tuple[list[str], float]]:
    """Parse ``NOTE[:duration],...`` into note groups and durations."""
    entries: list[tuple[list[str], float]] = []
    for raw in text.split(","):
        part = raw.strip()
        if not part:
            continue
        if ":" in part:
            notes_text, duration_text = part.rsplit(":", 1)
            duration = float(duration_text)
        else:
            notes_text, duration = part, 0.35
        if duration <= 0:
            raise ValueError("sequence durations must be positive")
        notes = [note.strip() for note in notes_text.split("+") if note.strip()]
        if not notes:
            raise ValueError(f"empty note group in {part!r}")
        entries.append((notes, duration))
    if not entries:
        raise ValueError("sequence is empty")
    return entries


def render_sequence(
    entries: Sequence[tuple[Sequence[str], float]],
    *,
    waveform: str,
    amplitude: float,
    adsr: ADSR,
    sample_rate: int,
    seed: int = 0,
) -> list[float]:
    """Concatenate separately enveloped notes or chords."""
    output: list[float] = []
    for index, (notes, duration) in enumerate(entries):
        frequencies = [note_to_frequency(note) for note in notes]
        output.extend(
            synthesize(
                frequencies,
                duration,
                waveform=waveform,
                amplitude=amplitude,
                adsr=adsr,
                sample_rate=sample_rate,
                seed=seed + index,
            )
        )
    return output


def write_wav(path: str | Path, samples: Sequence[float], sample_rate: int) -> Path:
    """Write normalized float samples as signed 16-bit PCM."""
    if not samples:
        raise ValueError("cannot write an empty waveform")
    pcm = array("h", (int(max(-1.0, min(1.0, sample)) * 32767) for sample in samples))
    if array("h").itemsize != 2:
        raise RuntimeError("platform does not provide 16-bit signed shorts")
    if sys.byteorder == "big":
        pcm.byteswap()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return destination


def demo_sequence() -> list[tuple[list[str], float]]:
    return parse_sequence(
        "C4:0.20,E4:0.20,G4:0.20,C5:0.30,R:0.08,"
        "A3:0.20,C4:0.20,E4:0.20,A4:0.30,R:0.08,"
        "F3+C4:0.70,C4+E4+G4+B4:0.90"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synthesize a WAV file from scratch.")
    parser.add_argument("--output", "-o", default="wav_demo.wav")
    parser.add_argument("--note", help="single note, e.g. A4")
    parser.add_argument("--chord", help="comma-separated notes, e.g. C4,E4,G4")
    parser.add_argument("--sequence", help="comma-separated NOTE:duration entries")
    parser.add_argument("--duration", type=float, default=2.0, help="single note duration")
    parser.add_argument("--waveform", choices=WAVEFORMS, default="sine")
    parser.add_argument("--amplitude", type=float, default=0.28)
    parser.add_argument("--sample-rate", type=int, default=SAMPLE_RATE)
    parser.add_argument("--seed", type=int, default=7, help="noise/demo randomization")
    parser.add_argument("--attack", type=float, default=0.02)
    parser.add_argument("--decay", type=float, default=0.10)
    parser.add_argument("--sustain", type=float, default=0.70)
    parser.add_argument("--release", type=float, default=0.20)
    args = parser.parse_args(argv)
    if not 1_000 <= args.sample_rate <= 384_000:
        parser.error("sample rate must be between 1000 and 384000")

    adsr = ADSR(args.attack, args.decay, args.sustain, args.release)
    try:
        if args.sequence:
            entries = parse_sequence(args.sequence)
            samples = render_sequence(
                entries,
                waveform=args.waveform,
                amplitude=args.amplitude,
                adsr=adsr,
                sample_rate=args.sample_rate,
                seed=args.seed,
            )
            label = f"sequence ({len(entries)} events)"
        elif args.note or args.chord:
            note_text = args.chord if args.chord else args.note
            notes = [part.strip() for part in note_text.split(",") if part.strip()]
            frequencies = [note_to_frequency(note) for note in notes]
            samples = synthesize(
                frequencies,
                args.duration,
                waveform=args.waveform,
                amplitude=args.amplitude,
                adsr=adsr,
                sample_rate=args.sample_rate,
                seed=args.seed,
            )
            label = "+".join(notes)
        else:
            entries = demo_sequence()
            samples = render_sequence(
                entries,
                waveform=args.waveform,
                amplitude=args.amplitude,
                adsr=adsr,
                sample_rate=args.sample_rate,
                seed=args.seed,
            )
            label = "built-in arpeggio demo"
        path = write_wav(args.output, samples, args.sample_rate)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    seconds = len(samples) / args.sample_rate
    print(
        f"wrote {path}: {seconds:.2f}s, {args.sample_rate} Hz, 16-bit mono, "
        f"{len(samples)} frames, waveform={args.waveform}"
    )
    print(f"source: {label}")
    print(f"peak sample: {max(abs(sample) for sample in samples):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
