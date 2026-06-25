# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the Clipboard History plugin.

Reads the Windows OS clipboard history (Win+V) live via winsdk. Type the keyword
to browse it, type more to filter. Enter puts the entry back on the clipboard
(ready to paste). Context menu: copy, delete entry, clear history.
"""

import json
import os
import sys
from datetime import datetime, timezone

_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

import clipboard_history as clip

ICON = "Images/icon.png"
PREVIEW_LEN = 90
MAX_ITEMS = 50


def _preview(text):
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW_LEN else text[:PREVIEW_LEN] + "…"


def _ago(ts):
    """Relative french timestamp from a tz-aware datetime."""
    try:
        now = datetime.now(timezone.utc)
        delta = now - ts.astimezone(timezone.utc)
        secs = int(delta.total_seconds())
    except Exception:
        return ""
    if secs < 60:
        return "à l'instant"
    if secs < 3600:
        return f"il y a {secs // 60} min"
    if secs < 86400:
        return f"il y a {secs // 3600} h"
    days = secs // 86400
    if days == 1:
        return "hier"
    if days < 7:
        return f"il y a {days} j"
    try:
        return ts.astimezone().strftime("%d/%m/%Y")
    except Exception:
        return ""


class ClipboardHistory(FlowLauncher):
    def query(self, query):
        text = (query or "").strip()

        if not clip.is_available():
            return self._single(
                "winsdk indisponible",
                "La librairie winsdk n'a pas pu être chargée (réinstalle requirements).",
            )

        ok, items = clip.get_items(MAX_ITEMS)
        if not ok:
            return self._single(
                "Historique du presse-papiers désactivé",
                "Active-le : Paramètres → Système → Presse-papiers → Historique (ou Win+V).",
            )

        if text:
            low = text.lower()
            items = [it for it in items if low in it.text.lower()]

        if not items:
            return self._single(
                "Aucune entrée" + (" correspondante" if text else ""),
                "Copie quelque chose, ou tape pour filtrer." if not text else "Essaie un autre terme.",
            )

        results = []
        for rank, it in enumerate(items):
            results.append({
                "Title": _preview(it.text),
                "SubTitle": f"{_ago(it.timestamp)}  ·  Entrée : remettre dans le presse-papiers  ·  Maj+Entrée : actions",
                "IcoPath": ICON,
                "Score": MAX_ITEMS - rank,  # preserve most-recent-first order
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [it.text, False, True],
                },
                "ContextData": [it.id, it.text],
            })
        return results

    def context_menu(self, data):
        item_id = data[0] if len(data) > 0 else ""
        text = data[1] if len(data) > 1 else ""
        return [
            {
                "Title": "Copier",
                "SubTitle": _preview(text),
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [text, False, True],
                },
            },
            {
                "Title": "Supprimer cette entrée",
                "SubTitle": "Retire l'entrée de l'historique Windows",
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "delete_item", "parameters": [item_id]},
            },
            {
                "Title": "Vider tout l'historique",
                "SubTitle": "Efface tout l'historique du presse-papiers Windows",
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "clear_history", "parameters": []},
            },
        ]

    # --- action methods -----------------------------------------------------

    def delete_item(self, item_id):
        ok = clip.delete(item_id)
        self._toast("Entrée supprimée" if ok else "Suppression impossible", "")

    def clear_history(self):
        ok = clip.clear()
        self._toast("Historique vidé" if ok else "Vidage impossible", "")

    # --- helpers ------------------------------------------------------------

    def _single(self, title, subtitle):
        return [{"Title": title, "SubTitle": subtitle, "IcoPath": ICON}]

    def _toast(self, title, subtitle):
        print(json.dumps({
            "method": "Flow.Launcher.ShowMsg",
            "parameters": [title, subtitle, ""],
        }))


if __name__ == "__main__":
    ClipboardHistory()
