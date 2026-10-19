#!/usr/bin/env python3
"""Validate a .env file against a simple typed schema.

Schema syntax - one rule per line, blank lines and '#' comments allowed:

    KEY=str:required
    PORT=port
    DEBUG=bool:optional
    RATE=float
    HOMEPAGE=url
    CONTACT=email
    DATA_DIR=path

Types: str, int, float, bool, url, email, path, port.
Suffixes: ':required' (default) or ':optional', combinable with ':check-path'
for path values that must already exist.

The env parser understands comments, 'export KEY=value', single/double
quoted values and inline comments in unquoted values. Duplicate keys and
malformed lines are reported; the last duplicate wins.

Exit status: 0 all rules satisfied, 1 validation errors, 2 unreadable input.

Usage:
    python env_validator.py --schema schema.txt --env .env
    python env_validator.py --schema schema.txt --env .env.example --json
    python env_validator.py --schema schema.txt --env .env --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

SCHEMA_TYPES = {"str", "int", "float", "bool", "url", "email", "path", "port"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
ASSIGNMENT_RE = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


@dataclass
class Rule:
    """One schema rule."""

    key: str
    kind: str
    required: bool = True
    check_path: bool = False


@dataclass
class Issue:
    """A validation or parsing problem."""

    key: str
    message: str
    severity: str = "error"


def read_text(path: Path) -> str:
    """Read UTF-8 text, converting errors into exit status 2."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"error: file not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    except IsADirectoryError:
        print(f"error: is a directory: {path}", file=sys.stderr)
        raise SystemExit(2)
    except UnicodeDecodeError as exc:
        print(f"error: {path} is not valid UTF-8 ({exc.reason})", file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def parse_schema(text: str) -> list[Rule]:
    """Parse schema lines, raising SystemExit on malformed rules."""
    rules: list[Rule] = []
    seen: set[str] = set()
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"error: schema line {number}: expected KEY=TYPE")
        key, spec = (part.strip() for part in line.split("=", 1))
        if not KEY_RE.match(key):
            raise SystemExit(f"error: schema line {number}: invalid key '{key}'")
        if key in seen:
            raise SystemExit(f"error: schema line {number}: duplicate key '{key}'")
        seen.add(key)

        parts = [part.strip().lower() for part in spec.split(":") if part.strip()]
        if not parts:
            raise SystemExit(f"error: schema line {number}: missing type for {key}")
        kind = parts[0]
        if kind not in SCHEMA_TYPES:
            raise SystemExit(
                f"error: schema line {number}: unknown type '{kind}' "
                f"(choose from {', '.join(sorted(SCHEMA_TYPES))})"
            )
        required = True
        check_path = False
        for option in parts[1:]:
            if option == "required":
                required = True
            elif option == "optional":
                required = False
            elif option == "check-path":
                check_path = True
            else:
                raise SystemExit(
                    f"error: schema line {number}: unknown option '{option}'"
                )
        if check_path and kind != "path":
            raise SystemExit(
                f"error: schema line {number}: check-path only applies to path"
            )
        rules.append(Rule(key, kind, required, check_path))

    if not rules:
        raise SystemExit("error: schema contains no rules")
    return rules


def unquote(value: str) -> str:
    """Remove matching quotes and decode simple backslash escapes."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        inner = value[1:-1]
        if value[0] == '"':
            return (
                inner.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )
        return inner
    # Strip an inline comment introduced by whitespace + '#'.
    return re.split(r"\s+#", value, maxsplit=1)[0].strip()


def parse_env(text: str) -> tuple[dict[str, str], list[Issue]]:
    """Parse .env text into a mapping plus parse-level issues."""
    values: dict[str, str] = {}
    issues: list[Issue] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = ASSIGNMENT_RE.match(line)
        if not match:
            issues.append(Issue("", f"line {number}: not a KEY=value assignment"))
            continue
        key, raw_value = match.group(1), match.group(2)
        if key in values:
            issues.append(Issue(key, f"line {number}: duplicate key (last value wins)", "warning"))
        values[key] = unquote(raw_value)
    return values, issues


def validate_value(rule: Rule, value: str) -> str | None:
    """Return an error message for an invalid value, or None."""
    if value == "":
        return "value is empty"
    if rule.kind == "str":
        return None
    if rule.kind == "int":
        try:
            int(value)
        except ValueError:
            return f"expected an integer, got {value!r}"
        return None
    if rule.kind == "float":
        try:
            number = float(value)
        except ValueError:
            return f"expected a number, got {value!r}"
        if number != number or number in (float("inf"), float("-inf")):
            return "expected a finite number"
        return None
    if rule.kind == "bool":
        if value.lower() not in TRUE_VALUES | FALSE_VALUES:
            return f"expected a boolean, got {value!r} (use true/false/1/0/yes/no)"
        return None
    if rule.kind == "port":
        try:
            port = int(value)
        except ValueError:
            return f"expected a port number, got {value!r}"
        if not 1 <= port <= 65535:
            return "port must be between 1 and 65535"
        return None
    if rule.kind == "url":
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return f"expected an http(s) URL, got {value!r}"
        return None
    if rule.kind == "email":
        if not EMAIL_RE.match(value):
            return f"expected an email address, got {value!r}"
        return None
    if rule.kind == "path":
        if rule.check_path and not Path(value).exists():
            return f"path does not exist: {value}"
        return None
    return None


def validate(rules: Sequence[Rule], values: dict[str, str],
             strict: bool) -> list[Issue]:
    """Check every rule and optionally flag unknown variables."""
    issues: list[Issue] = []
    for rule in rules:
        if rule.key not in values:
            if rule.required:
                issues.append(Issue(rule.key, "required variable is missing"))
            continue
        problem = validate_value(rule, values[rule.key])
        if problem:
            issues.append(Issue(rule.key, problem))
    if strict:
        known = {rule.key for rule in rules}
        for key in values:
            if key not in known:
                issues.append(Issue(key, "variable is not described by the schema", "warning"))
    return issues


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a .env file against a typed schema.",
        epilog="Schema lines look like KEY=int:required or DEBUG=bool:optional.",
    )
    parser.add_argument("--schema", required=True, help="schema file")
    parser.add_argument("--env", default=".env", help=".env file to validate (default: .env)")
    parser.add_argument("--strict", action="store_true",
                        help="warn about variables missing from the schema")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit JSON instead of text")
    args = parser.parse_args(argv)
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    rules = parse_schema(read_text(Path(args.schema)))
    values, issues = parse_env(read_text(Path(args.env)))
    issues.extend(validate(rules, values, args.strict))

    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]

    if args.as_json:
        print(json.dumps({
            "env": args.env,
            "schema": args.schema,
            "checked": len(rules),
            "errors": [asdict(issue) for issue in errors],
            "warnings": [asdict(issue) for issue in warnings],
            "valid": not errors,
        }, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            label = "warning" if issue.severity == "warning" else "error"
            key = f"{issue.key}: " if issue.key else ""
            print(f"{label}: {key}{issue.message}", file=sys.stderr)
        if errors:
            print(
                f"FAILED: {len(errors)} error(s), {len(warnings)} warning(s), "
                f"{len(rules)} rule(s) checked.",
                file=sys.stderr,
            )
        else:
            print(
                f"OK: {len(rules)} rule(s) checked, {len(warnings)} warning(s).",
                file=sys.stderr,
            )
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
