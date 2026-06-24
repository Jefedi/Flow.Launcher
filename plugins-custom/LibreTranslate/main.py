# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the LibreTranslate plugin.

Flow Launcher invokes this file as ``python main.py <json-rpc-request>``.
The ``flowlauncher`` library reads that request, dispatches to ``query`` /
``context_menu`` / action methods, and prints the JSON result back to Flow.
"""

import os
import sys
import webbrowser
from urllib.parse import quote

# Make bundled dependencies (installed via: pip install -r requirements.txt -t ./lib)
# importable, regardless of the directory Flow Launcher runs us from.
_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

from libretranslate import TranslationError, language_name, translate

ICON = "Images/icon.png"

# Default settings, used as a fallback if Flow has not pushed settings yet
# (e.g. a brand-new install before the settings panel is opened).
DEFAULTS = {
    "instance_url": "https://translate.jefe.ovh",
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
        target = settings["target_lang"]
        try:
            result = translate(
                text,
                instance_url=settings["instance_url"],
                target_lang=target,
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

        # Richer subtitle: full language names + detection confidence when available.
        detected_label = language_name(result.detected)
        if result.confidence is not None:
            detected_label += f" ({result.confidence}%)"
        subtitle = (
            f"{detected_label} → {language_name(target)}"
            "  ·  Entrée : copier  ·  Maj+Entrée : plus d'actions"
        )
        return [
            {
                "Title": result.text,
                "SubTitle": subtitle,
                "IcoPath": ICON,
                # method names starting with "Flow.Launcher." are handled by the
                # Flow core directly (IPublicAPI), not forwarded back to Python.
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [result.text, False, True],
                },
                # Carried into context_menu: [original, translation, detected, target].
                "ContextData": [text, result.text, result.detected, target],
            }
        ]

    def context_menu(self, data):
        # ``data`` is ContextData: [original, translation, detected, target].
        original = data[0] if len(data) > 0 else ""
        translation = data[1] if len(data) > 1 else ""
        detected = data[2] if len(data) > 2 else "auto"
        target = data[3] if len(data) > 3 else "en"

        def copy_entry(title, value):
            return {
                "Title": title,
                "SubTitle": value,
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [value, False, True],
                },
            }

        entries = [
            copy_entry("Copier la traduction", translation),
            copy_entry("Copier le texte original", original),
            copy_entry("Copier « original → traduction »", f"{original} → {translation}"),
            {
                "Title": "Ouvrir dans Google Translate",
                "SubTitle": "Ouvre le texte dans le navigateur (quitte ton instance)",
                "IcoPath": ICON,
                # Non "Flow.Launcher." method -> forwarded back to open_url below.
                "JsonRPCAction": {
                    "method": "open_url",
                    "parameters": [self._google_url(original, detected, target)],
                },
            },
        ]
        return entries

    # A few LibreTranslate codes differ from Google Translate's; map those.
    _GOOGLE_CODES = {
        "zh-Hans": "zh-CN", "zh-Hant": "zh-TW", "pt-BR": "pt", "nb": "no",
    }

    @classmethod
    def _google_url(cls, text, source, target):
        """Build a prefilled Google Translate URL ('auto' source is safest)."""
        sl = cls._GOOGLE_CODES.get(source, source) if source else "auto"
        tl = cls._GOOGLE_CODES.get(target, target) if target else "en"
        return (
            "https://translate.google.com/"
            f"?sl={quote(sl)}&tl={quote(tl)}&text={quote(text)}&op=translate"
        )

    def open_url(self, url):
        """Action handler: open a URL in the default browser."""
        webbrowser.open(url)


if __name__ == "__main__":
    LibreTranslate()
