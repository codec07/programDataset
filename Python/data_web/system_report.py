"""Print a system report: OS, CPU, memory, disks, network and Python details.

Uses only the standard library (platform, os, socket, shutil, ctypes).  No
psutil and no network access.  Output is human-readable by default and JSON
with ``--json``.

Usage:
    python system_report.py
    python system_report.py --json
    python system_report.py --demo        # same collection, compact output
    python system_report.py --output report.json --force
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import shutil
import socket
import sys
import time
from pathlib import Path
from typing import Any

GB = 1024 ** 3


def memory_info() -> dict[str, int] | None:
    """Total/available RAM in bytes, using platform-specific APIs."""
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        try:
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
                return {"total": int(status.ullTotalPhys),
                        "available": int(status.ullAvailPhys)}
        except (AttributeError, OSError):
            return None
        return None
    if sys.platform.startswith("linux"):
        try:
            values: dict[str, int] = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                for line in fh:
                    key, _, rest = line.partition(":")
                    if key in ("MemTotal", "MemAvailable"):
                        values[key] = int(rest.split()[0]) * 1024
            if "MemTotal" in values:
                return {"total": values["MemTotal"],
                        "available": values.get("MemAvailable", 0)}
        except (OSError, ValueError, IndexError):
            return None
    return None


def uptime_seconds() -> float | None:
    if os.name == "nt":
        try:
            return ctypes.windll.kernel32.GetTickCount64() / 1000.0  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            return None
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as fh:
            return float(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


def human_bytes(value: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def collect() -> dict[str, Any]:
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except OSError:
        local_ip = "unresolved"
    disks = []
    seen: set[str] = set()
    for root in ("/", os.environ.get("SystemDrive", "C:") + os.sep):
        if os.name == "nt" and root.startswith("/"):
            continue
        if not os.path.exists(root) or root in seen:
            continue
        seen.add(root)
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        disks.append({
            "mount": root,
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "percent_used": round(usage.used / usage.total * 100, 1)
            if usage.total else 0.0,
        })

    mem = memory_info()
    return {
        "host": {
            "hostname": hostname,
            "local_ip": local_ip,
            "user": os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
            "uptime_seconds": uptime_seconds(),
        },
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "bits": 64 if sys.maxsize > 2 ** 32 else 32,
        },
        "cpu": {
            "logical_cores": os.cpu_count(),
            "processor": platform.processor() or "unknown",
        },
        "memory": ({"total": mem["total"], "available": mem["available"],
                    "percent_used": round((mem["total"] - mem["available"])
                                          / mem["total"] * 100, 1)}
                   if mem and mem["total"] else None),
        "disks": disks,
        "environment": {
            "cwd": os.getcwd(),
            "encoding": sys.getdefaultencoding(),
            "filesystem_encoding": sys.getfilesystemencoding(),
            "temp_dir": os.environ.get("TEMP") or os.environ.get("TMPDIR") or "unknown",
        },
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def render(report: dict[str, Any]) -> str:
    host, osinfo = report["host"], report["os"]
    cpu, pyinfo = report["cpu"], report["python"]
    lines = [
        "=" * 58,
        " SYSTEM REPORT",
        "=" * 58,
        f"Host      : {host['hostname']} ({host['local_ip']})",
        f"User      : {host['user']}",
        f"Uptime    : {format_duration(host['uptime_seconds'])}",
        f"OS        : {osinfo['system']} {osinfo['release']} ({osinfo['machine']})",
        f"Platform  : {osinfo['platform']}",
        f"Python    : {pyinfo['version']} {pyinfo['implementation']} {pyinfo['bits']}-bit",
        f"CPU       : {cpu['logical_cores']} logical core(s) - {cpu['processor'][:40]}",
    ]
    mem = report["memory"]
    if mem:
        lines.append(
            f"Memory    : {human_bytes(mem['total'] - mem['available'])} used / "
            f"{human_bytes(mem['total'])} total ({mem['percent_used']}%)")
    else:
        lines.append("Memory    : unavailable on this platform")
    lines.append("Disks     :")
    for disk in report["disks"]:
        lines.append(
            f"  {disk['mount']:<8} {human_bytes(disk['used']):>10} used / "
            f"{human_bytes(disk['total']):>10} ({disk['percent_used']}%)")
    if not report["disks"]:
        lines.append("  (none detected)")
    env = report["environment"]
    lines.append(f"Cwd       : {env['cwd']}")
    lines.append(f"Temp      : {env['temp_dir']}")
    lines.append("=" * 58)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Standard-library system report.")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--output", type=Path, help="write report to a file")
    p.add_argument("--force", action="store_true")
    p.add_argument("--demo", action="store_true",
                   help="collect and print a compact report (offline)")
    args = p.parse_args(argv)

    if args.output and args.output.exists() and not args.force:
        print(f"error: {args.output} exists (use --force)", file=sys.stderr)
        return 2

    report = collect()
    text = json.dumps(report, indent=2) if (args.json or args.output) else render(report)
    if args.demo and not args.output:
        text = render(report).replace("=" * 58, "-" * 40)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"wrote report -> {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
