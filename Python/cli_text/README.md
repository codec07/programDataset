# cli_text - standalone Python command-line tools

A collection of 22 single-file, standard-library-only utilities for text
processing, file/directory work and small local productivity tasks.
Everything targets Python 3.10+ and works on Windows, macOS and Linux.
No package installation, no network access, no GUI.

Every script has an argparse interface (`python <script> --help`), reads
UTF-8 text, prints errors to stderr and returns a non-zero exit code on
failure. Tools that modify files are preview-first or require an explicit
confirmation.

## Programs

| Program | What it does | Example |
| --- | --- | --- |
| `word_frequency.py` | Rank word frequencies across files or stdin, with stop-word and length filters, table or JSON output. | `python word_frequency.py notes.txt --top 20 --ignore-stopwords` |
| `text_stats.py` | Report lines, words, sentences, paragraphs, reading time and Flesch readability for text files. | `python text_stats.py article.txt --json` |
| `markdown_toc.py` | Generate or refresh a Markdown table of contents between `<!-- toc -->` markers, or check it in CI. | `python markdown_toc.py README.md --in-place --dry-run` |
| `csv_to_json.py` | Convert CSV/TSV to a JSON array or NDJSON with delimiter sniffing and optional type inference. | `python csv_to_json.py people.csv --types -o people.json` |
| `json_tool.py` | Validate, pretty-print, minify and query JSON with dotted paths. | `python json_tool.py get package.json dependencies.0.version` |
| `log_analyzer.py` | Summarise access/application logs: levels, status codes, IPs, paths, bytes and time range. | `python log_analyzer.py access.log --top 15` |
| `duplicate_finder.py` | Find duplicate files by size and content hash; deletion is opt-in and keeps one copy per group. | `python duplicate_finder.py photos --min-size 4096` |
| `file_organizer.py` | Sort files into Images/Documents/Code/... folders by extension, previewing by default. | `python file_organizer.py Downloads --apply` |
| `password_generator.py` | Generate strong passwords or word-based passphrases with entropy estimates. | `python password_generator.py --length 24 --exclude-ambiguous` |
| `unit_converter.py` | Convert length, mass, temperature, volume, data, time, speed and area units. | `python unit_converter.py 72 f c --precision 2` |
| `todo_cli.py` | File-backed todo list with priorities, stable IDs, filters, JSON output and atomic saves. | `python todo_cli.py add "Write report" --priority high` |
| `batch_rename.py` | Bulk-rename files with regex, prefix/suffix and numbering; rejects unsafe plans. | `python batch_rename.py photos --pattern "IMG_(\d+)" --replace "photo_\1" --apply` |
| `diff_tool.py` | Unified diffs for two files or two directory trees, with ignore options and `--stat`. | `python diff_tool.py before/ after/ --stat` |
| `base64_tool.py` | Encode/decode Base64 for files, stdin or literal text, with URL-safe and wrapping options. | `python base64_tool.py decode photo.b64 -o photo.png` |
| `hash_checker.py` | Compute file hashes and verify `sha256sum`-style checksum files. | `python hash_checker.py --check SHA256SUMS` |
| `env_validator.py` | Validate `.env` files against a typed schema (int, bool, url, email, path, port). | `python env_validator.py --schema schema.txt --env .env` |
| `ini_config_editor.py` | List/get/set/delete INI values with atomic writes and automatic `.bak` backups. | `python ini_config_editor.py --file app.ini set database port 5433` |
| `cli_calendar.py` | Print a month or full-year calendar with ISO week numbers and today highlighted. | `python cli_calendar.py --month 12 --weeks` |
| `text_wrap_formatter.py` | Reflow, wrap and justify paragraphs and bullet lists to a chosen width. | `python text_wrap_formatter.py draft.txt --width 100 --justify` |
| `srt_shift.py` | Shift SRT subtitle timestamps, with validation, clamping and safe in-place writes. | `python srt_shift.py movie.srt --seconds 2.5 -o fixed.srt` |
| `csv_report.py` | Profile every CSV column and aggregate numeric values by group. | `python csv_report.py sales.csv --group-by region --agg amount:sum` |
| `directory_tree.py` | Print a read-only directory tree with depth limits, filters and optional sizes. | `python directory_tree.py src --depth 2 --sizes` |

## Shared conventions

- **Encoding:** input and output are UTF-8; a BOM is tolerated where relevant.
- **Safety:** `file_organizer.py` previews unless `--apply`; `batch_rename.py`
  previews unless `--apply`; `duplicate_finder.py` only deletes with
  `--delete --yes`; `srt_shift.py` writes to stdout unless `--in-place` or
  `-o` is used.
- **Dry runs:** mutating commands accept `--dry-run` where a preview is useful.
- **Errors:** messages go to stderr and the exit status is 1 (or 2 for usage
  errors from argparse).
- **Exit codes:** `diff_tool.py` uses 0 = identical, 1 = differences, 2 = error.

Run any program with `-h` for the full option list:

```text
python word_frequency.py --help
```
