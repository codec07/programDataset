"""Hangman (terminal).

Rules
-----
The computer picks a secret word. Guess one letter at a time. Correct letters
are revealed in place; wrong letters cost one of six lives and are drawn on
the gallows. Guess the whole word before the six body parts are complete.
Repeated or non-letter guesses do not cost a life.

Controls
--------
Type a single letter and press Enter to guess. Type the full word at any
time to attempt a complete solution. ``q`` quits. Ctrl+C / Ctrl+D exit too.

Run
---
    python hangman.py
"""

from __future__ import annotations

import random

MAX_WRONG = 6

WORDS: dict[str, str] = {
    "python": "a popular programming language named after a comedy troupe",
    "guitar": "a stringed instrument with a fretted neck",
    "volcano": "a mountain that can erupt with lava",
    "penguin": "a flightless bird that swims",
    "galaxy": "a huge system of stars and dust",
    "mystery": "something difficult to explain",
    "lantern": "a portable light with a protective case",
    "compass": "a tool that points north",
    "whisper": "to speak very softly",
    "dolphin": "an intelligent marine mammal",
    "pyramid": "an ancient stone structure in Egypt",
    "journey": "travel from one place to another",
    "cactus": "a spiny desert plant",
    "harbor": "a sheltered place where ships dock",
    "wizard": "a person with magical powers",
    "oxygen": "the gas we need to breathe",
    "marble": "a hard stone used in sculptures",
    "saddle": "a seat strapped to a horse",
    "tunnel": "an underground passage",
    "breeze": "a gentle wind",
}

GALLOWS: tuple[str, ...] = (
    r"""
  +---+
  |   |
      |
      |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
      |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
  |   |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
      |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
 /    |
      |
=========""",
    r"""
  +---+
  |   |
  O   |
 /|\  |
 / \  |
      |
=========""",
)


class HangmanGame:
    """One round of hangman with the secret word kept private."""

    def __init__(self, word: str | None = None, rng: random.Random | None = None) -> None:
        rng = rng or random.Random()
        self._word = (word or rng.choice(list(WORDS))).lower()
        self.hint = WORDS.get(self._word, "no hint available")
        self.guessed: set[str] = set()
        self.wrong = 0

    @property
    def word(self) -> str:
        """The revealed word pattern (not the secret letters)."""
        return " ".join(ch if ch in self.guessed else "_" for ch in self._word)

    def solved(self) -> bool:
        return all(ch in self.guessed for ch in self._word)

    def lost(self) -> bool:
        return self.wrong >= MAX_WRONG

    def guess(self, letter: str) -> str:
        """Process one letter.

        Returns one of ``hit``, ``miss``, ``repeat`` or ``invalid``.
        """
        letter = letter.lower()
        if len(letter) != 1 or not letter.isalpha():
            return "invalid"
        if letter in self.guessed:
            return "repeat"
        self.guessed.add(letter)
        if letter in self._word:
            return "hit"
        self.wrong += 1
        return "miss"

    def try_word(self, attempt: str) -> bool:
        """Allow the player to solve outright. Wrong attempts cost a life."""
        attempt = attempt.strip().lower()
        if attempt == self._word:
            self.guessed.update(self._word)
            return True
        self.wrong += 1
        return False

    def reveal(self) -> str:
        return self._word

    def status(self) -> str:
        return GALLOWS[min(self.wrong, MAX_WRONG)]


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def play_round(rng: random.Random) -> bool:
    """Play one round; return True if the player won."""
    game = HangmanGame(rng=rng)
    print("\nHint:", game.hint)
    print(f"You have {MAX_WRONG} wrong guesses allowed.")

    while not game.solved() and not game.lost():
        print(game.status())
        print("Word:", game.word)
        print("Wrong guesses:", game.wrong, "/", MAX_WRONG)
        print("Letters used:", " ".join(sorted(game.guessed)) or "(none)")

        raw = read_line("Guess a letter (or type the whole word, q to quit): ").strip()
        if raw.lower() in {"q", "quit", "exit"}:
            print("The word was:", game.reveal())
            raise SystemExit(0)

        if len(raw) > 1:
            if game.try_word(raw):
                print("Correct! The word was", game.reveal())
                return True
            print(f"Wrong word! That costs a life.")
            continue

        result = game.guess(raw)
        if result == "hit":
            print(f"Good guess! '{raw.lower()}' is in the word.")
        elif result == "miss":
            print(f"Sorry, '{raw.lower()}' is not in the word.")
        elif result == "repeat":
            print("You already tried that letter (no penalty).")
        else:
            print("Please enter a single letter A-Z.")

    print(game.status())
    if game.solved():
        print("You solved it! The word was", game.reveal().upper())
        return True
    print("Out of lives! The word was", game.reveal().upper())
    return False


def main() -> None:
    print("=" * 44)
    print("              HANGMAN")
    print("=" * 44)
    rng = random.Random()
    wins = losses = 0
    while True:
        if play_round(rng):
            wins += 1
        else:
            losses += 1
        print(f"\nScore: {wins} wins, {losses} losses")
        again = read_line("Play again? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
