# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the LibreTranslate plugin.

Flow Launcher invokes this file as ``python main.py <json-rpc-request>``.
The ``flowlauncher`` library reads that request, dispatches to ``query`` /
``context_menu`` / action methods, and prints the JSON result back to Flow.
"""

import os
import sys

# Make bundled dependencies (installed via: pip install -r requirements.txt -t ./lib)
# importable, regardless of the directory Flow Launcher runs us from.
_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

from libretranslate import TranslationError, translate

ICON = "Images/icon.png"

# Default settings, used as a fallback if Flow has not pushed settings yet
# (e.g. a brand-new install before the settings panel is opened).
DEFAULTS = {
    "instance_url": "https://translate.jefe.al",
    "target_lang": "fr",
    "api_key": "",
}


class LibreTranslate(FlowLauncher):
    def _settings(self):
        """Merge Flow-provided settings over our defaults."""
        settings = dict(DEFAULTS)
        provided = self.rpc_request.get("settings") or {}
        for key in DEFAULTS:
            value = provided.get(key)
            if value is not None:
                settings[key] = value
        return settings

    def query(self, query):
        text = (query or "").strip()

        # Empty / too-short query: show a hint instead of calling the API.
        if len(text) <= 1:
            return [
                {
                    "Title": "Tape un texte à traduire",
                    "SubTitle": "Exemple : tr hello world",
                    "IcoPath": ICON,
                }
            ]

        settings = self._settings()
        try:
            translated, detected = translate(
                text,
                instance_url=settings["instance_url"],
                target_lang=settings["target_lang"],
                api_key=settings["api_key"],
            )
        except TranslationError as exc:
            return [
                {
                    "Title": "Erreur de traduction",
                    "SubTitle": str(exc),
                    "IcoPath": ICON,
                }
            ]

        target = settings["target_lang"]
        subtitle = f"{detected or '?'} → {target}  ·  Entrée : copier la traduction"
        return [
            {
                "Title": translated,
                "SubTitle": subtitle,
                "IcoPath": ICON,
                # method names starting with "Flow.Launcher." are handled by the
                # Flow core directly (IPublicAPI), not forwarded back to Python.
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [translated, False, True],
                },
                # Carried into context_menu for the secondary action.
                "ContextData": [text, translated],
            }
        ]

    def context_menu(self, data):
        # ``data`` is whatever we put in ContextData above.
        original = data[0] if data else ""
        return [
            {
                "Title": "Copier le texte original",
                "SubTitle": original,
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [original, False, True],
                },
            }
        ]


if __name__ == "__main__":
    LibreTranslate()
