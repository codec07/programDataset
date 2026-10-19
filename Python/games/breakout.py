"""Breakout (tkinter).

Rules
-----
Bounce the ball off your paddle to smash every brick at the top of the
screen. You start with 3 lives; losing the ball costs one life. Clearing all
bricks wins the game. Higher rows are worth more points.

Controls
--------
* Left / Right or A / D - move the paddle
* Space                 - launch the ball
* P                     - pause / resume
* R                     - restart
* Esc                   - quit

Run
---
    python breakout.py
"""

from __future__ import annotations

import random
import tkinter as tk
from dataclasses import dataclass

WIDTH, HEIGHT = 760, 600
PADDLE_W, PADDLE_H = 104, 14
PADDLE_Y = HEIGHT - 46
BALL_R = 8
FRAME_MS = 16
ROWS, COLS = 5, 10
BRICK_GAP = 4
BRICK_TOP = 72
BRICK_SIDE = 34
ROW_COLORS = ("#ef5350", "#ffa726", "#ffee58", "#66bb6a", "#42a5f5")
ROW_POINTS = (50, 40, 30, 20, 10)


@dataclass
class Brick:
    x: float
    y: float
    w: float
    h: float
    row: int
    alive: bool = True

    @property
    def points(self) -> int:
        return ROW_POINTS[self.row]


class BreakoutGame:
    """Physics and scoring without any tkinter dependency."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        self.paddle_x = (WIDTH - PADDLE_W) / 2
        self.lives = 3
        self.score = 0
        self.paused = False
        self.game_over = False
        self.won = False
        self.ball_attached = True
        self.ball_x = WIDTH / 2
        self.ball_y = PADDLE_Y - BALL_R - 2
        self.dx = 0.0
        self.dy = 0.0
        self.bricks = self._make_bricks()

    def _make_bricks(self) -> list[Brick]:
        brick_w = (WIDTH - 2 * BRICK_SIDE - (COLS - 1) * BRICK_GAP) / COLS
        brick_h = 22
        bricks = []
        for row in range(ROWS):
            for col in range(COLS):
                x = BRICK_SIDE + col * (brick_w + BRICK_GAP)
                y = BRICK_TOP + row * (brick_h + BRICK_GAP)
                bricks.append(Brick(x, y, brick_w, brick_h, row))
        return bricks

    @property
    def bricks_left(self) -> int:
        return sum(brick.alive for brick in self.bricks)

    def move_paddle(self, direction: int) -> None:
        self.paddle_x = max(0, min(WIDTH - PADDLE_W,
                                   self.paddle_x + direction * 9))
        if self.ball_attached:
            self.ball_x = self.paddle_x + PADDLE_W / 2

    def launch(self) -> None:
        if self.ball_attached and not self.game_over and not self.paused:
            self.ball_attached = False
            speed = 5.6
            angle = self.rng.uniform(-0.45, 0.45)
            self.dx = speed * angle
            self.dy = -speed

    def _reset_ball(self) -> None:
        self.ball_attached = True
        self.ball_x = self.paddle_x + PADDLE_W / 2
        self.ball_y = PADDLE_Y - BALL_R - 2
        self.dx = self.dy = 0.0

    def _lose_life(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
        else:
            self._reset_ball()

    def update(self) -> None:
        if self.paused or self.game_over or self.ball_attached:
            return

        self.ball_x += self.dx
        self.ball_y += self.dy

        if self.ball_x - BALL_R <= 0:
            self.ball_x = BALL_R
            self.dx = abs(self.dx)
        elif self.ball_x + BALL_R >= WIDTH:
            self.ball_x = WIDTH - BALL_R
            self.dx = -abs(self.dx)

        if self.ball_y - BALL_R <= 0:
            self.ball_y = BALL_R
            self.dy = abs(self.dy)

        if self.ball_y - BALL_R > HEIGHT:
            self._lose_life()
            return

        # Paddle bounce, with angle based on where the ball strikes.
        if (self.dy > 0
                and PADDLE_Y - BALL_R <= self.ball_y + BALL_R <= PADDLE_Y + PADDLE_H
                and self.paddle_x - BALL_R <= self.ball_x <= self.paddle_x + PADDLE_W + BALL_R):
            self.ball_y = PADDLE_Y - BALL_R
            offset = (self.ball_x - (self.paddle_x + PADDLE_W / 2)) / (PADDLE_W / 2)
            self.dx = max(-6.5, min(6.5, offset * 6.5))
            self.dy = -abs(self.dy)

        # Brick collisions: at most one per frame keeps the bounce predictable.
        for brick in self.bricks:
            if not brick.alive:
                continue
            if (self.ball_x + BALL_R > brick.x and self.ball_x - BALL_R < brick.x + brick.w
                    and self.ball_y + BALL_R > brick.y
                    and self.ball_y - BALL_R < brick.y + brick.h):
                brick.alive = False
                self.score += brick.points
                brick_cx = brick.x + brick.w / 2
                brick_cy = brick.y + brick.h / 2
                overlap_x = (brick.w / 2 + BALL_R) - abs(self.ball_x - brick_cx)
                overlap_y = (brick.h / 2 + BALL_R) - abs(self.ball_y - brick_cy)
                if overlap_x < overlap_y:
                    self.dx = -self.dx
                else:
                    self.dy = -self.dy
                break

        if self.bricks_left == 0:
            self.game_over = True
            self.won = True


class BreakoutApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Breakout")
        self.root.resizable(False, False)
        self.game = BreakoutGame(rng=random.Random())
        self.keys: set[str] = set()
        self.job: str | None = None

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg="#0d1117", highlightthickness=0)
        self.canvas.pack()
        self.root.bind("<KeyPress>", self.on_press)
        self.root.bind("<KeyRelease>", self.on_release)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.schedule()
        self.draw()

    def close(self) -> None:
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self.root.destroy()

    def restart(self) -> None:
        self.game.reset()

    def schedule(self) -> None:
        self.job = self.root.after(FRAME_MS, self.tick)

    def tick(self) -> None:
        self.job = None
        if "left" in self.keys or "a" in self.keys:
            self.game.move_paddle(-1)
        if "right" in self.keys or "d" in self.keys:
            self.game.move_paddle(1)
        self.game.update()
        self.draw()
        self.schedule()

    def on_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys.add(key)
        if key == "space":
            self.game.launch()
        elif key == "p" and not self.game.game_over:
            self.game.paused = not self.game.paused
        elif key == "r":
            self.restart()
        elif key == "escape":
            self.close()

    def on_release(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def draw(self) -> None:
        self.canvas.delete("all")
        for brick in self.game.bricks:
            if brick.alive:
                self.canvas.create_rectangle(brick.x, brick.y, brick.x + brick.w,
                                             brick.y + brick.h,
                                             fill=ROW_COLORS[brick.row], outline="")

        self.canvas.create_rectangle(self.game.paddle_x, PADDLE_Y,
                                     self.game.paddle_x + PADDLE_W, PADDLE_Y + PADDLE_H,
                                     fill="#e0e0e0", outline="")
        self.canvas.create_oval(self.game.ball_x - BALL_R, self.game.ball_y - BALL_R,
                                self.game.ball_x + BALL_R, self.game.ball_y + BALL_R,
                                fill="#ffeb3b", outline="")

        self.canvas.create_text(20, 24, anchor="w", text=f"Score {self.game.score}",
                                fill="#e6edf3", font=("Consolas", 16, "bold"))
        self.canvas.create_text(WIDTH / 2, 24, text=f"Bricks {self.game.bricks_left}",
                                fill="#8b949e", font=("Consolas", 14))
        self.canvas.create_text(WIDTH - 20, 24, anchor="e",
                                text=f"Lives {'*' * self.game.lives}",
                                fill="#ff7b72", font=("Consolas", 16, "bold"))

        if self.game.ball_attached and not self.game.game_over:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 70,
                                    text="Press SPACE to launch",
                                    fill="#8b949e", font=("Segoe UI", 16))
        if self.game.paused:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2, text="PAUSED",
                                    fill="#ffeb3b", font=("Segoe UI", 32, "bold"))
        if self.game.game_over:
            message = "YOU WIN!" if self.game.won else "GAME OVER"
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 20, text=message,
                                    fill="#ffeb3b", font=("Segoe UI", 34, "bold"))
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 30,
                                    text=f"Score {self.game.score}   Press R to restart",
                                    fill="#cfd8dc", font=("Segoe UI", 15))


def main() -> None:
    root = tk.Tk()
    BreakoutApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
