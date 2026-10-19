"""Pong (tkinter).

Rules
-----
The left paddle is yours, the right paddle is the computer. Hit the ball past
your opponent to score a point. The first player to 7 points wins. The ball
speeds up slightly with every paddle hit.

Controls
--------
* W / S or Up / Down - move your paddle
* Space              - pause / resume
* R                  - restart
* Esc                - quit

Run
---
    python pong.py
"""

from __future__ import annotations

import random
import tkinter as tk

WIDTH, HEIGHT = 800, 500
PADDLE_W, PADDLE_H = 12, 90
BALL_R = 8
PADDLE_SPEED = 8
CPU_SPEED = 5.5
WIN_SCORE = 7
FRAME_MS = 16
MARGIN = 28


class PongGame:
    """Game state and physics, independent of tkinter."""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT,
                 rng: random.Random | None = None) -> None:
        self.width, self.height = width, height
        self.rng = rng or random.Random()
        self.reset()

    def reset(self) -> None:
        self.player_y = (self.height - PADDLE_H) / 2
        self.cpu_y = (self.height - PADDLE_H) / 2
        self.player_score = 0
        self.cpu_score = 0
        self.paused = False
        self.game_over = False
        self.serve_delay = 45
        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        self.vx = 5.0
        self.vy = 3.0

    def reset_ball(self, toward_player: bool) -> None:
        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        self.serve_delay = 45
        speed = 5.0
        angle = self.rng.uniform(-0.6, 0.6)
        direction = -1 if toward_player else 1
        self.vx = speed * direction
        self.vy = speed * angle

    def move_player(self, direction: int) -> None:
        """direction is -1 (up) or +1 (down)."""
        self.player_y = max(0, min(self.height - PADDLE_H,
                                   self.player_y + direction * PADDLE_SPEED))

    def clamp_ball(self) -> None:
        self.ball_y = max(BALL_R, min(self.height - BALL_R, self.ball_y))

    def paddle_hit(self, offset: float) -> None:
        """Bounce the ball, steering by where it struck the paddle."""
        self.vx *= -1.06
        self.vx = max(-18.0, min(18.0, self.vx))
        self.vy += offset * 0.18
        self.vy = max(-9.0, min(9.0, self.vy))

    def update(self) -> None:
        if self.paused or self.game_over:
            return
        if self.serve_delay > 0:
            self.serve_delay -= 1
            return

        # Simple AI: follow the ball only when it is heading toward the CPU.
        target = self.ball_y - PADDLE_H / 2 if self.vx > 0 else self.height / 2 - PADDLE_H / 2
        diff = target - self.cpu_y
        if abs(diff) > 3:
            self.cpu_y += max(-CPU_SPEED, min(CPU_SPEED, diff))
        self.cpu_y = max(0, min(self.height - PADDLE_H, self.cpu_y))

        self.ball_x += self.vx
        self.ball_y += self.vy

        if self.ball_y - BALL_R <= 0:
            self.ball_y = BALL_R
            self.vy = abs(self.vy)
        elif self.ball_y + BALL_R >= self.height:
            self.ball_y = self.height - BALL_R
            self.vy = -abs(self.vy)

        player_x = MARGIN
        cpu_x = self.width - MARGIN - PADDLE_W

        if (self.vx < 0
                and self.ball_x - BALL_R <= player_x + PADDLE_W
                and self.ball_x + BALL_R >= player_x
                and self.player_y - BALL_R <= self.ball_y
                <= self.player_y + PADDLE_H + BALL_R):
            self.ball_x = player_x + PADDLE_W + BALL_R
            offset = (self.ball_y - (self.player_y + PADDLE_H / 2)) / (PADDLE_H / 2)
            self.paddle_hit(offset)

        if (self.vx > 0
                and self.ball_x + BALL_R >= cpu_x
                and self.ball_x - BALL_R <= cpu_x + PADDLE_W
                and self.cpu_y - BALL_R <= self.ball_y
                <= self.cpu_y + PADDLE_H + BALL_R):
            self.ball_x = cpu_x - BALL_R
            offset = (self.ball_y - (self.cpu_y + PADDLE_H / 2)) / (PADDLE_H / 2)
            self.paddle_hit(offset)

        if self.ball_x + BALL_R < 0:
            self.cpu_score += 1
            self._after_point()
        elif self.ball_x - BALL_R > self.width:
            self.player_score += 1
            self._after_point()

    def _after_point(self) -> None:
        if self.player_score >= WIN_SCORE or self.cpu_score >= WIN_SCORE:
            self.game_over = True
            return
        self.reset_ball(toward_player=self.player_score <= self.cpu_score)


class PongApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Pong")
        self.root.resizable(False, False)
        self.game = PongGame(rng=random.Random())
        self.keys: set[str] = set()
        self.job: str | None = None

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg="#0b0f14", highlightthickness=0)
        self.canvas.pack()

        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.schedule()
        self.draw()

    def close(self) -> None:
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self.root.destroy()

    def schedule(self) -> None:
        self.job = self.root.after(FRAME_MS, self.tick)

    def tick(self) -> None:
        self.job = None
        if "w" in self.keys or "up" in self.keys:
            self.game.move_player(-1)
        if "s" in self.keys or "down" in self.keys:
            self.game.move_player(1)
        self.game.update()
        self.draw()
        self.schedule()

    def on_key_press(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        self.keys.add(key)
        if key == "space" and not self.game.game_over:
            self.game.paused = not self.game.paused
        elif key == "r":
            self.game.reset()
        elif key == "escape":
            self.close()

    def on_key_release(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def draw(self) -> None:
        self.canvas.delete("all")
        for y in range(0, HEIGHT, 28):
            self.canvas.create_rectangle(WIDTH / 2 - 2, y, WIDTH / 2 + 2, y + 14,
                                         fill="#1e2a36", outline="")
        self.canvas.create_text(200, 60, text=str(self.game.player_score),
                                fill="#4fc3f7", font=("Consolas", 46, "bold"))
        self.canvas.create_text(WIDTH - 200, 60, text=str(self.game.cpu_score),
                                fill="#ef5350", font=("Consolas", 46, "bold"))

        self.canvas.create_rectangle(MARGIN, self.game.player_y, MARGIN + PADDLE_W,
                                     self.game.player_y + PADDLE_H,
                                     fill="#4fc3f7", outline="")
        cpu_x = WIDTH - MARGIN - PADDLE_W
        self.canvas.create_rectangle(cpu_x, self.game.cpu_y, cpu_x + PADDLE_W,
                                     self.game.cpu_y + PADDLE_H,
                                     fill="#ef5350", outline="")
        self.canvas.create_oval(self.game.ball_x - BALL_R, self.game.ball_y - BALL_R,
                                self.game.ball_x + BALL_R, self.game.ball_y + BALL_R,
                                fill="#fff176", outline="")

        if self.game.serve_delay > 0 and not self.game.game_over:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 60, text="Get ready...",
                                    fill="#90a4ae", font=("Segoe UI", 16))
        if self.game.paused and not self.game.game_over:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2,
                                    text="PAUSED", fill="#ffeb3b",
                                    font=("Segoe UI", 32, "bold"))
        if self.game.game_over:
            winner = "You win!" if self.game.player_score > self.game.cpu_score else "Computer wins"
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 20, text=winner,
                                    fill="#ffeb3b", font=("Segoe UI", 32, "bold"))
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 30,
                                    text="Press R to play again", fill="#cfd8dc",
                                    font=("Segoe UI", 16))


def main() -> None:
    root = tk.Tk()
    PongApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
