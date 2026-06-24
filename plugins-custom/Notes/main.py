# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the Notes plugin (Raycast-style quick capture).

Type the keyword to:
  * capture: ``note buy milk`` -> top result saves a new note on Enter
  * list/search: ``note`` lists all notes; ``note milk`` filters them

Action methods (add/delete/pin) mutate the JSON store and print a
``Flow.Launcher.ShowMsg`` confirmation (the flowlauncher lib prints nothing for
non query/context_menu methods, so this is the sole stdout).
"""

import json
import os
import sys
from datetime import datetime

_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

import notes_store as store

ICON = "Images/icon.png"
PREVIEW_LEN = 100

# Scores keep the "create" entry on top and pinned notes above the rest.
SCORE_CREATE = 10 ** 15
SCORE_PINNED = 10 ** 12


def _preview(text):
    text = " ".join(text.split())  # collapse newlines/spaces for the list view
    return text if len(text) <= PREVIEW_LEN else text[:PREVIEW_LEN] + "…"


def _when(created):
    try:
        return datetime.fromtimestamp(created).strftime("%d/%m/%Y %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


class Notes(FlowLauncher):
    # --- query --------------------------------------------------------------

    def query(self, query):
        text = (query or "").strip()
        results = []

        if text:
            # Top result: capture the typed text as a new note.
            results.append({
                "Title": text,
                "SubTitle": "➕ Nouvelle note — Entrée pour enregistrer",
                "IcoPath": ICON,
                "Score": SCORE_CREATE,
                "JsonRPCAction": {"method": "add_note", "parameters": [text]},
            })
            matches = store.search(text)
        else:
            matches = store.ordered()

        for note in matches:
            results.append(self._note_result(note))

        if not results:
            results.append({
                "Title": "Aucune note pour l'instant",
                "SubTitle": "Tape « note <texte> » pour en créer une",
                "IcoPath": ICON,
            })
        return results

    def _note_result(self, note):
        text = note.get("text", "")
        pinned = bool(note.get("pinned"))
        created = note.get("created", 0)
        score = int(created) + (SCORE_PINNED if pinned else 0)
        return {
            "Title": ("📌 " if pinned else "") + _preview(text),
            "SubTitle": f"{_when(created)}  ·  Entrée : copier  ·  Maj+Entrée : actions",
            "IcoPath": ICON,
            "Score": score,
            "JsonRPCAction": {
                "method": "Flow.Launcher.CopyToClipboard",
                "parameters": [text, False, True],
            },
            "ContextData": [note.get("id", ""), text, pinned],
        }

    # --- context menu -------------------------------------------------------

    def context_menu(self, data):
        note_id = data[0] if len(data) > 0 else ""
        text = data[1] if len(data) > 1 else ""
        pinned = bool(data[2]) if len(data) > 2 else False
        return [
            {
                "Title": "Copier la note",
                "SubTitle": _preview(text),
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [text, False, True],
                },
            },
            {
                "Title": "Désépingler" if pinned else "Épingler en haut",
                "SubTitle": "",
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "toggle_pin", "parameters": [note_id]},
            },
            {
                "Title": "Supprimer la note",
                "SubTitle": _preview(text),
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "delete_note", "parameters": [note_id]},
            },
        ]

    # --- action methods (side effects + confirmation toast) -----------------

    def add_note(self, text):
        note = store.add(text)
        if note:
            self._toast("Note enregistrée", _preview(note["text"]))

    def delete_note(self, note_id):
        store.delete(note_id)
        self._toast("Note supprimée", "")

    def toggle_pin(self, note_id):
        pinned = store.toggle_pin(note_id)
        self._toast("Note épinglée" if pinned else "Note désépinglée", "")

    def _toast(self, title, subtitle):
        # Handled by the Flow core (IPublicAPI.ShowMsg) as the action response.
        print(json.dumps({
            "method": "Flow.Launcher.ShowMsg",
            "parameters": [title, subtitle, ""],
        }))


if __name__ == "__main__":
    Notes()
