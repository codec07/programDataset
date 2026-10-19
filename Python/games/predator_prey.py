"""Predator-Prey Simulation (simulation).

Model
-----
An agent-based grid ecosystem on a wrapping (toroidal) field.

* Grass regrows randomly on empty cells.
* Rabbits wander, eat grass for energy, lose energy every step, and reproduce
  when well fed. They die at zero energy.
* Foxes wander, hunt rabbits for energy, lose energy every step, and
  reproduce when well fed. They die at zero energy.
* Population caps keep the simulation bounded.

The simulation is deterministic for a given ``--seed``. It prints periodic
population counts, a summary at the end, and can write per-step data to CSV.

Options
-------
    python predator_prey.py
    python predator_prey.py --steps 300 --seed 42
    python predator_prey.py --width 40 --height 25 --rabbits 100 --foxes 20
    python predator_prey.py --steps 200 --csv ecosystem.csv

CSV columns: ``step,rabbits,foxes,grass``.

Run
---
    python predator_prey.py --seed 1
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass

RABBIT_ENERGY = 5.0
FOX_ENERGY = 8.0
METABOLISM = 1.0
GRASS_ENERGY = 4.0
RABBIT_BREED_ENERGY = 8.0
FOX_BREED_ENERGY = 15.0
CHILD_RABBIT_ENERGY = 2.0
CHILD_FOX_ENERGY = 7.0
NEIGHBOURS = tuple((dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                   if (dx, dy) != (0, 0))


@dataclass
class Animal:
    x: int
    y: int
    energy: float


class Ecosystem:
    def __init__(self, width: int = 30, height: int = 20, rabbits: int = 60,
                 foxes: int = 12, rng: random.Random | None = None,
                 regrowth: float = 0.10) -> None:
        if rabbits + foxes > width * height:
            raise ValueError("too many animals for the grid")
        self.width, self.height = width, height
        self.rng = rng or random.Random()
        self.regrowth = regrowth
        self.step_number = 0
        self.max_rabbits = max(50, width * height // 2)
        self.max_foxes = max(25, width * height // 4)

        cells = [(x, y) for y in range(height) for x in range(width)]
        rabbit_cells = self.rng.sample(cells, rabbits)
        rabbit_set = set(rabbit_cells)
        remaining = [cell for cell in cells if cell not in rabbit_set]
        fox_cells = self.rng.sample(remaining, foxes)

        self.rabbits = [Animal(x, y, RABBIT_ENERGY) for x, y in rabbit_cells]
        self.foxes = [Animal(x, y, FOX_ENERGY) for x, y in fox_cells]
        self.grass = {(x, y) for x, y in remaining if self.rng.random() < 0.45}

    def _move(self, animal: Animal) -> None:
        dx, dy = self.rng.choice(NEIGHBOURS)
        animal.x = (animal.x + dx) % self.width
        animal.y = (animal.y + dy) % self.height

    def _grow_grass(self) -> None:
        # Visit every cell that has no grass and let it regrow with probability p.
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) not in self.grass and self.rng.random() < self.regrowth:
                    self.grass.add((x, y))

    def _rabbit_step(self) -> None:
        survivors: list[Animal] = []
        for rabbit in self.rabbits:
            self._move(rabbit)
            cell = (rabbit.x, rabbit.y)
            if cell in self.grass:
                self.grass.remove(cell)
                rabbit.energy += GRASS_ENERGY
            else:
                rabbit.energy -= METABOLISM

            if rabbit.energy <= 0:
                continue
            if (rabbit.energy >= RABBIT_BREED_ENERGY
                    and len(survivors) < self.max_rabbits):
                rabbit.energy -= CHILD_RABBIT_ENERGY
                survivors.append(Animal(rabbit.x, rabbit.y, CHILD_RABBIT_ENERGY))
            survivors.append(rabbit)
        self.rabbits = survivors

    def _fox_step(self) -> None:
        rabbit_at = {(rabbit.x, rabbit.y): rabbit for rabbit in self.rabbits}
        survivors: list[Animal] = []
        for fox in self.foxes:
            self._move(fox)
            prey = rabbit_at.pop((fox.x, fox.y), None)
            if prey is not None:
                fox.energy += 8.0
                self.rabbits.remove(prey)
            else:
                fox.energy -= METABOLISM

            if fox.energy <= 0:
                continue
            if (fox.energy >= FOX_BREED_ENERGY
                    and len(survivors) < self.max_foxes):
                fox.energy -= CHILD_FOX_ENERGY
                survivors.append(Animal(fox.x, fox.y, CHILD_FOX_ENERGY))
            survivors.append(fox)
        self.foxes = survivors

    def step(self) -> tuple[int, int, int]:
        self.step_number += 1
        self._grow_grass()
        self._rabbit_step()
        self._fox_step()
        return len(self.rabbits), len(self.foxes), len(self.grass)


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agent-based predator-prey simulation.")
    parser.add_argument("--width", type=positive_int, default=30, help="grid width")
    parser.add_argument("--height", type=positive_int, default=20, help="grid height")
    parser.add_argument("--rabbits", type=int, default=60, help="initial rabbits")
    parser.add_argument("--foxes", type=int, default=12, help="initial foxes")
    parser.add_argument("--steps", type=positive_int, default=200,
                        help="number of simulation steps")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--regrowth", type=float, default=0.10,
                        help="per-cell grass regrowth probability (default 0.10)")
    parser.add_argument("--csv", metavar="PATH", help="write per-step data to CSV")
    args = parser.parse_args(argv)
    if args.width < 5 or args.height < 5:
        parser.error("width and height must be at least 5")
    if args.rabbits < 0 or args.foxes < 0:
        parser.error("initial populations must be non-negative")
    if not 0.0 <= args.regrowth <= 1.0:
        parser.error("regrowth must be between 0 and 1")
    if args.rabbits + args.foxes > args.width * args.height:
        parser.error("too many initial animals for this grid")
    return args


def run(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)
    eco = Ecosystem(args.width, args.height, args.rabbits, args.foxes,
                    rng, args.regrowth)

    rows: list[tuple[int, int, int, int]] = []
    rabbit_peak = len(eco.rabbits)
    fox_peak = len(eco.foxes)
    rabbits_gone: int | None = 0 if not eco.rabbits else None
    foxes_gone: int | None = 0 if not eco.foxes else None
    rabbit_sum = len(eco.rabbits)
    fox_sum = len(eco.foxes)

    print(f"Predator-Prey: {args.width}x{args.height} grid, seed={args.seed}, "
          f"regrowth={args.regrowth:.2f}")
    print(f"Start: {len(eco.rabbits)} rabbits, {len(eco.foxes)} foxes, "
          f"{len(eco.grass)} grass cells")
    print()
    print(f"{'Step':>5}  {'Rabbits':>8}  {'Foxes':>6}  {'Grass':>6}")
    print("-" * 32)
    rows.append((0, len(eco.rabbits), len(eco.foxes), len(eco.grass)))
    print(f"{0:>5}  {len(eco.rabbits):>8}  {len(eco.foxes):>6}  {len(eco.grass):>6}")

    for _ in range(args.steps):
        rabbits, foxes, grass = eco.step()
        rows.append((eco.step_number, rabbits, foxes, grass))
        rabbit_sum += rabbits
        fox_sum += foxes
        rabbit_peak = max(rabbit_peak, rabbits)
        fox_peak = max(fox_peak, foxes)
        if rabbits == 0 and rabbits_gone is None:
            rabbits_gone = eco.step_number
        if foxes == 0 and foxes_gone is None:
            foxes_gone = eco.step_number
        if eco.step_number % 20 == 0 or eco.step_number == args.steps:
            print(f"{eco.step_number:>5}  {rabbits:>8}  {foxes:>6}  {grass:>6}")
        if rabbits == 0 and foxes == 0:
            print("(Both populations extinct; stopping early.)")
            break

    samples = eco.step_number + 1
    print()
    print("=" * 46)
    print("SUMMARY")
    print("=" * 46)
    print(f"Steps simulated     : {eco.step_number}")
    print(f"Final rabbits       : {len(eco.rabbits)}")
    print(f"Final foxes         : {len(eco.foxes)}")
    print(f"Peak rabbits / foxes: {rabbit_peak} / {fox_peak}")
    print(f"Mean rabbits / foxes: {rabbit_sum / samples:.1f} / {fox_sum / samples:.1f}")
    print(f"Rabbits extinct at  : {rabbits_gone if rabbits_gone is not None else 'never'}")
    print(f"Foxes extinct at    : {foxes_gone if foxes_gone is not None else 'never'}")
    if len(eco.rabbits) == 0 and len(eco.foxes) == 0:
        print("Outcome             : total extinction")
    elif len(eco.foxes) == 0:
        print("Outcome             : predators died out")
    elif len(eco.rabbits) == 0:
        print("Outcome             : prey died out")
    else:
        print("Outcome             : both populations persist")

    if args.csv:
        try:
            with open(args.csv, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["step", "rabbits", "foxes", "grass"])
                writer.writerows(rows)
        except OSError as error:
            raise SystemExit(f"Could not write CSV: {error}")
        print(f"Data written to {args.csv}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        run(args)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
