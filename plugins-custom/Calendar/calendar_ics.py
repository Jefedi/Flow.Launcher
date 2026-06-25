# -*- coding: utf-8 -*-
"""Read upcoming events from one or more ICS calendar URLs.

No OAuth: the user pastes the secret ICS subscription URL of their calendar
(Google/Outlook/… all expose one). We fetch it (cached on disk with a short TTL),
expand recurring events with ``recurring_ical_events`` and return the occurrences
in a date window. Knows nothing about Flow Launcher.
"""

import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from collections import namedtuple
from datetime import date, datetime, timedelta, timezone

from icalendar import Calendar
import recurring_ical_events

HTTP_TIMEOUT = 8
CACHE_TTL = 300  # 5 minutes

Event = namedtuple(
    "Event", ["start", "end", "all_day", "summary", "location", "description",
              "url", "meeting_link"],
)


class CalendarError(Exception):
    """Raised with a readable message when events cannot be fetched/parsed."""


# Meeting providers we recognise (first match wins when picking a join link).
_MEETING_HOSTS = (
    "meet.google.com", "zoom.us", "teams.microsoft.com", "teams.live.com",
    "webex.com", "whereby.com", "meet.jit.si", "bluejeans.com", "chime.aws",
)
_URL_RE = re.compile(r"https?://[^\s<>\"')]+")


def _local_tz():
    return datetime.now().astimezone().tzinfo


def as_aware(value):
    """Normalize an ICS date/datetime to an aware datetime in local time."""
    tz = _local_tz()
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=tz)
    # date -> local midnight
    return datetime(value.year, value.month, value.day, tzinfo=tz)


# --- cache ------------------------------------------------------------------

def _cache_path():
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    folder = os.path.join(base, "FlowLauncher", "Calendar")
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        folder = tempfile.gettempdir()
    return os.path.join(folder, "ics_cache.json")


def _load_cache():
    try:
        with open(_cache_path(), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_cache(cache):
    try:
        with open(_cache_path(), "w", encoding="utf-8") as fh:
            json.dump(cache, fh)
    except OSError:
        pass


def _fetch_ics(url):
    """Return the ICS text for ``url``, using a short-lived disk cache."""
    cache = _load_cache()
    entry = cache.get(url)
    if entry and (time.time() - entry.get("ts", 0)) < CACHE_TTL:
        return entry["text"]

    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Calendar Flow Launcher plugin)",
        "Accept": "text/calendar, */*",
    })
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise CalendarError(f"HTTP {exc.code}")
    except urllib.error.URLError as exc:
        raise CalendarError(f"Réseau indisponible ({exc.reason})")
    except TimeoutError:
        raise CalendarError("Délai dépassé")

    cache[url] = {"ts": time.time(), "text": text}
    _save_cache(cache)
    return text


# --- parsing ----------------------------------------------------------------

def _meeting_link(*fields):
    urls = []
    for field in fields:
        if field:
            urls.extend(_URL_RE.findall(str(field)))
    for url in urls:
        if any(host in url for host in _MEETING_HOSTS):
            return url.rstrip(".,);")
    return urls[0].rstrip(".,);") if urls else ""


def _to_event(component):
    raw_start = component.get("DTSTART")
    if raw_start is None:
        return None
    start_val = raw_start.dt
    all_day = not isinstance(start_val, datetime)

    raw_end = component.get("DTEND")
    end_val = raw_end.dt if raw_end is not None else start_val

    summary = str(component.get("SUMMARY") or "(sans titre)")
    location = str(component.get("LOCATION") or "")
    description = str(component.get("DESCRIPTION") or "")
    url = str(component.get("URL") or "")
    link = _meeting_link(location, url, description, summary)

    return Event(
        start=as_aware(start_val),
        end=as_aware(end_val),
        all_day=all_day,
        summary=summary,
        location=location,
        description=description,
        url=url,
        meeting_link=link,
    )


def get_events(urls, days=7):
    """Return upcoming events across ``urls`` within ``days``, sorted by start.

    ``urls`` may be a string (one URL or comma/newline separated) or a list.
    Raises CalendarError only if *every* source fails.
    """
    if isinstance(urls, str):
        url_list = [u.strip() for u in re.split(r"[,\n]", urls) if u.strip()]
    else:
        url_list = [u for u in (urls or []) if u]
    if not url_list:
        raise CalendarError("Aucune URL ICS configurée")

    now = datetime.now(_local_tz())
    window_start = now - timedelta(hours=2)   # keep an event that just started
    window_end = now + timedelta(days=max(1, int(days)))

    events = []
    errors = []
    for url in url_list:
        try:
            cal = Calendar.from_ical(_fetch_ics(url))
            occurrences = recurring_ical_events.of(cal).between(
                window_start.date(), window_end.date() + timedelta(days=1)
            )
        except CalendarError as exc:
            errors.append(str(exc))
            continue
        except Exception:
            errors.append("calendrier illisible")
            continue
        for comp in occurrences:
            ev = _to_event(comp)
            if ev and window_start <= ev.start <= window_end:
                events.append(ev)

    if not events and errors:
        raise CalendarError(errors[0])

    events.sort(key=lambda e: e.start)
    return events
