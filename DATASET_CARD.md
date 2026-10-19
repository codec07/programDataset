# Dataset Card — Program Dataset

## Summary

`programDataset` is a collection of complete, single-file programs organized by language and domain. Its purpose is to serve as a compact, high-signal corpus for code-model training, instruction tuning, execution-feedback research, and evaluation.

- **Languages:** Python (current); additional languages planned.
- **Format:** one program per file, UTF-8 text.
- **Dependencies:** standard library only.
- **Provenance:** AI-agent generated under human-directed specifications, then compiled and smoke-tested. Not copied from existing repositories.
- **License:** MIT.

## Structure

```
<Language>/<domain>/<program>.py
```

Python domains currently include `cli_text`, `algorithms`, `games`, `data_web`, and `advanced`.

## Intended use

- Supervised fine-tuning on full programs rather than fragments.
- Instruction tuning: natural-language task → complete file.
- Execution-feedback and repair training (run the program, read the traceback, fix it).
- Test-generation and code-review tasks.
- Teaching examples for humans learning Python.

## Out-of-scope use

- Do **not** treat the corpus as a security reference. Several programs touch the filesystem, subprocesses, sockets, and archives for demonstration purposes.
- Do **not** assume production correctness, performance, or accessibility.
- Do **not** deploy the example servers (`rest_api_server.py`, `static_file_server.py`) to the public internet as-is.
- Do **not** infer that the absence of a bug class in this corpus means a model is safe.

## Quality process

1. Each program is written to a shared specification: docstring, type hints, argument parsing, input validation, `main()` guard.
2. Every file must pass `python -m py_compile`.
3. Every file is smoke-tested: CLI `--help`, self-tests with assertions, or offline/demo mode for networked tools.
4. GUI programs are imported without launching a window during testing.
5. A manifest with line counts and SHA-256 hashes can be generated with `python tools/build_manifest.py`.

## Known limitations

- **Synthetic origin.** Programs are model-generated, so subtle bugs, non-idiomatic choices, or insecure patterns may remain despite testing.
- **Coverage skew.** Small, self-contained domains (algorithms, CLIs) are over-represented relative to large application code.
- **No test suites per file.** Testing is embedded in `main()` demos rather than separate `test_*.py` files, by design (single-file constraint).
- **Version floor.** Targets Python 3.10+; some standard-library behavior differs on older interpreters.
- **Platform.** Developed and tested primarily on Windows; POSIX paths and terminal behavior are handled but less exercised.
- **No human line-by-line audit.** Review is specification-driven plus automated.

## Ethical and legal notes

- All code was generated for this repository; no third-party source was reproduced.
- MIT license permits commercial and non-commercial use with attribution.
- If you redistribute a derivative dataset, keep this card and the license notice.

## Maintenance

- Additions go in the correct `<Language>/<domain>/` folder as one self-contained file.
- Regenerate `manifest.json` after adding files.
- Breaking changes to the layout should be recorded here and in `README.md`.

## Citation

```bibtex
@misc{programdataset2026,
  title  = {Program Dataset: single-file programs for code model training},
  author = {codec07 and contributors},
  year   = {2026},
  url    = {https://github.com/codec07/programDataset}
}
```
