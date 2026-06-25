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
        is_dir = bool(data[2]) if len(data) > 2 else False
        parent = os.path.dirname(path)
        stem, ext = os.path.splitext(name)
        is_exe = (not is_dir) and ext.lower() in (
            ".exe", ".bat", ".cmd", ".com", ".msi", ".ps1")

        def act(title, method, sub):
            return {"Title": title, "SubTitle": sub, "IcoPath": ICON,
                    "JsonRPCAction": {"method": method, "parameters": [path]}}

        def copy(title, value):
            return {"Title": title, "SubTitle": value, "IcoPath": ICON,
                    "JsonRPCAction": {"method": "Flow.Launcher.CopyToClipboard",
                                      "parameters": [value, False, True]}}

        entries = [
            act("Ouvrir", "open_path", path),
            act("Ouvrir le dossier contenant", "reveal", parent),
        ]
        if not is_dir:
            entries.append(act("Ouvrir avec…", "open_with", "Choisir l'application"))
        entries.append(act("Ouvrir un terminal ici", "open_terminal",
                           path if is_dir else parent))
        if is_exe:
            entries.append(act("Exécuter en administrateur", "run_as_admin", path))
        entries.append(copy("Copier le chemin", path))
        entries.append(copy("Copier le dossier (chemin parent)", parent))
        entries.append(copy("Copier le nom", name))
        if not is_dir and stem and stem != name:
            entries.append(copy("Copier le nom sans extension", stem))
        return entries

    # --- action methods -----------------------------------------------------

    def open_path(self, path):
        try:
            os.startfile(path)  # default app for files, Explorer for folders
        except OSError:
            self.reveal(path)

    def reveal(self, path):
        # Open the containing folder with the item selected. explorer.exe needs the
        # exact form  /select,"<path>"  (quotes around the path only); building it as
        # an argv list makes Python quote the whole token and explorer then ignores
        # /select and opens the default folder. So pass one literal command string.
        try:
            subprocess.Popen(f'explorer /select,"{path}"')
        except OSError:
            pass

    def open_with(self, path):
        # Windows "Open with…" dialog (runs in a detached rundll32 process).
        try:
            subprocess.Popen(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", path])
        except OSError:
            pass

    def open_terminal(self, path):
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        safe = folder.replace("'", "''")
        try:
            subprocess.Popen(
                ["powershell.exe", "-NoExit", "-Command", f"Set-Location -LiteralPath '{safe}'"],
                creationflags=0x00000010,  # CREATE_NEW_CONSOLE
            )
        except OSError:
            pass

    def run_as_admin(self, path):
        try:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", path, None, os.path.dirname(path), 1)
        except Exception:
            pass

    def _single(self, title, subtitle):
        return [{"Title": title, "SubTitle": subtitle, "IcoPath": ICON}]


if __name__ == "__main__":
    FileSearch()
