# -*- coding: utf-8 -*-
"""Flow Launcher entry point for the Calendar plugin.

Reads upcoming events from the user's ICS calendar URL(s) and lists them.
Enter joins the meeting (if a video link is found) or copies the details.
"""

import os
import sys
import webbrowser
from datetime import datetime

_PLUGIN_DIR = os.path.abspath(os.path.dirname(__file__))
for _path in (_PLUGIN_DIR, os.path.join(_PLUGIN_DIR, "lib")):
    if _path not in sys.path:
        sys.path.append(_path)

from flowlauncher import FlowLauncher

import calendar_ics

ICON = "Images/icon.png"

DEFAULTS = {
    "ics_url": "",
    "lookahead_days": "7",
}

WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _day_label(start, now):
    delta_days = (start.date() - now.date()).days
    if delta_days == 0:
        return "Aujourd'hui"
    if delta_days == 1:
        return "Demain"
    if 2 <= delta_days <= 6:
        return WEEKDAYS_FR[start.weekday()].capitalize()
    return start.strftime("%d/%m")


def _format_when(ev, now):
    day = _day_label(ev.start, now)
    if ev.all_day:
        return f"{day} (journée)"
    span = ev.start.strftime("%H:%M")
    if ev.end and ev.end > ev.start:
        span += "–" + ev.end.strftime("%H:%M")
    # Imminence hints for conference calls.
    if ev.start <= now <= ev.end:
        return f"{day} {span} · en cours"
    mins = (ev.start - now).total_seconds() / 60
    if 0 <= mins < 60:
        return f"{day} {span} · dans {int(mins)} min"
    return f"{day} {span}"


class Calendar(FlowLauncher):
    def _settings(self):
        settings = dict(DEFAULTS)
        provided = self.rpc_request.get("settings") or {}
        for key in DEFAULTS:
            value = provided.get(key)
            if value is not None:
                settings[key] = value
        return settings

    def query(self, query):
        settings = self._settings()
        url = (settings.get("ics_url") or "").strip()
        if not url:
            return self._single(
                "Configure l'URL de ton agenda",
                "Settings → Plugins → Calendar → colle l'URL ICS (secrète) de ton calendrier.",
            )

        try:
            days = int(settings.get("lookahead_days") or 7)
        except (TypeError, ValueError):
            days = 7

        try:
            events = calendar_ics.get_events(url, days)
        except calendar_ics.CalendarError as exc:
            return self._single("Agenda indisponible", str(exc))

        text = (query or "").strip().lower()
        if text:
            events = [e for e in events
                      if text in e.summary.lower() or text in (e.location or "").lower()]

        if not events:
            return self._single(
                "Rien de prévu" + (" (filtre)" if text else f" dans les {days} jours"),
                "Profite-en ✨" if not text else "Essaie un autre terme.",
            )

        now = datetime.now(calendar_ics._local_tz())
        results = []
        for rank, ev in enumerate(events):
            when = _format_when(ev, now)
            bits = [when]
            if ev.location and not ev.location.startswith("http"):
                bits.append(ev.location)
            if ev.meeting_link:
                bits.append("🎥 visio")
            bits.append("Entrée : rejoindre la visio" if ev.meeting_link else "Entrée : copier")

            details = f"{ev.summary} — {when}" + (f" — {ev.location}" if ev.location else "")
            primary = {
                "method": "open_url" if ev.meeting_link else "Flow.Launcher.CopyToClipboard",
                "parameters": [ev.meeting_link] if ev.meeting_link else [details, False, True],
            }
            results.append({
                "Title": ev.summary,
                "SubTitle": "  ·  ".join(bits),
                "IcoPath": ICON,
                "Score": 10000 - rank,  # keep chronological order
                "JsonRPCAction": primary,
                "ContextData": [ev.meeting_link or "", details, ev.location or ""],
            })
        return results

    def context_menu(self, data):
        link = data[0] if len(data) > 0 else ""
        details = data[1] if len(data) > 1 else ""
        location = data[2] if len(data) > 2 else ""
        entries = []
        if link:
            entries.append({
                "Title": "Rejoindre la visio",
                "SubTitle": link,
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "open_url", "parameters": [link]},
            })
        entries.append({
            "Title": "Copier les détails",
            "SubTitle": details,
            "IcoPath": ICON,
            "JsonRPCAction": {
                "method": "Flow.Launcher.CopyToClipboard",
                "parameters": [details, False, True],
            },
        })
        if location and location.startswith("http"):
            entries.append({
                "Title": "Ouvrir le lieu",
                "SubTitle": location,
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "open_url", "parameters": [location]},
            })
        return entries

    def open_url(self, url):
        if url:
            webbrowser.open(url)

    def _single(self, title, subtitle):
        return [{"Title": title, "SubTitle": subtitle, "IcoPath": ICON}]


if __name__ == "__main__":
    Calendar()
