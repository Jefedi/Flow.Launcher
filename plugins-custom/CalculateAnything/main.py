# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the Calculate Anything plugin.

Flow invokes ``python main.py <json-rpc-request>``. The ``flowlauncher`` library
dispatches to ``query`` / ``context_menu`` / action methods and prints results.
"""

import os
import sys

# Make bundled deps (pip install -r requirements.txt -t ./lib) importable.
_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

from calculator import CalcError, evaluate

ICON = "Images/icon.png"

DEFAULTS = {
    "angle_unit": "radians",       # radians | degrees (for trig functions)
    "thousands_separator": False,  # group result digits with separators
}


class CalculateAnything(FlowLauncher):
    def _settings(self):
        settings = dict(DEFAULTS)
        provided = self.rpc_request.get("settings") or {}
        for key in DEFAULTS:
            value = provided.get(key)
            if value is not None:
                settings[key] = value
        return settings

    def query(self, query):
        expression = (query or "").strip()

        if not expression:
            return [
                {
                    "Title": "Tape une expression à calculer",
                    "SubTitle": "Ex : 2+2 · 15% of 80 · sqrt(2) · 2^10 · 5! · pi*2",
                    "IcoPath": ICON,
                }
            ]

        settings = self._settings()
        try:
            result = evaluate(
                expression,
                angle=settings["angle_unit"],
                thousands=bool(settings["thousands_separator"]),
            )
        except CalcError as exc:
            # Keyword is active, so show a gentle hint rather than a hard error.
            return [
                {
                    "Title": "= ?",
                    "SubTitle": f"Expression non reconnue ({exc})",
                    "IcoPath": ICON,
                }
            ]

        return [
            {
                "Title": result.formatted,
                "SubTitle": f"{expression}  ·  Entrée : copier le résultat",
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [result.formatted, False, True],
                },
                # [expression, formatted result] for the context menu.
                "ContextData": [expression, result.formatted],
            }
        ]

    def context_menu(self, data):
        expression = data[0] if len(data) > 0 else ""
        formatted = data[1] if len(data) > 1 else ""

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

        return [
            copy_entry("Copier le résultat", formatted),
            copy_entry("Copier « expression = résultat »", f"{expression} = {formatted}"),
        ]


if __name__ == "__main__":
    CalculateAnything()
