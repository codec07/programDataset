# Program Dataset

A curated, language-by-language collection of **single-file programs** built to be a clean, practical dataset for training and evaluating code models. It contains 110 dependency-free Python programs plus 15 examples for popular third-party libraries.

Every program is standalone, readable, and runnable with a standard interpreter — no package installs, no build step, no hidden project scaffolding. The point is to give models high-quality examples of *complete* programs: a real CLI, real edge-case handling, real docstrings, real tests-by-running.

---

## Why this exists

Most code datasets are either tiny snippets or giant repos. This sits in between:

- **Single file** → trivially chunkable into one training sample, one prompt/completion pair, or one repo-level task.
- **Complete** → has a `main()`, argument parsing, validation, and a docstring, so a model learns the whole shape of a program, not just an algorithm.
- **Runnable** → every file can be executed and tested, which makes it usable for execution-feedback training, unit-test generation, and bug-injection benchmarks.
- **Diverse** → games, algorithms, CLIs, data tools, async systems, graphics, simulations.

---

## Repository layout

```
VIBE_DATASET/
├── README.md
├── DATASET_CARD.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── tools/
│   └── build_manifest.py       # scans language folders → manifest.json + stats
└── Python/
    ├── README.md               # index of all Python programs
    ├── cli_text/               # CLIs, text processing, file tooling
    ├── algorithms/             # data structures, algorithms, math
    ├── games/                  # terminal games, tkinter games, simulations
    ├── data_web/               # CSV/SQLite, HTTP, automation, reporting
    ├── advanced/               # asyncio, multiprocessing, graphics, audio
    └── libraryCodeSet/         # examples for NumPy, pandas, Flask, FastAPI, …
```

Each language gets its own top-level folder. Each domain gets a subfolder. One program = one file.

---

## Python programs at a glance

| Folder | Focus | Examples |
|---|---|---|
| `Python/cli_text` | Command-line utilities & text/file tooling | `word_frequency.py`, `log_analyzer.py`, `batch_rename.py`, `todo_cli.py` |
| `Python/algorithms` | Data structures, algorithms, math | `graph_algorithms.py`, `trie.py`, `sudoku_solver.py`, `bigint_arithmetic.py` |
| `Python/games` | Playable games & simulations | `tetris.py`, `minesweeper.py`, `conway_life.py`, `predator_prey.py` |
| `Python/data_web` | Data, SQLite, HTTP, automation | `sqlite_crud.py`, `rest_api_server.py`, `data_pipeline.py`, `svg_chart.py` |
| `Python/advanced` | Concurrency, graphics, audio, systems | `asyncio_worker_pool.py`, `png_writer.py`, `wav_synth.py`, `mini_shell.py` |
| `Python/libraryCodeSet` | Third-party library examples *(not runtime-tested)* | `numpy_examples.py`, `pandas_examples.py`, `flask_examples.py`, `pydantic_examples.py` |

See [`Python/README.md`](Python/README.md) for the full index.

---

## Quick start

No installation required — Python 3.10+ and the standard library.

```bash
# Run any dependency-free program
python Python/algorithms/sorting_algorithms.py
python Python/cli_text/word_frequency.py --help
python Python/games/tic_tac_toe.py

# Library examples need their packages first (see the folder README)
pip install -r Python/libraryCodeSet/requirements.txt
python Python/libraryCodeSet/numpy_examples.py

# Generate a dataset manifest (file count, line counts, sha256)
python tools/build_manifest.py
```

GUI programs use `tkinter` (bundled with Python on Windows and macOS). On Linux you may need `sudo apt install python3-tk`.

---

## Quality standards

The 110 core programs follow all six rules below. The 15 files in
`Python/libraryCodeSet` are an intentional exception: they need third-party
packages, were only syntax-checked, and are documented as untested examples in
that folder's README.

Every core program in this repository is expected to:

1. Be **self-contained** — standard library only, no `pip install`.
2. Be **complete** — module docstring, type hints, decomposed functions, `if __name__ == "__main__": main()`.
3. Be **runnable** — compiles cleanly and executes without crashing.
4. Be **defensive** — validates input, handles missing files/bad data, exits with a useful message.
5. Be **honest** — no placeholder logic, no `TODO`, no canned output pretending to be computation.
6. Be **portable** — Windows, macOS, and Linux; UTF-8 everywhere.

---

## Using it as training data

Suggested sample format (one program per record):

```json
{
  "id": "python/algorithms/trie.py",
  "language": "python",
  "domain": "algorithms",
  "path": "Python/algorithms/trie.py",
  "lines": 214,
  "sha256": "…",
  "content": "…"
}
```

Run `python tools/build_manifest.py` to produce `manifest.json` with those fields for the whole repository.

Good uses: supervised fine-tuning on complete programs, instruction tuning (`"write a CLI that …"` → file), execution-feedback data, test-generation tasks, and bug-localization benchmarks. See [`DATASET_CARD.md`](DATASET_CARD.md) for limitations before training on it.

---

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version: one file, stdlib only, tested, documented, and placed in the right language/domain folder. Do not reformat or rewrite other people's programs.

---

## License

MIT — see [`LICENSE`](LICENSE).
