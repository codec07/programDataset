"""A deliberately small, safe command shell with built-ins and subprocess.

Built-ins: ``pwd``, ``cd``, ``ls``, ``cat``, ``echo``, ``clear``, ``help``,
and ``exit``. External programs run without a shell, using an argument list
and ``subprocess.run``; no string is ever passed to ``cmd.exe`` or ``/bin/sh``.
External commands are disabled unless ``--allow-external`` is supplied, and a
list of destructive names remains blocked unless ``--allow-dangerous`` is used.

Usage:
    python mini_shell.py                     # interactive built-in shell
    python mini_shell.py --demo              # self-contained demonstration
    python mini_shell.py -c "pwd" -c "ls"
    python mini_shell.py --allow-external -c "python --version"

The demo uses a temporary directory and never touches the user's files.
"""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

DANGEROUS_NAMES = {
    "rm",
    "rmdir",
    "del",
    "erase",
    "format",
    "mkfs",
    "dd",
    "shutdown",
    "reboot",
    "halt",
    "sudo",
    "runas",
    "powershell",
    "pwsh",
    "cmd",
    "bash",
    "sh",
    "zsh",
}
MAX_CAT_BYTES = 1_000_000


class ShellExit(Exception):
    """Raised by the ``exit`` built-in to end a session."""

    def __init__(self, code: int = 0) -> None:
        super().__init__(str(code))
        self.code = code


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    output: str
    code: int


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        return token[1:-1]
    return token


class MiniShell:
    """A single-process shell whose working directory is explicit state."""

    def __init__(
        self,
        *,
        cwd: str | Path | None = None,
        allow_external: bool = False,
        allow_dangerous: bool = False,
        timeout: float = 5.0,
    ) -> None:
        self.cwd = Path(cwd or Path.cwd()).expanduser().resolve()
        if not self.cwd.is_dir():
            raise ValueError(f"working directory does not exist: {self.cwd}")
        self.allow_external = allow_external
        self.allow_dangerous = allow_dangerous
        self.timeout = timeout

    def _resolve(self, value: str) -> Path:
        candidate = Path(value).expanduser()
        return (candidate if candidate.is_absolute() else self.cwd / candidate).resolve()

    def run_line(self, line: str) -> CommandResult:
        """Parse and execute one line, returning text output and an exit code."""
        text = line.strip()
        if not text or text.startswith("#"):
            return CommandResult(line, "", 0)
        try:
            tokens = [_unquote(token) for token in shlex.split(text, posix=False)]
        except ValueError as exc:
            return CommandResult(line, f"parse error: {exc}", 2)
        if not tokens:
            return CommandResult(line, "", 0)
        command, arguments = tokens[0], tokens[1:]
        builtin = getattr(self, f"_builtin_{command}", None)
        if builtin is not None:
            try:
                output, code = builtin(arguments)
            except ShellExit:
                raise
            except Exception as exc:
                output, code = f"{command}: {type(exc).__name__}: {exc}", 1
            return CommandResult(line, output, code)
        return self._external(line, command, arguments)

    def _builtin_pwd(self, arguments: Sequence[str]) -> tuple[str, int]:
        if arguments:
            return "usage: pwd", 2
        return str(self.cwd), 0

    def _builtin_cd(self, arguments: Sequence[str]) -> tuple[str, int]:
        if len(arguments) > 1:
            return "usage: cd [directory]", 2
        target = self._resolve(arguments[0]) if arguments else Path.home()
        if not target.is_dir():
            return f"cd: not a directory: {target}", 1
        self.cwd = target
        return str(self.cwd), 0

    def _builtin_ls(self, arguments: Sequence[str]) -> tuple[str, int]:
        if len(arguments) > 1:
            return "usage: ls [path]", 2
        target = self._resolve(arguments[0]) if arguments else self.cwd
        if target.is_file():
            return f"{target.name}  ({target.stat().st_size} bytes)", 0
        if not target.is_dir():
            return f"ls: no such directory: {target}", 1
        rows: list[str] = []
        try:
            entries = sorted(target.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except OSError as exc:
            return f"ls: {exc}", 1
        for entry in entries:
            if entry.is_dir():
                rows.append(f"{entry.name}/")
            else:
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                rows.append(f"{entry.name}  ({size} bytes)")
        return ("\n".join(rows) if rows else "(empty directory)"), 0

    def _builtin_cat(self, arguments: Sequence[str]) -> tuple[str, int]:
        if not arguments:
            return "usage: cat FILE [FILE ...]", 2
        sections: list[str] = []
        code = 0
        for argument in arguments:
            target = self._resolve(argument)
            try:
                if not target.is_file():
                    raise FileNotFoundError("not a file")
                data = target.read_bytes()[:MAX_CAT_BYTES]
                text = data.decode("utf-8", errors="replace")
                if len(arguments) > 1:
                    sections.append(f"==> {target.name} <==")
                sections.append(text.rstrip("\n"))
            except OSError as exc:
                sections.append(f"cat: {argument}: {exc}")
                code = 1
        return "\n".join(sections), code

    def _builtin_echo(self, arguments: Sequence[str]) -> tuple[str, int]:
        return " ".join(arguments), 0

    def _builtin_clear(self, arguments: Sequence[str]) -> tuple[str, int]:
        if arguments:
            return "usage: clear", 2
        return "\x1b[2J\x1b[H", 0

    def _builtin_help(self, arguments: Sequence[str]) -> tuple[str, int]:
        return (
            "built-ins: pwd, cd [dir], ls [path], cat FILE..., echo ..., "
            "clear, help, exit [code]\n"
            f"external commands: {'enabled' if self.allow_external else 'disabled'} "
            "(use --allow-external); no shell expansion or redirection",
            0,
        )

    def _builtin_exit(self, arguments: Sequence[str]) -> tuple[str, int]:
        if len(arguments) > 1:
            return "usage: exit [code]", 2
        try:
            code = int(arguments[0]) if arguments else 0
        except ValueError:
            return "exit: code must be an integer", 2
        raise ShellExit(code)

    def _external(self, line: str, command: str, arguments: Sequence[str]) -> CommandResult:
        if not self.allow_external:
            return CommandResult(
                line,
                "external commands are disabled; restart with --allow-external",
                126,
            )
        name = Path(command).name.lower()
        if name.endswith(".exe"):
            name = name[:-4]
        if name in DANGEROUS_NAMES and not self.allow_dangerous:
            return CommandResult(line, f"{command}: blocked destructive command", 126)
        executable = shutil.which(command)
        if executable is None and not Path(command).is_file():
            return CommandResult(line, f"{command}: executable not found", 127)
        try:
            completed = subprocess.run(
                [command, *arguments],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CommandResult(line, f"{command}: timed out after {self.timeout:g}s", 124)
        except OSError as exc:
            return CommandResult(line, f"{command}: {exc}", 126)
        output = completed.stdout
        if completed.stderr:
            output += ("\n" if output else "") + completed.stderr
        return CommandResult(line, output.rstrip("\n"), completed.returncode)


def _demo() -> int:
    with tempfile.TemporaryDirectory(prefix="mini-shell-") as directory:
        root = Path(directory)
        (root / "notes").mkdir()
        (root / "hello.txt").write_text("hello from mini_shell\n", encoding="utf-8")
        shell = MiniShell(cwd=root, allow_external=True)
        commands = [
            "pwd",
            "echo mini shell demo",
            "ls",
            "cat hello.txt",
            "cd notes",
            "pwd",
            "cd ..",
            f'"{sys.executable}" --version',
            "exit 0",
        ]
        print(f"demo cwd: {root}")
        for command in commands:
            print(f"> {command}")
            try:
                result = shell.run_line(command)
            except ShellExit as exc:
                print(f"[exit {exc.code}]")
                return exc.code
            if result.output:
                print(result.output)
            print(f"[exit {result.code}]")
    return 0


def _interactive(shell: MiniShell) -> int:
    print("mini_shell: type 'help' for commands, 'exit' to quit")
    while True:
        try:
            line = input(f"{shell.cwd}> ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\n(use 'exit' to leave)")
            continue
        try:
            result = shell.run_line(line)
        except ShellExit as exc:
            return exc.code
        if result.output:
            print(result.output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safe miniature shell.")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--command", "-c", action="append", default=[], help="run one command and exit")
    parser.add_argument("--cwd", help="initial working directory")
    parser.add_argument("--allow-external", action="store_true")
    parser.add_argument("--allow-dangerous", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    if args.demo:
        return _demo()
    try:
        shell = MiniShell(
            cwd=args.cwd,
            allow_external=args.allow_external,
            allow_dangerous=args.allow_dangerous,
            timeout=args.timeout,
        )
    except ValueError as exc:
        parser.error(str(exc))
    if args.command:
        last_code = 0
        for command in args.command:
            try:
                result = shell.run_line(command)
            except ShellExit as exc:
                return exc.code
            if result.output:
                print(result.output)
            last_code = result.code
        return last_code
    return _interactive(shell)


if __name__ == "__main__":
    raise SystemExit(main())
