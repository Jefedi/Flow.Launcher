# -*- coding: utf-8 -*-
"""Local persistence for the Notes plugin.

Notes are stored as JSON in a stable per-user folder (outside the plugin
directory, so they survive a redeploy):

    %APPDATA%/FlowLauncher/Notes/notes.json

Each note: {"id": str, "text": str, "created": float, "pinned": bool}.
This module knows nothing about Flow Launcher.
"""

import json
import os
import tempfile
import time
import uuid


def _data_dir():
    base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    folder = os.path.join(base, "FlowLauncher", "Notes")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = tempfile.gettempdir()
    return folder


def _path():
    return os.path.join(_data_dir(), "notes.json")


def load():
    """Return the list of notes (empty list if none / unreadable)."""
    try:
        with open(_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return []
    notes = data.get("notes") if isinstance(data, dict) else None
    return notes if isinstance(notes, list) else []


def save(notes):
    """Persist the list of notes (atomic write)."""
    path = _path()
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"notes": notes}, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass  # best-effort; nothing else we can do from here


def add(text):
    """Create a new note from ``text`` and return it."""
    text = (text or "").strip()
    if not text:
        return None
    notes = load()
    note = {
        "id": uuid.uuid4().hex[:10],
        "text": text,
        "created": time.time(),
        "pinned": False,
    }
    notes.append(note)
    save(notes)
    return note


def delete(note_id):
    notes = [n for n in load() if n.get("id") != note_id]
    save(notes)


def toggle_pin(note_id):
    notes = load()
    pinned_now = False
    for note in notes:
        if note.get("id") == note_id:
            note["pinned"] = not note.get("pinned", False)
            pinned_now = note["pinned"]
    save(notes)
    return pinned_now


def update(note_id, text):
    notes = load()
    for note in notes:
        if note.get("id") == note_id:
            note["text"] = (text or "").strip()
    save(notes)


def ordered(notes=None):
    """Notes sorted: pinned first, then most recent."""
    notes = load() if notes is None else notes
    return sorted(notes, key=lambda n: (not n.get("pinned", False), -n.get("created", 0)))


def search(query, notes=None):
    """Case-insensitive substring match on note text, keeping order."""
    notes = ordered(notes)
    q = (query or "").strip().lower()
    if not q:
        return notes
    return [n for n in notes if q in (n.get("text", "").lower())]
