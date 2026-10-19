# Python Games & Simulations

22 standalone Python programs: terminal games, tkinter games, and small
simulations. Everything uses the **standard library only** (tkinter is part of
Python on Windows), needs **Python 3.10+**, and works in a normal Windows
terminal or desktop session.

No images, sounds, fonts, or other external assets are used — all graphics are
canvas primitives and all game boards are ASCII/Unicode text.

## Quick reference

| File | Type | Controls | Run |
|---|---|---|---|
| `tic_tac_toe.py` | Terminal | `1`–`9` to place, `q` quit | `python tic_tac_toe.py` |
| `hangman.py` | Terminal | one letter, a whole word, `q` quit | `python hangman.py` |
| `blackjack.py` | Terminal | `h` hit, `s` stand, `d` double, `q` quit | `python blackjack.py` |
| `minesweeper.py` | tkinter | Left click reveal, right click flag, `R` restart, `Esc` quit | `python minesweeper.py` |
| `snake.py` | tkinter | Arrows/WASD, `Space` pause, `R` restart, `Esc` quit | `python snake.py` |
| `pong.py` | tkinter | `W`/`S` or Up/Down, `Space` pause, `R` restart, `Esc` quit | `python pong.py` |
| `breakout.py` | tkinter | Left/Right or `A`/`D`, `Space` launch, `P` pause, `R` restart, `Esc` quit | `python breakout.py` |
| `tetris.py` | tkinter | Arrows move/drop, `Up`/`X` rotate, `Z` rotate ccw, `Space` hard drop, `P` pause, `R` restart, `Esc` quit | `python tetris.py` |
| `game_2048.py` | tkinter | Arrows/WASD slide, `Enter` continue after 2048, `R` restart, `Esc` quit | `python game_2048.py` |
| `connect_four.py` | Terminal | column `1`–`7`, `q` quit | `python connect_four.py` |
| `battleship.py` | Terminal | `B2 H`/`B2 V` place, `r` random, shots like `B7`, `q` quit | `python battleship.py` |
| `mastermind.py` | Terminal | four letters from `R G B Y O P`, `q` quit | `python mastermind.py` |
| `rock_paper_scissors.py` | Terminal | `rock`/`paper`/`scissors` or `r`/`p`/`s`, `q` quit | `python rock_paper_scissors.py` |
| `number_guess.py` | Terminal | difficulty `1`–`3`, then numbers, `q` quit | `python number_guess.py` |
| `wordle_clone.py` | Terminal | five-letter guesses, `q` quit | `python wordle_clone.py` |
| `text_adventure.py` | Terminal | `look`, `go <dir>`, `take`, `drop`, `inventory`, `read`, `light lamp`, `help`, `quit` | `python text_adventure.py` |
| `maze_generator.py` | Simulation / terminal | `--solve`, `--play` (Arrows/WASD, `q`), `--seed`, `--csv` | `python maze_generator.py --solve` |
| `conway_life.py` | Simulation / tkinter | Left click toggle, `Space` run/pause, `N` step, `R` random, `C` clear, `G` glider, `Esc` quit; `--headless` | `python conway_life.py` |
| `nim_game.py` | Terminal | `pile count` e.g. `2 3`, `q` quit | `python nim_game.py` |
| `dice_simulator.py` | Simulation | CLI options only | `python dice_simulator.py --seed 1` |
| `card_deck.py` | Simulation | CLI options only | `python card_deck.py --seed 1` |
| `predator_prey.py` | Simulation | CLI options only | `python predator_prey.py --seed 1` |

## Terminal games

Enter answers at the prompts. Input is validated; invalid entries are rejected
without crashing. Every terminal game exits cleanly on `q` (use `quit` in the
text adventure), and on Ctrl+C or end-of-input (Ctrl+Z then Enter on Windows).
The games keep a session score and offer a replay where it makes sense.

* **tic_tac_toe** — two-player mode or an unbeatable minimax computer.
* **hangman** — six lives, ASCII gallows, hints, optional whole-word guesses.
* **blackjack** — betting bankroll, hit/stand/double, blackjack pays 3:2.
* **connect_four** — versus a computer that takes wins, blocks threats, and
  otherwise uses a positional heuristic.
* **battleship** — manually place five ships or randomise them; the computer
  uses hunt-and-target aiming.
* **mastermind** — exact/partial feedback with correct duplicate-letter
  handling.
* **rock_paper_scissors** — best-of-3/5/7 match with ASCII hand art.
* **number_guess** — binary-search-friendly ranges with hot/cold hints.
* **wordle_clone** — six guesses, green/yellow/grey feedback (coloured on
  terminals that support ANSI, readable brackets otherwise), on-screen
  keyboard.
* **text_adventure** — *The Dark Lighthouse*: explore six rooms, find the key,
  fuel, battery and matches, then light the beacon to win.
* **nim** — three piles, normal play, perfect XOR-based computer opponent.

## tkinter games

Run from a desktop session. Each file imports safely without opening a window;
the window is created only by `main()` under `if __name__ == "__main__"`.
Action games use non-blocking `after()` loops rather than blocking sleeps;
turn-based games redraw on input. All have a visible game-over/win state and an
`R` restart key. Keyboard focus is on the game window when it opens.

* **minesweeper** — 10×10, 12 mines, first click always safe, flood fill,
  flags, timer.
* **snake** — 22×22 grid, growing snake, pause, high score, wall/self collision.
* **pong** — first to 7, accelerating ball, angle-based paddle bounces.
* **breakout** — 50 bricks, three lives, score by row, launch/pause controls.
* **tetris** — 7-bag randomiser, wall kicks, ghost-free 10×20 board, levels and
  line-clear scoring.
* **game_2048** — full merge/slide rules, score and best score, win at 2048 with
  the option to continue.
* **conway_life** — clickable Life grid with run/pause, single-step, random,
  clear and glider patterns.

## Simulations

All simulations are deterministic for a given `--seed`, print clear summary
statistics, and can export data:

```text
python maze_generator.py --width 31 --height 19 --seed 7 --solve --csv maze.csv
python conway_life.py --headless --steps 200 --seed 7 --csv life.csv
python dice_simulator.py --dice 3 --sides 8 --rolls 50000 --seed 7 --csv dice.csv
python card_deck.py --hands 50000 --seed 7 --csv poker.csv
python predator_prey.py --steps 300 --seed 7 --csv ecosystem.csv
```

* **maze_generator** — randomised DFS perfect maze; ASCII output, BFS shortest
  path, optional walkable play mode. CSV: `step,row,col` solution path.
* **conway_life** — B3/S23 Life on a toroidal grid; windowed or headless.
  CSV: `generation,population`.
* **dice_simulator** — roll `n` dice with `s` sides, observed vs expected mean,
  standard deviation, histogram. CSV: `sum,count,percent`.
* **card_deck** — sealed 52-card deck, five-card poker evaluator (including
  ace-low straights, royal flush and duplicate-free deck), category frequency
  compared with theoretical probabilities. CSV:
  `category,count,percent,expected_percent`.
* **predator_prey** — agent-based rabbits, foxes and regrowing grass on a
  toroidal grid. CSV: `step,rabbits,foxes,grass`.

## Notes

* Run any file from this folder; none of them import each other.
* `python -m py_compile <file>` verifies syntax.
* GUI programs must not be imported in a headless environment that lacks a
  display; they are safe to import, but `main()` needs a desktop.
* Arguments can be inspected with `--help`, e.g.
  `python predator_prey.py --help`.
