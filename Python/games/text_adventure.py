"""Text Adventure: The Dark Lighthouse (terminal).

Story
-----
A storm has wrecked your boat on a rocky island. The only way to summon help
is to light the old lighthouse beacon. Explore the tower, find what the lamp
needs, and escape before the tide turns.

Rules
-----
Move between rooms, pick up items, and figure out how to light the lamp.
The cellar is locked; a brass key is hidden somewhere in the tower.

Controls
--------
    look                  describe the current room
    go <direction>        north/south/east/west/up/down (or n/s/e/w/u/d)
    take <item>           pick up an item
    drop <item>           put an item down
    inventory (or i)      list what you carry
    read <item>           read a readable item
    light lamp            try to light the beacon in the lamp room
    help                  show this list
    quit                  leave the game

Ctrl+C / Ctrl+D also exit.

Run
---
    python text_adventure.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

DIRECTIONS = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "u": "up", "d": "down",
    "north": "north", "south": "south", "east": "east", "west": "west",
    "up": "up", "down": "down",
}

ITEM_TEXT = {
    "note": "A water-stained note: 'To wake the lamp you need fuel, a battery "
            "and matches. The cellar key hangs in the storeroom.'",
    "brass key": "A small brass key, green with salt. It might open the cellar.",
    "matches": "A dry box of matches. Useful if you find something to light.",
    "fuel can": "A red can with a little lamp oil left inside.",
    "battery": "A heavy glass battery. It still holds a charge.",
}


@dataclass
class Room:
    name: str
    description: str
    exits: dict[str, str]
    items: list[str] = field(default_factory=list)


def build_rooms() -> dict[str, Room]:
    return {
        "shore": Room(
            "Rocky Shore",
            "Cold surf crashes over black rocks. A narrow path climbs north "
            "toward the lighthouse. A curled note is wedged under a stone.",
            {"north": "base"},
            ["note"],
        ),
        "base": Room(
            "Lighthouse Base",
            "Salt and old oil hang in the air. Stairs spiral upward. A "
            "storeroom lies north, a workshop east, and a cellar hatch leads "
            "down.",
            {"north": "storeroom", "east": "workshop", "up": "lamp_room",
             "down": "cellar", "south": "shore"},
        ),
        "storeroom": Room(
            "Storeroom",
            "Dusty tins line the shelves. A brass key hangs from a hook, and "
            "a box of matches sits on a crate.",
            {"south": "base"},
            ["brass key", "matches"],
        ),
        "workshop": Room(
            "Workshop",
            "Rusted tools cover the bench. A red fuel can stands in the "
            "corner beside coils of rope.",
            {"west": "base"},
            ["fuel can"],
        ),
        "cellar": Room(
            "Cellar",
            "A damp stone cellar. Broken crates are piled in the corner, and "
            "a heavy glass battery lies half-buried in the straw.",
            {"up": "base"},
            ["battery"],
        ),
        "lamp_room": Room(
            "Lamp Room",
            "The great lens fills the room. The fuel tank is empty, the "
            "battery socket is bare, and the lamp wick is dry.",
            {"down": "base"},
        ),
    }


class Adventure:
    """The complete game state and command interpreter."""

    def __init__(self) -> None:
        self.rooms = build_rooms()
        self.location = "shore"
        self.inventory: list[str] = []
        self.cellar_unlocked = False
        self.won = False
        self.turns = 0

    @property
    def room(self) -> Room:
        return self.rooms[self.location]

    def look(self) -> str:
        room = self.room
        lines = [room.name, room.description, ""]
        exits = []
        for direction, target in sorted(room.exits.items()):
            name = self.rooms[target].name
            if self.location == "base" and direction == "down" and not self.cellar_unlocked:
                name += " (locked)"
            exits.append(f"{direction} to {name}")
        lines.append("Exits: " + ", ".join(exits) + ".")
        if room.items:
            lines.append("You see: " + ", ".join(room.items) + ".")
        else:
            lines.append("There is nothing else here.")
        return "\n".join(lines)

    def move(self, direction: str) -> str:
        direction = DIRECTIONS.get(direction.lower(), direction.lower())
        if direction not in self.room.exits:
            return f"You can't go {direction} from here."
        if self.location == "base" and direction == "down" and not self.cellar_unlocked:
            if "brass key" in self.inventory:
                self.cellar_unlocked = True
                self.location = "cellar"
                return ("The brass key turns with a gritty click. You climb down "
                        "into the cellar.\n\n" + self.look())
            return "The cellar hatch is locked. You need a key."
        self.location = self.room.exits[direction]
        return f"You go {direction}.\n\n" + self.look()

    def find_item(self, name: str) -> str | None:
        name = " ".join(name.lower().split())
        matches = [item for item in self.room.items if item == name]
        if matches:
            return matches[0]
        matches = [item for item in self.room.items if name in item]
        if len(matches) == 1:
            return matches[0]
        matches = [item for item in self.inventory if item == name]
        if matches:
            return matches[0]
        matches = [item for item in self.inventory if name in item]
        return matches[0] if len(matches) == 1 else None

    def take(self, name: str) -> str:
        item = self.find_item(name)
        if item is None or item not in self.room.items:
            return f"There is no {name} here to take."
        self.room.items.remove(item)
        self.inventory.append(item)
        return f"You take the {item}."

    def drop(self, name: str) -> str:
        item = self.find_item(name)
        if item is None or item not in self.inventory:
            return f"You aren't carrying a {name}."
        self.inventory.remove(item)
        self.room.items.append(item)
        return f"You drop the {item}."

    def read(self, name: str) -> str:
        item = self.find_item(name)
        if item is None or item not in self.inventory:
            return "You need to be carrying that to read it."
        if item == "note":
            return ITEM_TEXT["note"]
        return f"The {item} has nothing written on it."

    def show_inventory(self) -> str:
        if not self.inventory:
            return "Your pockets are empty."
        return "You are carrying: " + ", ".join(self.inventory) + "."

    def light_lamp(self) -> str:
        if self.location != "lamp_room":
            return "There is no lamp here to light."
        missing = [item for item in ("fuel can", "battery", "matches")
                   if item not in self.inventory]
        if missing:
            return "The lamp won't light. You still need: " + ", ".join(missing) + "."
        self.won = True
        return ("You pour in the fuel, seat the battery and strike a match. "
                "The wick catches with a soft roar, and the great lens throws a "
                "beam across the sea. Hours later a rescue boat answers the "
                "light.\n\n*** YOU ESCAPE THE ISLAND. YOU WIN! ***")

    def execute(self, line: str) -> str:
        """Run one command and return the text to display."""
        line = line.strip().lower()
        if not line:
            return "Type 'help' for the command list."
        self.turns += 1
        parts = line.split(maxsplit=1)
        command, argument = parts[0], (parts[1] if len(parts) > 1 else "")

        if command in {"help", "h", "?"}:
            return ("Commands: look, go <direction>, take <item>, drop <item>, "
                    "inventory, read <item>, light lamp, help, quit.")
        if command in {"look", "l"}:
            return self.look()
        if command in {"go", "move", "walk"}:
            if not argument:
                return "Go where? Try 'go north'."
            return self.move(argument)
        if command in {"take", "get", "grab"}:
            if not argument:
                return "Take what?"
            return self.take(argument)
        if command in {"drop", "put"}:
            if not argument:
                return "Drop what?"
            return self.drop(argument)
        if command in {"inventory", "inv", "i"}:
            return self.show_inventory()
        if command in {"read", "examine"}:
            if not argument:
                return "Read what?"
            return self.read(argument)
        if command == "light":
            if argument in {"lamp", "beacon", "lamp lamp"}:
                return self.light_lamp()
            return "What do you want to light?"
        if command == "use":
            if argument in {"lamp", "beacon", "lamp lamp"}:
                return self.light_lamp()
            if "key" in argument:
                return ("The brass key fits the cellar hatch at the base of "
                        "the tower. Go down there to use it.")
            if argument in {"note", "matches", "fuel can", "battery"}:
                return f"Using the {argument} here does nothing useful."
            return "What do you want to use?"
        if command in {"quit", "exit"}:
            return "__QUIT__"
        return f"I don't understand '{command}'. Type 'help' for commands."


def read_line(prompt: str) -> str | None:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def main() -> None:
    print("=" * 58)
    print("            THE DARK LIGHTHOUSE")
    print("=" * 58)
    print("A storm has wrecked your boat. Light the beacon to signal for help.")
    print("Type 'help' at any time.\n")

    game = Adventure()
    print(game.look())
    while not game.won:
        raw = read_line("\n> ")
        if raw is None:
            print("You leave the island to its storms. Goodbye!")
            return
        result = game.execute(raw)
        if result == "__QUIT__":
            print("You give up on the lighthouse and wait by the shore. Goodbye!")
            return
        print(result)

    print(f"\nCompleted in {game.turns} turns. Thanks for playing!")


if __name__ == "__main__":
    main()
