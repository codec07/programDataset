"""Wordle clone (terminal).

Rules
-----
Guess a hidden five-letter word in six tries. After each guess every letter
is marked:

* green  - correct letter, correct position
* yellow - correct letter, wrong position
* grey   - the letter does not appear (or appears fewer times than guessed)

Only words from the built-in list are accepted. Duplicate letters are handled
correctly: a letter can only be marked as many times as it occurs in the
answer.

Controls
--------
Type a five-letter word and press Enter. ``q`` quits.
Ctrl+C / Ctrl+D exit cleanly.

Options
-------
    python wordle_clone.py [--seed N]

Run
---
    python wordle_clone.py
"""

from __future__ import annotations

import argparse
import os
import random
import sys

MAX_GUESSES = 6
GREEN, YELLOW, GREY = 2, 1, 0
ANSI = {GREEN: "\033[42m\033[30m", YELLOW: "\033[43m\033[30m",
        GREY: "\033[100m\033[97m"}
RESET = "\033[0m"

WORD_TEXT = """
about above actor acute admit adopt adult after again agent agree ahead alarm
album alert alike alive allow alone along alter among anger angle angry apart
apple apply arena argue arise armor army aroma array arrow aside asset audio
audit avoid awake award aware badly baker basic basin beach began begin being
below bench birth black blade blame blank blast blaze bleed blend bless blind
block blood board boast bonus boost booth bound brain brand brave bread break
breed brick bride brief bring broad broke brown brush build burst cabin cable
camel canal candy canoe cargo carry carve catch cause chain chair chalk charm
chart chase cheap check chess chest chief child chill china chose civic civil
claim clash class clean clear clerk click cliff climb clock close cloud coach
coast could count court cover crack craft crane crash crazy cream creek crime
crisp cross crowd crown crude curve cycle daily dairy dance dated dealt death
debut decay delay dense depth derby devil diary digit dirty ditch dizzy dodge
doing donor doubt dozen draft drain drama drank dream dress dried drift drill
drink drive drove drown dying eager eagle early earth easel eaten eight elbow
elder elect elite empty enemy enjoy enter entry equal equip erase error essay
event every exact exist extra fable faced fairy faith false fancy fatal fault
favor feast fence ferry fever fiber field fifth fifty fight final first flame
flash fleet flesh float flood floor flour fluid flush focus force forge forth
forty forum found frame fraud fresh front frost fruit fully funny genre ghost
giant given glass globe glory glove going grace grade grain grand grant grape
graph grasp grass grave great green greet grief grill grind groan groom group
grove grown guard guess guest guide happy harsh haste hatch haunt heart heavy
hedge hello hence hobby honey horse hotel house human humor hurry ideal image
imply index inner input irony issue ivory jeans jelly jewel joint jolly judge
juice jumbo kebab kneel knife knock known label labor lance large laser later
laugh layer learn lease least leave legal lemon level lever light limit linen
liver lobby local lodge logic loose lover lower loyal lucky lunar lunch lying
magic major maker maple march marsh match maybe mayor meant medal media melon
mercy merge merit metal meter midst might mimic minor minus mixer model moist
money month moral motor mount mouse mouth movie music naive naked nasty naval
nerve never newly night noble noise north novel nurse nylon occur ocean offer
often olive onion opera orbit order organ other ought ounce outer owner ozone
paint panel panic paper party pasta patch pause peace peach pearl pedal penny
perch phase phone photo piano piece pilot pinch pitch pixel pizza place plain
plane plant plate plaza point polar porch pound power press price pride prime
print prize probe prone proof proud prove prune pulse punch pupil puppy purse
quack queen query quest queue quick quiet quilt quite quote radar radio raise
rally ranch range rapid ratio reach react ready realm rebel refer reign relax
relay remix renew repay reply rider ridge rifle right rigid rinse risen risky
rival river roast robin robot rocky rogue roman rough round route royal rugby
ruler rumor rural saint salad salon salsa sauce scale scare scarf scene scent
scope score scout scrap screw script scrub sense serve seven shade shaft shake
shall shape share shark sharp sheep sheet shelf shell shift shine shirt shock
shore short shout shown shrub sight silly since sixth sixty skate skill skirt
slave sleep slice slide slope small smart smell smile smoke snack snake soapy
soccer solid solve sorry sound south space spare spark speak speed spell spend
spent spice spider spike spine spite split spoke spoon sport spray squad stack
staff stage stair stake stand start state steak steal steam steel steep steer
stern stick still stock stone stood store storm story stove strap straw strip
stuck study stuff style sugar suite sunny super surge sushi swamp swarm swear
sweat sweep sweet swift swing sword table taken tales taste teach teeth tempo
tenth thank theft their theme there these thick thief thing think third those
three throw thumb tiger tight timer tired title toast today token tooth topic
torch total touch tough tower toxic trace track trade trail train trait trash
treat trend trial tribe trick tried troop trout truck truly trunk trust truth
tulip tumor tutor twice twist ultra uncle under union unite unity until upper
upset urban urged usage usual utter vague valid value valve vapor vault venue
verse video villa vinyl virus visit vital vivid vocal voice vowel wagon waist
waste watch water weary weigh weird wheat wheel where which while white whole
whose widow width witch woman world worry worse worst worth would wound wrist
write wrong wrote yield young youth zebra
"""
WORDS: tuple[str, ...] = tuple(sorted({word for word in WORD_TEXT.split() if len(word) == 5}))
WORD_SET = frozenset(WORDS)


def supports_color() -> bool:
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")
    return True


def score_guess(secret: str, guess: str) -> list[int]:
    """Return a list of GREEN/YELLOW/GREY marks for each guess letter."""
    marks = [GREY] * 5
    remaining: dict[str, int] = {}
    for index in range(5):
        if guess[index] == secret[index]:
            marks[index] = GREEN
        else:
            remaining[secret[index]] = remaining.get(secret[index], 0) + 1
    for index in range(5):
        if marks[index] == GREEN:
            continue
        letter = guess[index]
        if remaining.get(letter, 0) > 0:
            marks[index] = YELLOW
            remaining[letter] -= 1
    return marks


def render_guess(guess: str, marks: list[int], color: bool) -> str:
    if color:
        return " ".join(f"{ANSI[m]} {ch.upper()} {RESET}" for ch, m in zip(guess, marks))
    symbols = {GREEN: "[{}]", YELLOW: "({})", GREY: " {} "}
    return " ".join(symbols[m].format(ch.upper()) for ch, m in zip(guess, marks))


def keyboard_status(guesses: list[tuple[str, list[int]]]) -> dict[str, int]:
    status: dict[str, int] = {}
    for guess, marks in guesses:
        for ch, mark in zip(guess, marks):
            status[ch] = max(status.get(ch, GREY), mark)
    return status


def render_keyboard(guesses: list[tuple[str, list[int]]], color: bool) -> str:
    status = keyboard_status(guesses)
    rows = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
    lines = []
    for row in rows:
        parts = []
        for ch in row:
            mark = status.get(ch)
            if mark is None:
                parts.append(ch.upper())
            elif color:
                parts.append(f"{ANSI[mark]} {ch.upper()} {RESET}")
            else:
                parts.append({GREEN: f"[{ch.upper()}]", YELLOW: f"({ch.upper()})",
                              GREY: f" {ch.upper()} "}[mark])
        lines.append(" ".join(parts))
    return "\n".join(lines)


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        raise SystemExit(0)


def play_round(rng: random.Random) -> bool:
    secret = rng.choice(WORDS)
    color = supports_color()
    guesses: list[tuple[str, list[int]]] = []
    print("\nGuess the five-letter word. Green = exact, (yellow) = present,"
          " grey = absent.")
    print("Legend: [A] correct place, (A) wrong place,  A  not in word.\n")

    while len(guesses) < MAX_GUESSES:
        for attempt in range(MAX_GUESSES):
            if attempt < len(guesses):
                guess, marks = guesses[attempt]
                print(render_guess(guess, marks, color))
            else:
                print("  .    .    .    .    .")
        print()
        print(render_keyboard(guesses, color))

        while True:
            raw = read_line(f"\nGuess {len(guesses) + 1}/{MAX_GUESSES} (q to quit): ")
            if raw.strip().lower() in {"q", "quit", "exit"}:
                print("The word was", secret.upper())
                raise SystemExit("Thanks for playing!")
            guess = raw.strip().lower()
            if len(guess) == 5 and guess.isalpha() and guess in WORD_SET:
                break
            if len(guess) == 5 and guess.isalpha():
                print("That word is not in the dictionary. Try another.")
            else:
                print("Enter exactly five letters.")

        marks = score_guess(secret, guess)
        guesses.append((guess, marks))
        print()
        if guess == secret:
            for past, past_marks in guesses:
                print(render_guess(past, past_marks, color))
            print(f"\nSolved in {len(guesses)} guess{'es' if len(guesses) != 1 else ''}!")
            return True

    for guess, marks in guesses:
        print(render_guess(guess, marks, color))
    print(f"\nOut of guesses. The word was {secret.upper()}.")
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play a Wordle-style game.")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed the random word picker for reproducible games")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    rng = random.Random(args.seed)
    print("=" * 44)
    print("              WORDLE")
    print("=" * 44)
    wins = losses = 0
    while True:
        if play_round(rng):
            wins += 1
        else:
            losses += 1
        print(f"Score: {wins} wins, {losses} losses")
        again = read_line("Play again? [y/N]: ").strip().lower()
        if again not in {"y", "yes"}:
            print("Thanks for playing!")
            return


if __name__ == "__main__":
    main()
