# Contributing

Thanks for helping grow the dataset. The rules are deliberately strict so the corpus stays clean.

## The one rule that matters

**One program = one self-contained file.** No packages, no shared helper modules, no imports between files in this repo.

## Requirements for a new program

1. **Location:** `<Language>/<domain>/<snake_case_name>.py`, e.g. `Python/algorithms/trie.py`.
   Pick the closest existing domain. Create a new domain only if at least 5 programs would live there.
2. **Standard library only.** No `pip install`, no vendored third-party code.
3. **Python 3.10+.** Do not rely on 3.11/3.12-only syntax.
4. **Complete shape:**
   - Module docstring: what it does, how to run it, one example.
   - Type hints on public functions.
   - Small, named functions instead of one giant `main`.
   - `argparse` for CLIs.
   - `if __name__ == "__main__": main()`.
5. **Defensive:** validate input, handle missing files/malformed data, print errors to `stderr`, exit non-zero on failure.
6. **Portable:** `encoding="utf-8"` on text I/O; no hardcoded absolute paths; no shell-specific commands.
7. **No destructive defaults:** tools that delete or overwrite must support `--dry-run` and/or require `--force`.
8. **No TODO, no stub, no fake output, no `pass` placeholders.**

## Testing before you open a pull request

```bash
python -m py_compile Python/<domain>/<file>.py
python Python/<domain>/<file>.py --help
python Python/<domain>/<file>.py          # or its demo/self-test mode
```

- GUI programs must not open a window on import; verify with:
  `python -c "import importlib; importlib.import_module('module_name')"`
- Network programs must have an offline/demo path so tests never hang.
- Simulations and concurrent demos must terminate on their own.

## Naming and style

- Files: `snake_case.py`, descriptive, no numeric prefixes.
- No duplicate concepts across folders. Check the index in `Python/README.md` first.
- Four-space indentation, ~100-column soft limit, double quotes, `from __future__ import annotations` where it helps.
- Keep files roughly 80–300 lines. If it needs 1000, it probably belongs in a different dataset.

## Updating the index and manifest

- Add one line for your program to the relevant `<Language>/README.md`.
- Regenerate metadata:

```bash
python tools/build_manifest.py
```

Commit the updated `manifest.json` alongside your program.

## What not to do

- Do not reformat, rename, or "improve" unrelated files in the same PR.
- Do not add generated artifacts (`__pycache__`, `.wav`, `.png`, `*.db`).
- Do not add a framework, package config, or CI that changes how programs are run.
- Do not submit code you did not verify runs.

## Commit style

```
feat(python/algorithms): add trie with prefix search
fix(python/cli_text): handle empty CSV in csv_report
docs: update Python index
```

By contributing you agree your code is released under the repository's MIT license.
