# Python — 110 standalone programs

Single-file Python programs for code-model training and human reference.
Every file is self-contained, uses **only the standard library**, targets
**Python 3.10+**, and runs on Windows, macOS, and Linux.

| Domain | Programs | Lines | What it covers |
|---|---:|---:|---|
| [cli_text](cli_text/) | 22 | 5,186 | command-line tools, text processing, file & directory utilities |
| [algorithms](algorithms/) | 22 | 5,812 | data structures, algorithms, math, classic puzzles |
| [games](games/) | 22 | 5,058 | terminal games, tkinter games, deterministic simulations |
| [data_web](data_web/) | 22 | 5,359 | CSV/JSON/SQLite, HTTP clients & servers, automation, reporting |
| [advanced](advanced/) | 22 | 5,319 | asyncio, threads, multiprocessing, graphics, audio, systems |
| **Total** | **110** | **26,734** | |

Run anything with `--help`, or open the file and read the module docstring:

```powershell
python Python/cli_text/word_frequency.py --help
python Python/games/tic_tac_toe.py
python Python/algorithms/sorting_algorithms.py
```

---

## cli_text — command-line & text utilities

| Program | Description |
|---|---|
| [word_frequency.py](cli_text/word_frequency.py) | Rank word frequencies across files or stdin, with stop-word and length filters. |
| [text_stats.py](cli_text/text_stats.py) | Line/word/sentence counts, reading time, Flesch readability. |
| [markdown_toc.py](cli_text/markdown_toc.py) | Generate or refresh a Markdown table of contents between markers; CI `--check`. |
| [csv_to_json.py](cli_text/csv_to_json.py) | CSV/TSV → JSON/NDJSON with delimiter sniffing and type inference. |
| [json_tool.py](cli_text/json_tool.py) | Validate, format, minify, and query JSON via dotted paths. |
| [log_analyzer.py](cli_text/log_analyzer.py) | Summarise access/app logs: levels, status codes, IPs, paths, bytes, time range. |
| [duplicate_finder.py](cli_text/duplicate_finder.py) | Find duplicate files by size + hash; deletion requires `--delete --yes`. |
| [file_organizer.py](cli_text/file_organizer.py) | Sort files into category folders by extension; previews unless `--apply`. |
| [password_generator.py](cli_text/password_generator.py) | Secure passwords and passphrases with entropy estimates. |
| [unit_converter.py](cli_text/unit_converter.py) | Length, mass, temperature, volume, data, time, speed, area conversions. |
| [todo_cli.py](cli_text/todo_cli.py) | JSON-backed todo list with priorities, filters, and atomic saves. |
| [batch_rename.py](cli_text/batch_rename.py) | Regex/affix/number bulk renaming with collision-safe planning. |
| [diff_tool.py](cli_text/diff_tool.py) | Unified diffs for files or directory trees, with ignore flags and `--stat`. |
| [base64_tool.py](cli_text/base64_tool.py) | Base64 encode/decode files, stdin, or text; URL-safe and wrapping options. |
| [hash_checker.py](cli_text/hash_checker.py) | Compute file hashes and verify `sha256sum`-style checksum lists. |
| [env_validator.py](cli_text/env_validator.py) | Validate `.env` files against a typed schema (int, bool, url, email, path, port). |
| [ini_config_editor.py](cli_text/ini_config_editor.py) | INI get/set/delete with atomic writes and automatic backups. |
| [cli_calendar.py](cli_text/cli_calendar.py) | Month/year calendar with ISO week numbers and today marker. |
| [text_wrap_formatter.py](cli_text/text_wrap_formatter.py) | Reflow, wrap, and justify paragraphs and bullet lists. |
| [srt_shift.py](cli_text/srt_shift.py) | Shift validated SRT timestamps with clamping and safe writes. |
| [csv_report.py](cli_text/csv_report.py) | Profile CSV columns and aggregate numeric values by group. |
| [directory_tree.py](cli_text/directory_tree.py) | Read-only directory tree with depth limits, filters, and sizes. |

## algorithms — data structures, algorithms, math

| Program | Description |
|---|---|
| [sorting_algorithms.py](algorithms/sorting_algorithms.py) | Six classic sorts with complexity notes and seeded timing comparison. |
| [binary_search.py](algorithms/binary_search.py) | Lower/upper bound, first/last occurrence, rotated array, exponential search. |
| [graph_algorithms.py](algorithms/graph_algorithms.py) | BFS, DFS, Dijkstra, topological sort, cycle detection, components. |
| [dynamic_programming.py](algorithms/dynamic_programming.py) | Seven DP problems in memoized and tabulated forms. |
| [linked_list.py](algorithms/linked_list.py) | Singly linked list: reverse, middle, nth-from-end, merge, Floyd cycle detection. |
| [stack_queue.py](algorithms/stack_queue.py) | Min-stack, two-stack queue, circular queue, bracket matching, sliding max. |
| [binary_search_tree.py](algorithms/binary_search_tree.py) | BST insert/search/delete, traversals, k-th smallest, invariant validation. |
| [heap_tools.py](algorithms/heap_tools.py) | Min/max heap from scratch, heapify, heapsort, top-k; checked against `heapq`. |
| [trie.py](algorithms/trie.py) | Prefix tree with prefix counts, pruning delete, and longest common prefix. |
| [union_find.py](algorithms/union_find.py) | DSU with path compression + union by rank, Kruskal MST, cycle detection. |
| [lru_cache_impl.py](algorithms/lru_cache_impl.py) | LRU cache from a hash map + doubly linked list, with hit/miss stats. |
| [matrix_ops.py](algorithms/matrix_ops.py) | Multiply, transpose, determinant, Gauss-Jordan inverse, powers. |
| [bigint_arithmetic.py](algorithms/bigint_arithmetic.py) | Signed add/sub/mul/div on digit strings, no native big ints in core ops. |
| [number_theory.py](algorithms/number_theory.py) | GCD/EGCD, modular inverse/power, Miller-Rabin, sieve, factorization, CRT. |
| [combinatorics.py](algorithms/combinatorics.py) | Binomial, permutations, Pascal, Catalan, derangements, lazy generators. |
| [statistics_kit.py](algorithms/statistics_kit.py) | Mean/median/mode/percentile/variance/correlation/regression from scratch. |
| [expression_evaluator.py](algorithms/expression_evaluator.py) | Tokenizer + shunting-yard + RPN evaluator with variables. |
| [sudoku_solver.py](algorithms/sudoku_solver.py) | Constraint-validated backtracking with MRV and solution counting. |
| [n_queens.py](algorithms/n_queens.py) | Bitmask backtracking count/construct with board rendering. |
| [maze_solver.py](algorithms/maze_solver.py) | Grid parser with BFS, DFS, and A* search plus path rendering. |
| [string_algorithms.py](algorithms/string_algorithms.py) | KMP, Rabin-Karp, Z-algorithm, Manacher, anagrams, RLE codec. |
| [interval_tools.py](algorithms/interval_tools.py) | Merge/insert/intersect intervals, coverage, max overlap, randomized checks. |

## games — games & simulations

| Program | Type | Description |
|---|---|---|
| [tic_tac_toe.py](games/tic_tac_toe.py) | Terminal | Two-player or unbeatable minimax opponent. |
| [hangman.py](games/hangman.py) | Terminal | Six lives, ASCII gallows, hints, whole-word guesses. |
| [blackjack.py](games/blackjack.py) | Terminal | Betting bankroll, hit/stand/double, blackjack pays 3:2. |
| [minesweeper.py](games/minesweeper.py) | tkinter | 10×10, 12 mines, first-click safety, flood fill, flags, timer. |
| [snake.py](games/snake.py) | tkinter | 22×22 grid, growth, pause, high score, wall/self collision. |
| [pong.py](games/pong.py) | tkinter | First to 7, accelerating ball, angle-based paddle bounce. |
| [breakout.py](games/breakout.py) | tkinter | 50 bricks, three lives, launch/pause, score by row. |
| [tetris.py](games/tetris.py) | tkinter | 7-bag randomiser, rotation, hard drop, levels, line-clear scoring. |
| [game_2048.py](games/game_2048.py) | tkinter | Full merge/slide rules, score, best score, continue past 2048. |
| [connect_four.py](games/connect_four.py) | Terminal | Computer takes wins, blocks threats, positional heuristic. |
| [battleship.py](games/battleship.py) | Terminal | Manual/random fleet placement, hunt-and-target AI. |
| [mastermind.py](games/mastermind.py) | Terminal | Exact/partial feedback with correct duplicate handling. |
| [rock_paper_scissors.py](games/rock_paper_scissors.py) | Terminal | Best-of-3/5/7 match with ASCII hand art. |
| [number_guess.py](games/number_guess.py) | Terminal | Difficulty levels with hot/cold hints. |
| [wordle_clone.py](games/wordle_clone.py) | Terminal | Six guesses, duplicate-letter scoring, on-screen keyboard. |
| [text_adventure.py](games/text_adventure.py) | Terminal | *The Dark Lighthouse*: six rooms, inventory, puzzles, win state. |
| [maze_generator.py](games/maze_generator.py) | Simulation | Randomised DFS maze, BFS solver, play mode, CSV export. |
| [conway_life.py](games/conway_life.py) | Simulation | Toroidal Life, interactive grid or `--headless` stats/CSV. |
| [nim_game.py](games/nim_game.py) | Terminal | Three piles with a perfect XOR-based opponent. |
| [dice_simulator.py](games/dice_simulator.py) | Simulation | Seeded dice rolls, observed vs expected stats, histogram, CSV. |
| [card_deck.py](games/card_deck.py) | Simulation | 52-card deck, poker evaluator, category frequencies vs theory. |
| [predator_prey.py](games/predator_prey.py) | Simulation | Agent-based rabbits, foxes, and regrowing grass with CSV output. |

## data_web — data, SQLite, HTTP, automation

| Program | Description |
|---|---|
| [csv_cleaner.py](data_web/csv_cleaner.py) | Streaming CSV cleaner: trim, dedupe, drop empty, fill blanks, lowercase. |
| [json_store.py](data_web/json_store.py) | Persistent JSON key/value store with dotted keys and atomic writes. |
| [sqlite_crud.py](data_web/sqlite_crud.py) | Parameterised SQLite inventory CRUD with validation and `--dry-run`. |
| [sqlite_query_runner.py](data_web/sqlite_query_runner.py) | Read-only SQL runner with table/CSV/JSON output and injection refusal. |
| [expense_tracker.py](data_web/expense_tracker.py) | Expenses, budgets, monthly reports, and CSV export. |
| [portfolio_tracker.py](data_web/portfolio_tracker.py) | Holdings, FIFO sells, valuation, and allocation from a local price file. |
| [weather_cli.py](data_web/weather_cli.py) | Open-Meteo current conditions and forecast with retries; offline demo. |
| [http_client.py](data_web/http_client.py) | urllib client: methods, headers, JSON/form bodies, retries, backoff. |
| [rest_api_server.py](data_web/rest_api_server.py) | Threaded JSON CRUD task API with validation, status codes, self-test. |
| [static_file_server.py](data_web/static_file_server.py) | Safe static server with directory listings and traversal guards. |
| [web_scraper.py](data_web/web_scraper.py) | Polite urllib + html.parser scraper with robots checks; offline HTML parsing. |
| [rss_reader.py](data_web/rss_reader.py) | RSS 2.0 / Atom reader with keyword filters and JSON output. |
| [contact_book.py](data_web/contact_book.py) | SQLite contacts with tags, search, and vCard export. |
| [backup_tool.py](data_web/backup_tool.py) | SHA-256 snapshot backups with verify, restore, zip, and listing. |
| [download_manager.py](data_web/download_manager.py) | Concurrent downloads with Range resume, retries, checksum verification. |
| [task_scheduler.py](data_web/task_scheduler.py) | Interval jobs from JSON config with logging, `--once`, `--dry-run`. |
| [system_report.py](data_web/system_report.py) | OS, CPU, memory, disk, and Python details as text or JSON (ctypes, no psutil). |
| [disk_usage_report.py](data_web/disk_usage_report.py) | Folder/file/extension sizes with bars and largest entries. |
| [svg_chart.py](data_web/svg_chart.py) | CSV → standalone SVG bar or line chart, no matplotlib. |
| [report_generator.py](data_web/report_generator.py) | Self-contained HTML or Markdown report from CSV/JSON. |
| [data_pipeline.py](data_web/data_pipeline.py) | Streaming read → transform → aggregate → write pipeline. |
| [log_rotator.py](data_web/log_rotator.py) | Size-based rotation, gzip, listing, and count/age pruning. |

## advanced — concurrency, graphics, audio, systems

| Program | Description |
|---|---|
| [asyncio_worker_pool.py](advanced/asyncio_worker_pool.py) | Bounded queue, futures, error isolation, cancellation, graceful shutdown. |
| [thread_pool_tasks.py](advanced/thread_pool_tasks.py) | Named `ThreadPoolExecutor` tasks with timeouts, cancellation, outcomes. |
| [multiprocessing_pipeline.py](advanced/multiprocessing_pipeline.py) | Spawn-safe producer → workers → collector pipeline with sentinels. |
| [producer_consumer.py](advanced/producer_consumer.py) | Bounded `queue.Queue` pipeline with multiple producers/consumers. |
| [async_rate_limiter.py](advanced/async_rate_limiter.py) | Asyncio token bucket with burst, refill, timeouts, context manager. |
| [async_crawler_sim.py](advanced/async_crawler_sim.py) | Offline async crawler: dedupe, depth/page limits, concurrency cap. |
| [retry_decorator.py](advanced/retry_decorator.py) | Sync/async retry with exponential backoff, jitter, and callbacks. |
| [cache_decorator.py](advanced/cache_decorator.py) | Thread-safe LRU/TTL cache with stats and async request coalescing. |
| [event_emitter.py](advanced/event_emitter.py) | Thread-safe emitter with wildcard/once listeners, sync + async dispatch. |
| [async_task_scheduler.py](advanced/async_task_scheduler.py) | Priority delayed scheduler with heap, worker pool, cancellation. |
| [key_value_store.py](advanced/key_value_store.py) | Append-only JSONL store with tombstones, fsync, atomic compaction. |
| [mini_shell.py](advanced/mini_shell.py) | Safe shell with built-ins and `shell=False` external execution. |
| [png_writer.py](advanced/png_writer.py) | From-scratch 8-bit RGB PNG encoder using CRC-32 and zlib. |
| [image_processor.py](advanced/image_processor.py) | PPM P6/P3 I/O, grayscale, blur, Sobel edges, bilinear resize. |
| [ascii_art.py](advanced/ascii_art.py) | PPM/PNG → ASCII converter with a procedural demo image. |
| [wav_synth.py](advanced/wav_synth.py) | WAV synthesis: five waveforms, chords, sequences, ADSR envelopes. |
| [waveform_svg.py](advanced/waveform_svg.py) | WAV/demo waveform rendering to styled SVG with statistics. |
| [mandelbrot.py](advanced/mandelbrot.py) | Smooth-colour Mandelbrot renderer to PNG or PPM. |
| [fractal_tree.py](advanced/fractal_tree.py) | Recursive turtle tree with headless PostScript export. |
| [spirograph.py](advanced/spirograph.py) | Hypotrochoid spirograph with turtle preview and PS export. |
| [terminal_dashboard.py](advanced/terminal_dashboard.py) | ANSI live dashboard with simulated metrics and clean terminal restore. |
| [progress_bar.py](advanced/progress_bar.py) | ANSI progress bars with rate/ETA and TTY/Unicode fallbacks. |

---

## Conventions

- **Standard library only.** No `requirements.txt`, no virtualenv needed.
- **Typed and documented.** Module docstring, type hints, decomposed functions, `main()` guard.
- **Defensive.** Invalid input raises or exits with a message on `stderr`; no silent data loss.
- **Safe defaults.** Mutating tools preview (`--dry-run`) or require `--apply`/`--force`.
- **Portable.** UTF-8 I/O, `pathlib`, no hardcoded absolute paths, Windows/POSIX terminal handling.
- **Offline-testable.** Network tools ship a `--demo`/`--offline`/`--once` path.

## Verification status

All 110 files pass `python -m py_compile` and were executed during review.
CLI tools were exercised with `--help` and real fixtures; GUI programs were
imported without opening a window; servers and downloaders were tested against
local ephemeral servers; generated PNG, WAV, SVG, and PostScript artifacts were
parsed back and validated.

Per-domain details live in each folder's `README.md`.
