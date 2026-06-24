# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the Calculate Anything plugin.

Flow invokes ``python main.py <json-rpc-request>``. The ``flowlauncher`` library
dispatches to ``query`` / ``context_menu`` / action methods and prints results.

A query is routed through handlers in order of specificity:
    1. currency / crypto   (10 usd in eur, 0.5 btc in usd)
    2. dates / time zones   (now in tokyo, days until 2026-12-25)
    3. math expression      (2+2, 15% of 80, sqrt(2))
The first handler that recognises the input wins.
"""

import os
import sys

# Make bundled deps (pip install -r requirements.txt -t ./lib) importable.
_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

import currency
import datetime_calc
from calculator import CalcError, evaluate

ICON = "Images/icon.png"

DEFAULTS = {
    "angle_unit": "radians",        # radians | degrees (trig)
    "thousands_separator": False,   # group math result digits
    "default_currency": "EUR",      # target when a currency query omits one
}


def _fmt_money(value):
    """Readable money string: 2-4 decimals for >=1, more sig digits for fractions."""
    if abs(value) >= 1:
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return f"{value:.6g}"


def _plain_money(value):
    """Same number without grouping, for copying / chaining."""
    if abs(value) >= 1:
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{value:.6g}"


class CalculateAnything(FlowLauncher):
    def _settings(self):
        settings = dict(DEFAULTS)
        provided = self.rpc_request.get("settings") or {}
        for key in DEFAULTS:
            value = provided.get(key)
            if value is not None:
                settings[key] = value
        return settings

    # --- result helpers -----------------------------------------------------

    def _result(self, title, subtitle, primary_copy, menu_pairs):
        """Build a single Flow result; Enter copies ``primary_copy``.

        ``menu_pairs`` is a list of [menu_title, value] used by context_menu.
        """
        return {
            "Title": title,
            "SubTitle": subtitle,
            "IcoPath": ICON,
            "JsonRPCAction": {
                "method": "Flow.Launcher.CopyToClipboard",
                "parameters": [primary_copy, False, True],
            },
            "ContextData": menu_pairs,
        }

    def _hint(self, title, subtitle):
        return [{"Title": title, "SubTitle": subtitle, "IcoPath": ICON}]

    # --- query --------------------------------------------------------------

    def query(self, query):
        text = (query or "").strip()
        if not text:
            return self._hint(
                "Tape une expression",
                "2+2 · 15% of 80 · 10 usd in eur · 0.5 btc in usd · now in tokyo · days until 2026-12-25",
            )

        settings = self._settings()

        result = (self._try_currency(text, settings)
                  or self._try_date(text)
                  or self._try_math(text, settings))
        if result is not None:
            return [result]

        return self._hint("= ?", "Expression non reconnue")

    def _try_currency(self, text, settings):
        parsed = currency.parse_query(text, settings.get("default_currency", "EUR"))
        if not parsed:
            return None
        amount, src, dst = parsed
        try:
            r = currency.convert(amount, src, dst)
        except currency.ConversionError as exc:
            # The intent was clearly a conversion: report the error, don't fall back.
            return {"Title": "Conversion impossible", "SubTitle": str(exc), "IcoPath": ICON}

        title = f"{_fmt_money(r.value)} {dst}"
        subtitle = (f"{_plain_money(amount)} {src}  ·  1 {src} = {_fmt_money(r.unit_rate)} {dst}"
                    "  ·  Entrée : copier")
        return self._result(
            title, subtitle, _plain_money(r.value),
            [
                ["Copier le montant", _plain_money(r.value)],
                ["Copier avec la devise", f"{_plain_money(r.value)} {dst}"],
                ["Copier le taux", f"1 {src} = {_fmt_money(r.unit_rate)} {dst}"],
            ],
        )

    def _try_date(self, text):
        try:
            ans = datetime_calc.handle(text)
        except datetime_calc.NotADate:
            return None
        return self._result(
            ans.title, f"{ans.subtitle}  ·  Entrée : copier", ans.copy,
            [["Copier", ans.copy], ["Copier le libellé", ans.title]],
        )

    def _try_math(self, text, settings):
        try:
            r = evaluate(
                text,
                angle=settings["angle_unit"],
                thousands=bool(settings["thousands_separator"]),
            )
        except CalcError:
            return None
        return self._result(
            r.formatted, f"{text}  ·  Entrée : copier le résultat", r.formatted,
            [
                ["Copier le résultat", r.formatted],
                ["Copier « expression = résultat »", f"{text} = {r.formatted}"],
            ],
        )

    # --- context menu -------------------------------------------------------

    def context_menu(self, data):
        # ``data`` is the list of [menu_title, value] pairs from the result.
        entries = []
        for pair in data or []:
            if not isinstance(pair, list) or len(pair) < 2:
                continue
            title, value = pair[0], pair[1]
            entries.append({
                "Title": title,
                "SubTitle": value,
                "IcoPath": ICON,
                "JsonRPCAction": {
                    "method": "Flow.Launcher.CopyToClipboard",
                    "parameters": [value, False, True],
                },
            })
        return entries


if __name__ == "__main__":
    CalculateAnything()
