# Advanced Python: 22 Standalone Programs

A collection of self-contained Python 3.10+ programs covering concurrency,
decorators, generative graphics/audio, and systems-level utilities. Every file
uses only the standard library, has a module docstring and `argparse` CLI, and
can be executed directly from this directory.

## Quick Start

```powershell
cd Python/advanced
python asyncio_worker_pool.py --workers 4 --jobs 16 --cancel
python png_writer.py --output demo.png --size 320x200 --pattern plasma
python wav_synth.py --output demo.wav
python mandelbrot.py --size 640x480 --iterations 180 --output mandelbrot.png
```

Each program accepts `--help`. Demos terminate on their own; generated files
are written to the current directory (or the path you provide). No packages
need to be installed.

### Platform Notes

- **Windows multiprocessing**: `multiprocessing_pipeline.py` uses the `spawn`
  start method and all process entry points plus its `main()` are guarded by
  `if __name__ == "__main__"`.
- **Turtle graphics**: `fractal_tree.py` and `spirograph.py` never create a
  window at import time. Use `--save output.ps` for headless PostScript export;
  run without `--save` (or add `--preview`) to open the interactive viewer.
- **Terminal UI**: `terminal_dashboard.py` and `progress_bar.py` use ANSI
  sequences. They animate in a TTY and print a readable summary when output is
  redirected. `progress_bar.py --unicode` falls back to ASCII when the output
  encoding cannot represent block characters.
- **Artifacts**: PNG, PPM, WAV, SVG, and PostScript writers were checked by
  parsing the generated files back with independent readers.

---

## Concurrency and Async

### `asyncio_worker_pool.py`

A fixed-size asyncio worker pool with a bounded queue, future-based results,
error isolation, cancellation, and graceful shutdown.

**Demonstrates:** coroutine and plain-callable jobs, `asyncio.Queue`, a
`gather`-based shutdown, peak-concurrency tracking, and injected failures that
do not kill workers.

```powershell
python asyncio_worker_pool.py --workers 4 --jobs 16 --cancel
```

### `thread_pool_tasks.py`

Named task submission over `ThreadPoolExecutor` with structured outcomes,
batch timeouts, cancellation, and deterministic shutdown.

**Demonstrates:** `concurrent.futures`, `as_completed`, `Future.cancel()`,
thread-safe counters, timeout handling, and task-error propagation.

```powershell
python thread_pool_tasks.py --workers 4 --tasks 12
python thread_pool_tasks.py --timeout 0.05
```

### `multiprocessing_pipeline.py`

A spawn-safe three-stage pipeline: producer -> transform workers -> collector.

**Demonstrates:** `multiprocessing.Process`, bounded queues, sentinels, error
reporting without worker crashes, parent-side deadlines, and forced cleanup of
stuck children. Works on Windows with no `fork` assumptions.

```powershell
python multiprocessing_pipeline.py --items 60 --workers 3
python multiprocessing_pipeline.py --items 30 --workers 2 --fail-at 9
```

### `producer_consumer.py`

A bounded `queue.Queue` pipeline with multiple producers, consumers, a stop
event, and one stop sentinel per consumer.

**Demonstrates:** backpressure, daemon threads, sentinel-based termination,
queue task accounting, and per-item error collection (with an optional strict
mode that re-raises the first failure).

```powershell
python producer_consumer.py
python producer_consumer.py --producers 4 --consumers 2 --items 20 --strict
```

### `async_rate_limiter.py`

An asyncio token-bucket limiter with burst capacity, refill rate, timeouts, and
`async with` support.

**Demonstrates:** token accounting under an `asyncio.Lock`, concurrent waiters,
timeout propagation, and measuring achieved request spacing.

```powershell
python async_rate_limiter.py --tasks 16 --capacity 5 --rate 10
```

### `async_crawler_sim.py`

An offline crawler simulation with a fake delayed fetcher, worker pool, URL
deduplication, depth/page limits, and per-page errors.

**Demonstrates:** an `asyncio.Queue` frontier, deduplication and depth rules,
concurrency limits, cancellation-safe worker shutdown, and no real network
access.

```powershell
python async_crawler_sim.py --workers 4 --max-pages 20 --max-depth 2
```

### `async_task_scheduler.py`

A delayed, priority-aware scheduler with a heap of due jobs and a worker pool.

**Demonstrates:** timer dispatch, priority/insertion ordering, future
cancellation, async and sync jobs, aggregated failures, and clean shutdown of
unscheduled work.

```powershell
python async_task_scheduler.py --workers 3 --jobs 10
```

---

## Decorators and Events

### `retry_decorator.py`

A retry decorator that supports sync and async functions, exception filtering,
capped exponential backoff, jitter, and an `on_retry` callback.

**Demonstrates:** `functools.wraps`, `inspect.iscoroutinefunction`, ParamSpec
typing, callback handling, and re-raising the original exception after the
last attempt.

```powershell
python retry_decorator.py --demo
```

### `cache_decorator.py`

A thread-safe LRU cache decorator with optional TTL, statistics, and async
deduplication.

**Demonstrates:** `OrderedDict` LRU eviction, monotonic TTL checks, per-key
async locks, cache hits/misses/evictions, and concurrent request coalescing.

```powershell
python cache_decorator.py --demo
```

### `event_emitter.py`

A thread-safe event emitter with wildcard listeners, one-shot handlers,
synchronous dispatch, and concurrent async dispatch.

**Demonstrates:** immutable event records, decorator subscription, handler
removal, error aggregation via `EventError`, and mixed sync/async handlers.

```powershell
python event_emitter.py --demo
```

---

## Storage and Systems Utilities

### `key_value_store.py`

A string-keyed store backed by an append-only JSONL log with tombstones and
atomic compaction.

**Demonstrates:** replaying a log into an index, durable appends (`fsync`),
`os.replace` atomic compaction, tombstone accounting, reopening persisted state,
and a CLI for `set/get/delete/list/compact/info`.

```powershell
python key_value_store.py --demo
python key_value_store.py --db data.jsonl set user '{"name": "Ada"}'
python key_value_store.py --db data.jsonl get user
```

### `mini_shell.py`

A small safe shell with `pwd`, `cd`, `ls`, `cat`, `echo`, `clear`, `help`, and
`exit` built-ins.

**Demonstrates:** `shlex` tokenization, command dispatch, explicit working
directory state, `subprocess.run(..., shell=False)` with argument lists, timeouts,
and safety gates. External commands are disabled by default; destructive names
stay blocked even when external execution is enabled.

```powershell
python mini_shell.py --demo
python mini_shell.py -c "pwd" -c "ls"
python mini_shell.py --allow-external -c "python --version"
```

---

## Images, Audio, and Generative Graphics

### `png_writer.py`

A from-scratch 8-bit RGB PNG encoder using `struct`, `zlib`, and CRC-32.

**Demonstrates:** PNG signature and chunk layout, IHDR/IDAT/IEND, big-endian
lengths, scanline filtering, CRC calculation, and generated gradient/checker/
plasma test images.

```powershell
python png_writer.py --output gradient.png --size 320x200
python png_writer.py --pattern plasma --size 256x256 --output plasma.png
```

### `image_processor.py`

A pure-Python PPM toolkit supporting P6/P3 input, P6/P3 output, grayscale, box
blur, Sobel edge detection, and bilinear resizing.

**Demonstrates:** binary and ASCII PPM parsing (including comments), separable
convolution, clamped-edge kernels, interpolation, and a generated test card.
`--demo` writes a source image plus four processed outputs.

```powershell
python image_processor.py --demo --output-dir demo_images
python image_processor.py input.ppm --op blur --radius 3 -o blurred.ppm
python image_processor.py input.ppm --op resize --size 320x240 -o small.ppm
python image_processor.py input.ppm --op gray --ascii -o gray_p3.ppm
```

### `ascii_art.py`

Converts PPM or PNG images into character art and includes a procedural sunset
landscape demo.

**Demonstrates:** a minimal PNG decoder (8-bit grayscale/RGB/RGBA, all filter
types, CRC checks), PPM parsing, cell-averaged luminance sampling, aspect-ratio
correction, and custom character ramps.

```powershell
python ascii_art.py --demo --width 90
python ascii_art.py --demo --save-demo sunset.ppm
python ascii_art.py screenshot.png --width 100 --invert -o art.txt
```

### `wav_synth.py`

Real 16-bit mono WAV synthesis with sine, square, sawtooth, triangle, and noise
oscillators, chords, sequences, and ADSR envelopes.

**Demonstrates:** the `wave` module, phase accumulation, envelope evaluation,
note-name to frequency conversion, safe normalization, and a built-in arpeggio.
Every invocation produces a valid RIFF/WAVE file.

```powershell
python wav_synth.py
python wav_synth.py --note A4 --duration 2 --waveform sine
python wav_synth.py --chord C4,E4,G4 --duration 1.5 --output chord.wav
python wav_synth.py --sequence "C4:0.2,E4:0.2,G4:0.2,R:0.1,C5:0.8"
```

### `waveform_svg.py`

Renders a WAV file, or a generated chirp, as a styled SVG waveform with grids,
labels, peak/RMS statistics, and a gradient fill.

**Demonstrates:** WAV decoding for 8/16/32-bit PCM, stereo-to-mono mixing,
min/max envelope bucketing, and XML/SVG generation with escaped text.

```powershell
python waveform_svg.py --input wav_demo.wav --output waveform.svg
python waveform_svg.py --demo --output demo_wave.svg --width 1200
```

### `mandelbrot.py`

Renders the Mandelbrot set with smooth escape-time coloring to PNG or PPM.

**Demonstrates:** configurable dimensions/iterations/zoom/center, continuous
coloring with a five-stop palette, and a dependency-free PNG encoder embedded in
the program.

```powershell
python mandelbrot.py --size 640x480 --iterations 180 --output mandelbrot.png
python mandelbrot.py --size 64x64 --iterations 80 --output tiny.png
python mandelbrot.py --size 400x300 --zoom 8 --center=-0.743643,0.131825 -o zoom.ppm
```

### `fractal_tree.py`

A recursive branching tree rendered with turtle graphics or exported to
PostScript.

**Demonstrates:** geometry generation independent of the GUI, depth-based
width/color blending, optional seeded variation, lazy turtle import, and
headless `--save` output.

```powershell
python fractal_tree.py --save tree.ps
python fractal_tree.py --depth 11 --angle 28 --seed 7 --save organic.ps
python fractal_tree.py --preview
```

### `spirograph.py`

Generates hypotrochoid spirograph art in turtle or as a PostScript page.

**Demonstrates:** parametric curves, automatic bounds fitting, palette
interpolation, per-segment coloring, lazy GUI import, and deterministic export.

```powershell
python spirograph.py --save star.ps
python spirograph.py --R 220 --r 61 --d 120 --turns 8 --save woven.ps
python spirograph.py --R 180 --r 40 --d 90 --turns 20 --preview
```

---

## Terminal UI

### `terminal_dashboard.py`

A live ANSI dashboard with simulated queue, CPU, latency, throughput, and error
telemetry.

**Demonstrates:** alternate-screen handling, cursor hide/restore in `finally`,
in-place redraw, sparklines, bar meters, terminal-width awareness, and a
non-TTY summary fallback.

```powershell
python terminal_dashboard.py
python terminal_dashboard.py --duration 5 --fps 12
```

### `progress_bar.py`

Single-line ANSI progress bars with rate, ETA, milestone fallback, and optional
Unicode blocks.

**Demonstrates:** `ESC[2K` line clearing, throttled repainting, TTY detection,
encoding-aware Unicode fallback, context-manager cleanup, and a small `track()`
iterator helper.

```powershell
python progress_bar.py
python progress_bar.py --duration 4 --width 50 --unicode
python progress_bar.py --duration 1 --no-color
```

---

## Verification Performed

- `python -m py_compile` was run on all 22 programs.
- Every non-GUI program was executed end-to-end with small parameters.
- Asyncio and multiprocessing demos completed in under two seconds each in the
  test environment (well below the 15-second budget).
- PNG outputs were checked for signature, chunk CRCs, IHDR fields, and decoded
  raster dimensions.
- PPM outputs were read back as both P6 and P3; WAV files were opened with the
  `wave` module; SVG and PostScript outputs were checked for complete documents.
- `fractal_tree.py` and `spirograph.py` were tested through `--save`; importing
  them was separately checked to confirm no turtle window is created.
