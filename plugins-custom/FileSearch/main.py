# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the File Search plugin (Everything-powered).

Forwards the query to the running Everything index via es.exe and lists matching
files/folders instantly. Enter opens the item; context menu opens the containing
folder or copies the path/name.
"""

import os
import subprocess
import sys

_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

import es_search

ICON = "Images/icon.png"
_NO_WINDOW = 0x08000000

DEFAULTS = {
    "es_path": "",
    "max_results": "30",
}


class FileSearch(FlowLauncher):
    def _settings(self):
        settings = dict(DEFAULTS)
        provided = self.rpc_request.get("settings") or {}
        for key in DEFAULTS:
            value = provided.get(key)
            if value is not None:
                settings[key] = value
        return settings

    def query(self, query):
        text = (query or "").strip()
        if not text:
            return self._single(
                "Tape un nom de fichier ou de dossier",
                "Syntaxe Everything : *.pdf · rapport · ext:docx · C:\\Users\\ facture",
            )

        settings = self._settings()
        try:
            limit = int(settings.get("max_results") or 30)
        except (TypeError, ValueError):
            limit = 30

        try:
            results = es_search.search(text, settings.get("es_path", ""), limit)
        except es_search.EverythingError as exc:
            return self._single("Recherche indisponible", str(exc))

        if not results:
            return self._single("Aucun résultat", f"Rien ne correspond à « {text} »")

        out = []
        for rank, r in enumerate(results):
            meta = " · ".join(p for p in (r.size, r.date) if p)
            out.append({
                "Title": r.name,
                "SubTitle": f"{r.path}   ·   {meta}",
                # Use the item's own path as icon so files/folders show their shell icon.
                "IcoPath": r.path,
                "Score": len(results) - rank,
                "JsonRPCAction": {"method": "open_path", "parameters": [r.path]},
                "ContextData": [r.path, r.name, r.is_dir],
            })
        return out

    def context_menu(self, data):
        path = data[0] if len(data) > 0 else ""
        name = data[1] if len(data) > 1 else ""
        return [
            {
                "Title": "Ouvrir",
                "SubTitle": path,
                "IcoPath": path or ICON,
                "JsonRPCAction": {"method": "open_path", "parameters": [path]},
            },
            {
                "Title": "Ouvrir le dossier contenant",
                "SubTitle": os.path.dirname(path),
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "reveal", "parameters": [path]},
            },
            {
                "Title": "Copier le chemin",
                "SubTitle": path,
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [path, False, True],
                },
            },
            {
                "Title": "Copier le nom",
                "SubTitle": name,
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [name, False, True],
                },
            },
        ]

    # --- action methods -----------------------------------------------------

    def open_path(self, path):
        try:
            os.startfile(path)  # default app for files, Explorer for folders
        except OSError:
            self.reveal(path)

    def reveal(self, path):
        # Open the containing folder with the item selected.
        try:
            subprocess.Popen(["explorer", f"/select,{path}"], creationflags=_NO_WINDOW)
        except OSError:
            pass

    def _single(self, title, subtitle):
        return [{"Title": title, "SubTitle": subtitle, "IcoPath": ICON}]


if __name__ == "__main__":
    FileSearch()
