"""Blackjack (terminal).

Rules
-----
A standard 52-card deck is shuffled. You and the dealer each receive two
cards. Number cards are worth their face value, face cards are worth 10, and
an ace is worth 11 or 1 (whichever keeps the hand at or under 21).

* Hit: draw another card.
* Stand: keep your total and let the dealer play.
* Double: double your bet, draw exactly one card, then stand.

You bust above 21 and lose immediately. The dealer draws until reaching 17
and must stand on 17. A two-card 21 is a "blackjack" and pays 3:2. A normal
win pays 1:1, and equal totals push (your bet is returned).

Controls
--------
At the prompt type ``h`` (hit), ``s`` (stand), ``d`` (double), or ``q``.
Bet with a whole number. Ctrl+C / Ctrl+D exit cleanly.

Run
---
    python blackjack.py
"""

from __future__ import annotations

import random
from dataclasses import dataclass

STARTING_BANKROLL = 500
SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        if self.rank == "A":
            return 11
        if self.rank in {"J", "Q", "K"}:
            return 10
        return int(self.rank)

    def __str__(self) -> str:
        symbol = {"Hearts": "H", "Diamonds": "D", "Clubs": "C", "Spades": "S"}[self.suit]
        return f"{self.rank}{symbol}"


class Deck:
    """A shuffled deck that can be refilled from a fresh 52-card set."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self._cards: list[Card] = []
        self.reset()

    def reset(self) -> None:
        self._cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        self.rng.shuffle(self._cards)

    @property
    def remaining(self) -> int:
        return len(self._cards)

    def draw(self) -> Card:
        if len(self._cards) < 15:
            self.reset()
            print("(Deck reshuffled.)")
        return self._cards.pop()


class Hand:
    def __init__(self) -> None:
        self.cards: list[Card] = []

    def add(self, card: Card) -> None:
        self.cards.append(card)

    @property
    def value(self) -> int:
        """Best total that does not bust when possible."""
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def soft(self) -> bool:
        """True when an ace is still being counted as 11."""
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return aces > 0

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21

    def __str__(self) -> str:
        return " ".join(str(card) for card in self.cards) or "(empty)"


def read_line(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nThanks for playing!")
        raise SystemExit(0)


def player_turn(deck: Deck, hand: Hand, bet: int, bankroll: int) -> tuple[int, bool]:
    """Run the player's decisions. Return the final bet and whether they busted."""
    while True:
        if hand.value > 21:
            print("Bust!")
            return bet, True
        action = read_line("Action [h]it / [s]tand / [d]ouble / [q]uit: ").strip().lower()
        if action in {"q", "quit"}:
            raise SystemExit("Thanks for playing!")
        if action in {"h", "hit"}:
            hand.add(deck.draw())
            print(f"You drew {hand.cards[-1]}. Hand: {hand} (total {hand.value})")
        elif action in {"s", "stand"}:
            return bet, False
        elif action in {"d", "double"}:
            if len(hand.cards) != 2:
                print("You can only double on your first two cards.")
                continue
            if bet * 2 > bankroll:
                print("You do not have enough bankroll to double.")
                continue
            bet *= 2
            hand.add(deck.draw())
            print(f"Double down! You drew {hand.cards[-1]}. Hand: {hand} "
                  f"(total {hand.value})")
            if hand.value > 21:
                print("Bust!")
                return bet, True
            return bet, False
        else:
            print("Please enter h, s, d or q.")


def dealer_play(deck: Deck, hand: Hand) -> None:
    while hand.value < 17:
        card = deck.draw()
        hand.add(card)
        print(f"Dealer draws {card}. Total: {hand.value}")
    print(f"Dealer stands on {hand.value}." if hand.value <= 21 else "Dealer busts!")


def settle(player: Hand, dealer: Hand, bet: int, bankroll: int) -> int:
    """Apply the result of a round and return the new bankroll."""
    player_blackjack = player.is_blackjack()
    dealer_blackjack = dealer.is_blackjack()

    if player_blackjack and dealer_blackjack:
        print("Both have blackjack. Push.")
        return bankroll
    if player_blackjack:
        print("Blackjack! You win 3:2.")
        return bankroll + int(bet * 1.5)
    if dealer_blackjack:
        print("Dealer has blackjack. You lose.")
        return bankroll - bet
    if dealer.value > 21:
        print("Dealer busts. You win!")
        return bankroll + bet
    if player.value > dealer.value:
        print("You win!")
        return bankroll + bet
    if player.value < dealer.value:
        print("Dealer wins.")
        return bankroll - bet
    print("Push. Your bet is returned.")
    return bankroll


def play_round(deck: Deck, bankroll: int) -> int:
    while True:
        raw = read_line(f"\nBankroll: ${bankroll}. Bet amount (q to quit): ").strip()
        if raw.lower() in {"q", "quit"}:
            raise SystemExit("Thanks for playing!")
        if raw.isdigit() and 0 < int(raw) <= bankroll:
            bet = int(raw)
            break
        print("Enter a whole number between 1 and your bankroll.")

    player = Hand()
    dealer = Hand()
    for _ in range(2):
        player.add(deck.draw())
        dealer.add(deck.draw())

    print(f"\nYour hand: {player}  (total {player.value})")
    print(f"Dealer shows: {dealer.cards[0]} and one hidden card")

    if player.is_blackjack() or dealer.is_blackjack():
        print(f"\nDealer's hand: {dealer}  (total {dealer.value})")
        return settle(player, dealer, bet, bankroll)

    bet, busted = player_turn(deck, player, bet, bankroll)
    if busted:
        print(f"You lose ${bet}.")
        return bankroll - bet

    print(f"\nYour final hand: {player}  (total {player.value})")
    dealer_play(deck, dealer)
    print(f"Dealer's final hand: {dealer}  (total {dealer.value})")
    return settle(player, dealer, bet, bankroll)


def main() -> None:
    print("=" * 46)
    print("                BLACKJACK")
    print("=" * 46)
    print("Blackjack pays 3:2. Dealer stands on 17.")
    rng = random.Random()
    deck = Deck(rng)
    bankroll = STARTING_BANKROLL
    rounds = 0

    while bankroll > 0:
        bankroll = play_round(deck, bankroll)
        rounds += 1
        if bankroll == 0:
            print("\nYou are out of money. Better luck next time!")
            break
        if rounds % 5 == 0:
            raw = read_line("Keep playing? [Y/n]: ").strip().lower()
            if raw in {"n", "no"}:
                break

    print(f"\nSession over after {rounds} round(s). Final bankroll: ${bankroll}")


if __name__ == "__main__":
    main()
