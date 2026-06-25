# -*- coding: utf-8 -*-
"""Query the running Everything instance through its official CLI, ``es.exe``.

Everything (voidtools) keeps an instant index of the whole filesystem; ``es.exe``
is its command-line client. We shell out to it and parse the CSV output (UTF-8).
Requires Everything to be installed and running. Knows nothing about Flow Launcher.
"""

import csv
import os
import subprocess
import tempfile
from collections import namedtuple

Result = namedtuple("Result", ["name", "path", "size", "date", "is_dir"])

TIMEOUT = 6
_FILE_DIR = os.path.abspath(os.path.dirname(__file__))

# Hide the console window when spawning es.exe.
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW


class EverythingError(Exception):
    """Raised with a readable message when a search cannot be performed."""


def find_es(configured=""):
    """Locate es.exe: explicit setting -> bundled tools/ -> PATH -> Everything dir."""
    candidates = [
        configured,
        os.path.join(_FILE_DIR, "tools", "es.exe"),
        "es.exe",  # PATH
        r"C:\Program Files\Everything\es.exe",
        r"C:\Program Files (x86)\Everything\es.exe",
    ]
    for cand in candidates:
        if not cand:
            continue
        if os.path.isfile(cand):
            return cand
        # a bare command name (no path separator) -> trust PATH resolution
        if os.sep not in cand and "/" not in cand:
            return cand
    return None


def search(query, es_path="", limit=30, sort=""):
    """Return a list of Result for ``query`` (Everything search syntax)."""
    exe = find_es(es_path)
    if not exe:
        raise EverythingError("es.exe introuvable (voir réglages / README)")

    # es.exe's stdout encoding follows the (often absent) console code page, which
    # mangles non-ASCII names. Exporting to a CSV file is reliably UTF-8.
    fd, tmp = tempfile.mkstemp(suffix=".csv", prefix="flow_es_")
    os.close(fd)
    args = [
        exe,
        "-n", str(max(1, int(limit))),
        "-export-csv", tmp, "-no-header",
        "-full-path-and-name", "-size", "-date-modified", "-attributes",
    ]
    if sort:
        args += ["-sort", sort]
    args.append(query)

    try:
        proc = subprocess.run(
            args, capture_output=True, timeout=TIMEOUT, creationflags=_NO_WINDOW,
        )
        if proc.returncode != 0:
            err = (proc.stderr or b"").decode("utf-8", "replace").strip()
            # es returns an error when the Everything service/app is not running.
            if "not running" in err.lower() or proc.returncode == 8:
                raise EverythingError("Everything n'est pas lancé")
            raise EverythingError(err or f"es.exe a échoué (code {proc.returncode})")

        with open(tmp, "r", encoding="utf-8-sig", errors="replace", newline="") as fh:
            text = fh.read()
    except FileNotFoundError:
        raise EverythingError("es.exe introuvable (voir réglages / README)")
    except subprocess.TimeoutExpired:
        raise EverythingError("Everything n'a pas répondu (délai dépassé)")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    results = []
    for row in csv.reader(text.splitlines()):
        if len(row) < 4:
            continue
        path, size, date, attr = row[0], row[1], row[2], row[3]
        # es -attributes prints DOS attribute letters (D=directory, R, H, S, A...).
        is_dir = "D" in (attr or "").upper()
        results.append(Result(
            name=os.path.basename(path) or path,
            path=path,
            size=_human_size(size, is_dir),
            date=date,
            is_dir=is_dir,
        ))
    return results


def _human_size(size, is_dir):
    if is_dir:
        return "Dossier"
    try:
        n = int(size)
    except (TypeError, ValueError):
        return ""
    units = ["o", "Ko", "Mo", "Go", "To"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{int(value)} {unit}" if unit == "o" else f"{value:.1f} {unit}"
        value /= 1024
    return ""
