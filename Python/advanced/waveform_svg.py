"""Turn a WAV file (or a generated demo tone) into a polished SVG waveform.

The renderer computes per-pixel min/max envelopes, draws an anti-aliased
filled waveform, adds a grid, axis labels, and summary statistics. Everything
is emitted as plain SVG text, so the result opens in any browser.

Usage:
    python waveform_svg.py --input wav_demo.wav --output waveform.svg
    python waveform_svg.py --demo --output demo_wave.svg
    python waveform_svg.py --demo --width 1400 --height 420
"""

from __future__ import annotations

import argparse
import math
import sys
import wave
from array import array
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class Signal:
    samples: list[float]
    sample_rate: int
    label: str

    @property
    def duration(self) -> float:
        return len(self.samples) / self.sample_rate if self.sample_rate else 0.0

    @property
    def peak(self) -> float:
        return max((abs(sample) for sample in self.samples), default=0.0)

    @property
    def rms(self) -> float:
        if not self.samples:
            return 0.0
        return math.sqrt(sum(value * value for value in self.samples) / len(self.samples))


def read_wav(path: str | Path) -> Signal:
    """Read mono/stereo PCM WAV data and normalize it to [-1, 1]."""
    source = Path(path)
    with wave.open(str(source), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.getnframes()
        raw = handle.readframes(frames)
    if channels < 1 or rate <= 0:
        raise ValueError("invalid WAV channel count or sample rate")

    if width == 1:
        values = [(byte - 128) / 128.0 for byte in raw]
    elif width == 2:
        pcm = array("h")
        pcm.frombytes(raw[: len(raw) - (len(raw) % 2)])
        if sys.byteorder == "big":
            pcm.byteswap()
        values = [value / 32768.0 for value in pcm]
    elif width == 4:
        pcm = array("i")
        pcm.frombytes(raw[: len(raw) - (len(raw) % 4)])
        if sys.byteorder == "big":
            pcm.byteswap()
        values = [value / 2_147_483_648.0 for value in pcm]
    else:
        raise ValueError(f"unsupported WAV sample width: {width} bytes")

    if channels > 1:
        mono: list[float] = []
        for start in range(0, len(values) - channels + 1, channels):
            mono.append(sum(values[start : start + channels]) / channels)
        values = mono
    return Signal(values, rate, source.name)


def demo_signal(sample_rate: int = 16_000, duration: float = 2.4) -> Signal:
    """Generate a chirp with harmonics and a gentle envelope."""
    count = int(sample_rate * duration)
    samples: list[float] = []
    phase = 0.0
    for index in range(count):
        t = index / sample_rate
        progress = t / duration
        frequency = 160.0 + 740.0 * progress * progress
        phase = (phase + frequency / sample_rate) % 1.0
        attack = min(1.0, t / 0.12)
        release = min(1.0, (duration - t) / 0.35)
        envelope = attack * release
        tremolo = 0.82 + 0.18 * math.sin(2.0 * math.pi * 5.0 * t)
        value = (
            math.sin(2.0 * math.pi * phase)
            + 0.32 * math.sin(4.0 * math.pi * phase)
            + 0.12 * math.sin(6.0 * math.pi * phase)
        )
        samples.append(0.55 * envelope * tremolo * value)
    return Signal(samples, sample_rate, "procedural chirp")


def envelope(signal: Signal, columns: int) -> list[tuple[float, float]]:
    """Return (minimum, maximum) pairs for each horizontal pixel bucket."""
    if not signal.samples:
        return [(0.0, 0.0)] * columns
    result: list[tuple[float, float]] = []
    for column in range(columns):
        start = int(column * len(signal.samples) / columns)
        end = max(start + 1, int((column + 1) * len(signal.samples) / columns))
        block = signal.samples[start:end]
        result.append((min(block), max(block)))
    return result


def _fmt_time(seconds: float) -> str:
    return f"{seconds:.2f}s"


def render_svg(
    signal: Signal,
    *,
    width: int = 1000,
    height: int = 360,
    columns: int = 700,
) -> str:
    """Build the complete SVG document as a string."""
    if width < 320 or height < 180:
        raise ValueError("SVG dimensions are too small")
    margin_left, margin_right = 68, 34
    margin_top, margin_bottom = 74, 58
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    middle = margin_top + plot_height / 2
    amplitude = max(0.001, signal.peak)
    scale = (plot_height * 0.46) / amplitude
    points = envelope(signal, columns)

    upper: list[str] = []
    lower: list[str] = []
    for index, (low, high) in enumerate(points):
        x = margin_left + (index / max(1, columns - 1)) * plot_width
        upper.append(f"{x:.2f},{middle - high * scale:.2f}")
        lower.append(f"{x:.2f},{middle - low * scale:.2f}")
    polygon = " ".join(upper + list(reversed(lower)))

    grid_parts: list[str] = []
    for step in range(9):
        x = margin_left + plot_width * step / 8
        grid_parts.append(
            f'<line x1="{x:.1f}" y1="{margin_top}" x2="{x:.1f}" '
            f'y2="{margin_top + plot_height}" class="grid"/>'
        )
    for step in range(5):
        y = margin_top + plot_height * step / 4
        grid_parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_width}" '
            f'y2="{y:.1f}" class="grid"/>'
        )

    labels: list[str] = []
    for step in range(5):
        seconds = signal.duration * step / 4
        x = margin_left + plot_width * step / 4
        labels.append(
            f'<text x="{x:.1f}" y="{margin_top + plot_height + 28}" '
            f'class="axis" text-anchor="middle">{_fmt_time(seconds)}</text>'
        )
    for fraction in (-1.0, 0.0, 1.0):
        y = middle - fraction * amplitude * scale
        labels.append(
            f'<text x="{margin_left - 12}" y="{y + 4:.1f}" class="axis" '
            f'text-anchor="end">{fraction:+.1f}</text>'
        )

    title = escape(signal.label)
    peak_db = 20.0 * math.log10(signal.peak) if signal.peak > 0 else -math.inf
    stats = (
        f"{signal.duration:.2f} s  |  {signal.sample_rate:,} Hz  |  "
        f"peak {signal.peak:.2f} ({peak_db:.1f} dBFS)  |  RMS {signal.rms:.3f}"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" role="img" aria-label="Waveform of {title}">
  <defs>
    <linearGradient id="wave" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#52e0b8"/>
      <stop offset="55%" stop-color="#58b7ff"/>
      <stop offset="100%" stop-color="#c084fc"/>
    </linearGradient>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#121923"/>
      <stop offset="100%" stop-color="#0a0e14"/>
    </linearGradient>
    <filter id="glow" x="-10%" y="-20%" width="120%" height="140%">
      <feGaussianBlur stdDeviation="3.2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="{width}" height="{height}" rx="14" fill="url(#bg)"/>
  <text x="{margin_left}" y="38" class="title">{title}</text>
  <text x="{margin_left}" y="58" class="subtitle">{escape(stats)}</text>
  <g>{''.join(grid_parts)}</g>
  <line x1="{margin_left}" y1="{middle:.1f}" x2="{margin_left + plot_width}"
        y2="{middle:.1f}" class="center"/>
  <polygon points="{polygon}" fill="url(#wave)" fill-opacity="0.86" filter="url(#glow)"/>
  <g>{''.join(labels)}</g>
  <style>
    .title {{ fill:#e7eef8; font:600 20px 'Segoe UI',system-ui,sans-serif; }}
    .subtitle {{ fill:#7f93aa; font:13px 'Segoe UI',system-ui,sans-serif; }}
    .axis {{ fill:#61748a; font:11px 'Consolas',monospace; }}
    .grid {{ stroke:#26364a; stroke-width:1; stroke-dasharray:2 5; }}
    .center {{ stroke:#3b5068; stroke-width:1; }}
  </style>
</svg>
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render WAV audio as an SVG waveform.")
    parser.add_argument("--input", "-i", help="input .wav file")
    parser.add_argument("--output", "-o", default="waveform.svg")
    parser.add_argument("--demo", action="store_true", help="use a generated chirp")
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--columns", type=int, default=700)
    args = parser.parse_args(argv)

    try:
        if args.input and not args.demo:
            signal = read_wav(args.input)
        else:
            signal = demo_signal()
        svg = render_svg(
            signal, width=args.width, height=args.height, columns=args.columns
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(svg, encoding="utf-8")
    except (OSError, ValueError, wave.Error) as exc:
        parser.error(str(exc))

    print(
        f"wrote {output} ({len(svg)} chars, {args.width}x{args.height}) from "
        f"{signal.label!r}: {signal.duration:.2f}s, peak={signal.peak:.3f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
